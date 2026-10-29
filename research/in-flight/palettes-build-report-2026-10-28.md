# The thirty palettes, built: the build report (2026-10-28)

Branch `palettes` (worktree `.claude/worktrees/palettes`, from `8d26641a5`). Design: `research/in-flight/palettes-2026-10-28/DESIGN.md`
(read from the main checkout, where that folder is untracked).

Daniel, verbatim (2026-10-28): "when i tried the color options on my phone the lights just turn amber, the dns strands just
change amber sometimes or dont change at all, i love the built in gradients you built for the dna strands can we make more
high quality color theme presets and animations. I want us to have 30 color palates that are high quality and what is used
for driving the colors so it always looks careful and deliberate, perhaps for the lights we can also have color gradient
patches as well as single colors". On the colour kick: "I want us to be able to have both, sometimes white is good other
times color is good".

## 1. Pre-registered acceptance (written and committed before any headless run)

The numbers to beat are KICK round 2's (`research/in-flight/kick-v2-report-2026-10-27.md`, "Round 2: the final receipts").

| id | check | bar | my prediction before running |
|---|---|---|---|
| K1 | `stage_verify kickpix`, the 46 cases at 832 x 384, coverage = share of the frame moved by dE76 > 10 (the larger of the quarter-beat and one-beat frames), run per look with `--pix-looks` if a burst truncates | median >= 44.4 % | 40-50 %. The colour kick now lifts each cell to a lighter colour of its own palette (+0.16 to +0.34 OKLab L) instead of a contrasting hue, so colour-kick cases should stay near round 2; the white kick on the halo no longer turns the halo's wheel to the bright warm-white slot (it punches violet), so the four halo white-kick cases may drop |
| K2 | the same 46 cases | minimum >= 8.9 % | 9-20 %. The weakest round-2 case (break, DJ_OTS, colour kick on the strand, 8.9 %) should rise: the strand heads now rest on violet (beamA) and step to magenta, where before they kept indigo |
| K3 | the same | latency 1 frame in all 46; presses_unlit 0; every control frame identical with and without the kick | held |
| A1 | amber: `arsenal/lanes/palette_amber.mjs` (inventory.md section 4's method: per palette and look, 12 colour-kick presses a bar apart, held 2 beats at velocity 0.7, the kicked heads' wheel slot read 1.5 beats in) | share of colour-kicked moving-head frames on the warm-white slot (12): 0 % in all 30 palettes (none declares it) | 0 % (already measured by the node test while building; the receipt is the full method) |
| A2 | the same receipt, white kick | 0 wheel moves on white-kicked heads | 0 |
| A3 | the same receipt | colour-kicked heads on a palette colour (a slot within 45 degrees of a palette hue) >= 90 % in the 27 palettes whose heads can lift; the 3 white-resting palettes (Rose Fans, Titanium, Noir) never take a colour kick on the heads-only halo | held |
| F1 | `stage_verify flash` (bar 14), 1280 x 720 | at most 3 flashes a second in every window, red 0, limiter 0 interventions | held (the default palette's colours are a little brighter on the strand dots and lifts, and the white kick is the palette's tinted white) |
| F2 | `stage_verify flash --flash-from-bar 30` (case K2) | the same, zero interventions | held |
| F3 | `stage_verify storm` | the same | held |
| F4 | `stage_verify kickstorm` in chunks (frames 0-300, 220-520, 420-720, 640-960, 640 x 360) + `--stitch` | P1 worst <= 3 flashes a second, red <= 3; input in every segment; no errors | held |
| F5 | the stitched kickstorm | the limiter acts on <= 7.8 % of the held-strobe frames (A to C) and <= 6.1 % of K3's rapid-tap frames (KICK round 2's loads) | held-strobe about the same (the strobe is unchanged); rapid taps the same or lower (a colour re-strike is now a swap between two luminance-matched lift colours, ratio 0.96 in Source Violet) |
| N1 | `node --test tests/stage_*.test.mjs tests/vj_*.test.mjs` | every test passes (vj_lasers "Round 4" is a known clock-seeded flake: rerun twice before calling it) | held |
| N2 | the new tests (`tests/stage_palettes.test.mjs`) | the validator (all 30 pass, its faults refused, Molten loads), palette switching (16-bar landing, crossfade, dip), the wheel plans, the strand gradient under kicks | held |
| V1 | the contact sheet: `stage_verify palettes` renders each palette's Stage (drop look, FOH_WIDE) headless; I look at all 30 | every palette reads as its swatch, careful and deliberate; any that looks wrong on the rig is described and fixed | unknown: the design was never seen on the rig |
| P1 | the headless phone check (`stage_verify phonebar`, 915 x 412, touch): the PALETTE pad and the colour strip's wash of the lift colours | every check passes; the page announces the palette only on a change; the frame time with the bar within 2x (or +40 ms) of without | held |

Everything headless runs on SwiftShader under the house GPU lock, at below-normal priority.

## 2. Results

(filled in below after the runs)
