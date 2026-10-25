# Virtual Stage v0: built and judged (2026-10-25)

Workflow run wf_324eb0ef-7bf (task w0fkmktm1), the build and judge stages. Branch worktree-wf_324eb0ef-7bf-6 (a4bc476a), arsenal/web/stage/; not merged yet. Verbatim; local paths shortened to <scratch> and <worktrees>. Qlimax footage, frames and downloaded specs stay in local scratch, never in this repo.

Vandor's read: 4.5/10 against Daniel's bar ("beats the real thing"), 7/10 as an engineering slice. The bones are right (a data-driven rig, beat-locked effects with 0 frames of error, real hoist limits, cuts on bar lines); the picture is not yet light in haze. The judge's v1 list starts where Void Star's and Laser Sky's verdicts do: make the air glow, and stop the beams clipping.

---

## The build (verbatim)

I built the Virtual Stage v0 page and committed it on branch `worktree-wf_324eb0ef-7bf-6` as commit `a4bc476a`. It was never pushed and master is untouched. The 54 node tests pass, and every check in the headless SwiftShader receipt passes at 1280×720.

**How to open it.** Use `http://127.0.0.1:8793/web/stage/index.html?demo=1` for the built-in demo show at 150 BPM. Without `?demo=1` the page listens to the engine on 8794 and only reads from it; it never posts. Daniel's server serves the main checkout, so the URL works only after this branch is merged. three.js r186 still comes from the same jsDelivr link the piano page uses.

**What Daniel will see.** The demo runs intro, build, drop and break in a loop:
- **The hall:** an oval arena of our own with raked stands, a rigging grid, PA hangs and 7,000 crowd figures. A third of them have raised arms that move on the beat.
- **The strand:** 12 rungs hung from 24 hoists, each carrying two cubes, dot strips and pixel bars. It moves in a beat-locked wave at real hoist limits (0.5 m/s, 0.4 m/s²). The build's "sky comes down" move lands exactly on the drop's downbeat.
- **The beams:** 28 moving heads with the real parameter set, drawn as volumetric beams in haze: 12 under the rungs, 8 on an overhead truss and 8 on the stage lip. Effects (chase, fan, wave, pulse) are locked to one beat clock.
- **The lasers:** 21 projectors (both banks, the side towers and a hero position) drawing the lattice, tunnel, ceiling and fan looks plus pad hits.
- **The rest:** a four-ring spiral of 3,013 LED cells and 8 hazers feeding one haze field.
- **The camera:** shots are cut on bar lines. They include a front-of-house hold, a crane rise, the strand flythrough, the shot looking up the strand, two orbits, a tribune view, a top-down view and a crowd view. The flythrough ends inside the inner ring on the drop's downbeat.
- **Controls:** pads 1 (KICK), 2 (lasers; holding gates them), 6 (FLY-OUT) and 10 (DROP NOW); the keyboard keys are 1, 2, 6 and 0. Faders F1, F4, F5, F6 and F9 (strand, lasers, haze, speed, master) are also sliders in the on-screen panel.

**The numbers** (receipt `stage-20261025-063245`):

| Check | Result |
|---|---|
| Boot | SwiftShader confirmed, no errors |
| Beat grid | one beat every 24 or 25 frames at 150 BPM (93 beats) |
| Strand | every rung travels 6 m; the landing falls on the drop's bar line (minimum move time 10.8 s) |
| Effects on the clock | the strand heads' pulse (32 peaks) and the KICK lift peak on the beat frame, 0 frames off |
| Camera | 4 cuts, all on bar lines (within 1 frame), at least 8 beats apart; flythrough ends 0.10 m from the ring centre on the downbeat |
| Fake engine | 140 BPM followed, re-anchors on a tap, pads reach the rig, beat position never runs backward |
| Flash safety (240 frames, 60 fps virtual clock, every frame read back) | at most 2 flashes a second in any window, no red flashes, zero limiter interventions. This holds for the demo as programmed and with a laser pad storm (17 presses, 9 new hits). |

Frame cost on SwiftShader (front-of-house shot, 1280×720) is about 480–760 ms a frame:

| Pass | ms |
|---|---|
| Opaque scene | 690 |
| Wide beams (half resolution) | 13–15 |
| Composite | 7 |
| Bloom | 15 |
| Finish | 9 |
| Flash meter | 3 |
| Apply pass | 9 |

The crowd alone costs about 450 ms of that on SwiftShader. The RX 6600 figure is an op-count estimate, not a measurement: about 1.5 ms a frame at 1280×720 (about 3.4 ms at 1080p), of which the opaque pass is 0.83 ms. It does not count the 960,000 triangles or the one-frame stall from reading the flash meter back each frame. The 60-second real-GPU bench with Daniel present (design slice S10) replaces it.

**Where it departs from the design** (Daniel should know these):
- **Folder name:** the code lives in `arsenal/web/stage/` as the brief asked; the design calls it `arena`.
- **Lasers v2 and gate v2:** neither is on master, so the page carries a small laser engine that follows the Lasers v2 output format, and its own flash limiter. The limiter adjusts each of 16 screen cells, holds a cell on its last frame instead of fading it toward grey, and allows 5 transitions a second; the file header explains why 5 keeps the count at 3 flashes the way the verifier counts. Both are meant to be replaced by the real modules.
- **New safety rules I added:**
  - Fast laser gates dip to 70 % instead of black.
  - A new fast laser hit cancels the older ones.
  - A pad press within a quarter beat of the last one keeps the current hit lit instead of starting another.
  - Lasers passing within 4 m of the camera fade, and a beam the camera flies into drops to 15 %.

  Without these, the build's held laser gate flashed the whole frame.
- **Display caps:** laser pixels are capped at 200 units and bloom input at 40 units. These only limit glow; they are look choices.
- **Moving-head dimmer speed:** set to a 0.04 s full fade, an estimate.
- **Shaders:** the beam shaders and bloom are local to the page, not yet modules in the house GLSL library.
- **Commit hook side effects:** the hook regenerated `docs/PHYSICS.md` (included in the commit) and appended a line to `state/authorship/seats.jsonl`, which I left uncommitted.

**How it compares with Daniel's frames.** The tribune view (ref-22) is the closest match. Against ref-20 the laser density is far lower: dozens of beams against more than 100. There is no star formation or figure (ref-24), the cubes read as flat pink boxes, and the haze has no magenta glow from the LEDs or washes.

**Gap to v1:**
- Run the stage as a set inside the VJ page, with gate v2 as the limiter, Lasers v2 as the laser engine, and the VJ scenes as LED content.
- The full rig: 16 rungs with 8 heads each and the 8×8 matrix, 5 tilting rings, the figure, 288 heads, 53 lasers with followers, about 18 atmosphere units.
- Gobo, prism and frost on the beams; half-colour wheels; heads that aim at world points.
- CO2, puff and pyro smoke volumes; sparks and flames; low fog; glow lit into the haze by the LEDs and washes.
- The predictive flash governor, a smarter camera director, and the full KeyLab map.
- Shadows and an edge-aware upsample for the beams; a lighter crowd model with phone screens.
- Vendor three.js locally (Daniel's call), and add the beam shaders and bloom to the house library.
- The real-GPU bench (S10).

Files are in `<worktrees>\wf_324eb0ef-7bf-6`:
- `arsenal\web\stage\` (open `index.html`; the rig is in `sets\source-v0.json`; `README.md` explains it)
- `arsenal\lanes\stage_verify.mjs` (the headless receipt)
- `tests\stage_*.test.mjs`
- `state\arsenal\receipts\stage-20261025-063245\receipt.json` (not committed)

Contact sheets are private and live only in `<scratch>\stage\v0\`:
- `all-shots.jpg`
- `pair-ref-19.jpg`, `pair-ref-20.jpg`, `pair-ref-22.jpg`, `pair-ref-24.jpg`
- the 10 PNG shots and `make_sheets.py`

---

## The judge (verbatim)

**Verdict: Virtual Stage v0 scores 4.5/10 against Daniel's bar ("beats the real thing").** As an engineering slice it is a solid 7/10. The timing, data model, tests and licence are good. The picture is the weak part: it does not yet read as a real stage in haze, and it is far from the density of Qlimax 2014.

**What I checked.** The branch is `worktree-wf_324eb0ef-7bf-6`, commit `a4bc476a`. It is not on master, has no upstream, and carries no attribution trailer. I exported it with `git archive` into my scratch folder and ran it headless on SwiftShader, one Chrome at a time under the house GPU lock, from port 8988. Seven bursts, all clean, no page errors:
- the director's own camera at 15 moments;
- 10 posed shots matched to Daniel's frames;
- one bar of the drop, every 6th frame;
- three frame-by-frame series where I read the canvas back and counted flashes with my own code;
- a haze test at 15% and 100%.

The builder's 54 node tests pass on the export.

| Area | Score | Evidence |
|---|---|---|
| Reads as a real stage in haze | 3/10 | Beams come out as clipped white rods of even brightness with almost no halo or haze texture. The noise in the haze is at 9–26 m, too coarse to show inside a beam. The room is a flat dark-purple veil; in every Qlimax frame the air itself glows blue, magenta or gold. At 100% haze the room just turns a flat grey (`haze-sheet.jpg`). Cubes are flat magenta boxes with hard edges, not glowing cubes. |
| Qlimax 2014 grammar | 3.5/10 | Closest match is the tribune view against ref-22. Missing: the figure, sparkler/gerb crowns, flames, CO2, the star cluster (it exists in `kinetics.js` but the show never uses it), PA silhouettes and the lit stage. Rings are dotted and lean back like a dish, not broad LED slats around a head. The strand has 1 head per rung (real: several). Lasers run 32–52 segments, green and blue only, about 1 px wide; ref-20 has more than 100 beams. |
| Camera | 6/10 | Cuts land exactly on bar lines, and the flythrough arrives on the downbeat (the builder's receipt measured 0.10 m from the ring centre). But drop shots hold 2–4 bars against 0.6–1.6 s in the footage. The crowd shot has no hands or phones in the foreground. TOPDOWN is nearly black (mean luminance 0.038). TUNNEL_UP has a beat-swinging black slab of crowd arm in the middle of the frame. Only the flythrough, crane, orbits and top-down exist; there are no corkscrew, ring-thread, jib or side-track flypaths, and no glides. |
| Musicality | 5/10 | Everything is locked to the beat grid with 0 frames of error. But the page ignores the engine's hits, bands, chords and tension; energy only moves the crowd's arms. Beat pulses swing the frame's luminance by only 4–14% (my series). The moving heads mostly hang straight down or up, with no fans, circles or ballyhoo outside pad 6. |
| Fitness for hundreds of fixtures at 60 fps on an RX 6600 | 6/10 | Good bones: a data-driven rig, instancing, a renderer that never sees music, analytic beam cones, equiangular sampling. Hard ceilings: 32 spot lights (the first 32, not the most relevant), 512 laser segments (Source v1 wants about 1,300), and a synchronous CPU readback every frame for the limiter (a pipeline stall; gate v2's `vj-limiter.js` does this on the GPU with no readback). Also about 8 object allocations per head per frame, 960k triangles for a crowd you can barely see, and no GPU timing. The RX 6600 cost is an estimate only. |
| Flash safety | 6.5/10 | See the next section. |
| Tests | 7.5/10 | 54 targeted tests, including the motion limits, laser power sharing, the console-equivalent spreads and phase continuity. Missing from the design's receipts: a determinism hash, the beam-brightness-versus-angle law, a shimmer test, a 3-minute flash run, and a run with the crowd on. |
| Licence | 10/10 | All our own code, no Shadertoy or GPL. three.js r186 still loads from the CDN, and the beam and bloom shaders are local to the page rather than in the house GLSL library. |

**Flash safety in detail.** The good part: the limiter judges every frame, nothing goes over 2 flashes a second anywhere, and there is no red in any of my runs.

The problem: **the limiter does act during the programmed demo, not only under a pad storm.** The builder's "zero interventions" holds only for the 4 seconds his receipt covered.
- With the crowd on, 2 bars of TUNNEL_UP gave 12 interventions, starting at beat position 71.3 when the laser hit lands.
- The same bars with the crowd off gave 0. The cause is the crowd's beat-swinging arms right in front of that camera's lens, on top of the laser hit.
- When the limiter holds, it leaves a visible hard rectangle in the picture: it works on a 4×4 grid of fixed cells. See `limiter-seam-f12-crop.png`.

**What v1 must do, ranked, for Daniel to say it beats the real thing:**
1. **Make the air glow.** The haze must be lit and coloured by every source (beams, washes, LEDs), not a uniform veil, with haze texture at 0.5–3 m drifting through the beams, as in ref-17, 22, 23 and 24. Add a receipt comparing the colour and brightness of the frame's upper third with the refs.
2. **Fix the beams.** Stop them clipping: per-shot exposure and a real bloom halo. Give them a soft profile, falloff with distance, pools where they land on the crowd, colour (lime, violet), and gobo, prism and frost. Hang 6–8 heads per rung, and add the truss rows from ref-18.
3. **Hit the counts.** The full Source v1 rig: 288 heads, 53 lasers with followers, Lasers v2 as the laser brain. Laser looks of 100–300 beams, sheets and cone tunnels in several colours. Raise the laser cap and replace the 32-light limit with clustered lighting.
4. **Build the hero objects.** The figure (with the hero laser in its third eye). Rings as vertical slat halos with spiral, sunburst and chopper poses. The star/mandala formation actually used at drops. Cubes that glow from inside. PA silhouettes and a lit DJ deck.
5. **Add pyro and atmosphere effects.** Gerb crowns, sparkler rows from the cubes, flames, CO2 that catches the lasers, fog bursts. These are the peak moments in the footage.
6. **Make it hear the music.** Engine hits, bands, energy and tension; a section estimator; the build grammar (speed doubling, tilts converging, the strand lowering, a black beat before the drop); position effects on the heads; full-depth chases using phase spread (permitted by the safety rules).
7. **Camera.** Cut every 1–2 bars at drops, as the footage does. Crowd POV with hand and phone silhouettes. Add the corkscrew, ring-thread, side-track, jib tilt-down and roof-establish flypaths, plus glides in breakdowns. Match exposure across cuts, reject shots with occluders or near-black frames, and put a manual camera on the dial.
8. **Flash safety.** Run behind gate v2 (`vj-limiter.js`: on the GPU, no readback, a smooth field with no seams) plus the predictive governor. Fix the crowd-arm flicker at its source by culling or freezing crowd geometry close to the lens. The receipt is a 3-minute run with the crowd on, every shot, zero interventions.
9. **Architecture.** Make the stage a set inside `vj.html` with the VJ sets as LED content; vendor three.js locally; move the beam and bloom shaders into the house GLSL library; remove the per-frame allocations; add crowd LOD and GPU timing; run the real-GPU bench (with Daniel present).
10. **Tests.** Add the determinism hash, the beam-brightness law, the shimmer test, the long flash run with the crowd on, and a look receipt against the refs.

The sheets and frames contain Qlimax footage, so they stay in scratch and must not be committed.

Files are in `<scratch>/stage/judge/`:
- `out/pairs-all.jpg` (also split as `out/pairs-1.jpg`, `out/pairs-2.jpg`; per pair `out/pair-ref-17.jpg` … `out/pair-ref-24.jpg`) – Daniel's 8 frames beside v0
- `out/director-sheet.jpg` (15 frames in `out/director/`) – the director's own camera at 15 moments
- `out/strip-sheet.jpg` (16 frames in `out/strip/`) – one bar of the drop; f12 shows the limiter seam
- `out/limiter-seam-f12-crop.png`
- `out/haze-sheet.jpg` – haze at 15% and 100%
- `out/pairs/*.png` – the 10 posed shots
- `out/series/series-17.json`, `series-23.json`, `series-17.25-crowd-640.json` – frame-by-frame data for the flash and beat analysis
- `judge.mjs`, `analyse.py`, `pairs.py`, `sheet.py` – my harness and analysis, plus the export in `src/`
- the burst logs `out-*.txt`
