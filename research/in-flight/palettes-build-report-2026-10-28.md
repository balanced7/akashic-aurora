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

## 2. What was built

| piece | what it does now |
|---|---|
| `arsenal/web/palettes.json` | the design's 30 palettes, copied; one build change (Moon Hive, section 6), recorded in the palette's own `changes` |
| `arsenal/web/palettes.js` (new, pure) | the shared validator (the VJ red rule at 0.78 for anything that moves, 0.80 for a held pin; the red sector; the strand pair; the kick's contrast; the matched re-strike ladder; decay chroma; the amber guard; the wheel plan checked with the kick's own wheel rules; every gradient's 32 samples; lasers; the KeyLab pad rule). A palette that fails is refused with its reasons and the rest load. Also the gradient tables, `stageTheme`, `planOf` (the wheel plan), `neighbours` / `needsDip`, `landingPos` (the next 16-bar line), `stepPalette`, `vjTheme`. |
| `stage/programmer.js` | roles gain `accent`, `accent2`, `accentLift`, `pin`; the role array keeps its identity (the rings hold it); the wheel plan (a head shows only its palette's slots; every wheel move, the look's too, takes the red-free short way; a dark head snaps; a lit head asked for more than one clean slot waits up to a beat for black); splits and pins per member (a split's cells show the second family, a strand wing for Neomuna; a pin's cells hold their colour and follow the scene's level slowly, never kicked); 3-stop strands sampled from the palette's own gradient (Lantern Walk, Aurora; two-stop strands keep the linear mix that made the loved helix); the palette's tempo on the helix and the ring ladder; Lantern Walk's walk; `beginPalette` (a neighbour crossfades in OKLCh over 4 bars, anything else cuts on the line through a one-beat dip with the colours and wheels changing at the bottom); the colour kick's per-cell lift buffer |
| `stage/kick.js` | the white kick is the palette's white and never turns a wheel; the colour kick lifts each cell's own roles inside the palette and keeps its mix (the helix stays a helix), and every colour effect on the area jumps a quarter cycle and eases back over a beat; the re-strike swaps the luminance-matched ladder; heads step one clean slot by the plan; the dealer never gives the colour kick an area of heads that cannot change colour, never gives the white kick an area of heads that cannot show white, deals the strand at least once in three presses while it shows, and of the areas that show takes the one whose screen share times changed share is largest. The set's fixed 8-colour list, `contrast_deg` and its own white are retired (`validateKick` refuses them) |
| `stage/effects.js` | an effect's `kickJump` (the colour kick's pattern jump) |
| `stage/lasers.js`, `stage/lasers3d.js` | the red fallback is the palette's white (it was a warm white, one of the amber paths); a fan of the first two colours takes a colour per beam along the palette's laser gradient |
| `stage/stage.js` | `?palette=` (then `?theme=`; a set theme that is not a palette still loads), `show.palette`; key P / Shift+P and the pad actions `palette-next` / `palette-prev`, landing on the next 16-bar line; the lasers and the air follow the palette; the window event `arsenal:palette` (on change only) and `window.__palette`; `window.__stage.palette(id, {now})` for receipts |
| `stage/sets/source-v1.json` | `show.palette: "source-violet"`; KeyLab pads 11 and 12 = palette next and previous; the strand heads on `beamA` (the palette's rest slot) in the four looks that had them on white; the kick block's colour list and white removed |
| `lib/touchbar.js` | the PALETTE pad (presses P; its small line shows the palette, or "-> the next one" while one is queued); the colour kick strip wears a faint wash of the palette's two lift colours; both event-driven, nothing per frame |
| `vj-themes.js`, `vj.js` | one library: `fetchLibrary` also loads palettes.json and `withPalettes()` adds each palette as theme `pal-<id>` in family tabs `pal-violet` ... `pal-neutral` (Shift+F1-F6 on the page; off the fader, which is full), with the Stage's colours, laser pair and pad stand-ins; the merged library passes `validateLibrary` with no errors and no warnings |
| `arsenal/lanes/palette_amber.mjs` (new) | the amber receipt, node only |
| `arsenal/lanes/stage_verify.mjs` | phases `palettes` (the contact sheet) and `phonebar` (the headless phone check) |
| tests | `tests/stage_palettes.test.mjs` (14), `tests/vj_palettes.test.mjs` (5); `stage_kick` and `stage_looks_wave1` updated to the palette kick |

## 3. Deviations from DESIGN.md, and why

1. **The old set themes stay in the set file.** The page takes palettes first; `genesis-indigo`, `vex-conflux` and
   `anti-sun` (wave-1 themes that are not palettes) still load by `?theme=` with their own roles, and take the same kick
   rules from their roles (bumpB, bumpA). The tests that pin them (and the VJ library's Dreaming City) are untouched.
   Retiring them is Daniel's call (choice 6).
2. **The palette tempo drives the colour motions only** (the strand's helix and the ring ladder: drive 16/8, slow 32/16,
   raw 8/4, still 32 and a ladder held to one turn in 16 bars, walk 16/16). The brightness chases keep the set's own rates:
   they carry the flash budget the KICK rounds were measured on. The raw palettes' "lift band over a 40 % floor" is not built.
3. **A role was added: `accent2`** (a split's second stop: Neomuna's pink wing partner, otherwise the accent gradient's
   first stop), so a split's cells keep a two-colour gradient in their own family.
4. **The re-strike's colour step on the VJ page** stays the VJ's own (`colourSequence`: the laser pair, then white), not
   the design's kick, highlight, accent lift: the VJ's hits are lasers and pad effects, and its sequence already steps a
   palette theme's own colours.
5. **The KeyLab control is a pad pair, not the family tabs:** pads 11 and 12 in the Stage's pad map step the palette (the
   KeyLab's numbers there are a guess until Daniel binds them); on the VJ page the palette families are Shift+F1-F6.
6. **A palette change dips through black, not through `deep`:** the rig's grand master dims over the half beat before the
   line and comes back over the half beat after, the colours and wheels changing at the bottom (so a head's wheel never
   turns while it is lit). The air (ambient) stays the old palette's deep until the line.
7. **Pins** are held by a slow follower (1.2 s) on the scene's level rather than at a fixed level, so a pin on a dark group
   stays dark; their frame share was not measured on the bench (the pins sit on `strips.v1`, which no look lights).
8. **Lantern Walk's walk** moves role A only (the rims, bars and slats the bed colours); its strand keeps the 3-stop ramp.
9. **Moon Hive's wheel plan changed** after the contact sheet (section 6).

## 4. The results against the pre-registered bars

Every headless run: SwiftShader, the house GPU lock, below-normal priority, test-band ports. Receipts named below are under
`.claude/worktrees/palettes/state/arsenal/receipts/` (gitignored) unless they say scratchpad.

| id | bar | result | verdict |
|---|---|---|---|
| K1 | kickpix median >= 44.4 % | 27.2 % (with the dealer changes; 26.2 % first run); the final code's run is pending (renders paused for Daniel's game) | **NOT MET** (section 5) |
| K2 | kickpix minimum >= 8.9 % | 8.6 % (break, DJ_OTS, colour kick on the strand: round 2's weakest case, 8.9 % there) | **NOT MET**, by 0.3 points |
| K3 | latency 1 frame in all 46, no unlit press, every control frame identical | held in both runs: 1 frame in 46 of 46, 0 unlit, every control frame identical | met |
| A1 | colour-kicked head frames on the warm-white slot ~0 % unless declared | 0 of 59,960 in all 30 palettes (before: 66-70 % in the violet themes; the halo 100 %) | met |
| A2 | white-kicked heads: no wheel moves | 0 of 62,848 head frames | met |
| A3 | colour-kicked heads on a palette colour >= 90 % where heads can lift | 97.7-98.6 % in the 26 that can; the 4 white-resting palettes never colour-kick the heads-only halo | met |
| F1-F5 | flash, flash 30, storm, kickstorm + stitch, limiter loads | pending: the GPU lock is held while Daniel plays ("Daniel is gaming: renders paused"); not run on any palette code yet | **NOT YET RUN** |
| N1 | every stage_* and vj_* node test | 405 of 405 (before the last test was added; 14 of 14 in stage_palettes after it) | met |
| N2 | new tests | stage_palettes 14, vj_palettes 5: all pass | met |
| V1 | the contact sheet, all 30 looked at | done; Moon Hive fixed; two observations (section 6) | met |
| P1 | headless phone check | 8 of 8 (stage-20261029-031606): the pad shows the palette, the strip wears the lift colours, a touch queues the next palette for the 16-bar line, one event per change, frame time with the bar 160-167 ms against 167 ms without (SwiftShader), a finger on the strip kicks in the lift colour, the landing updates the pad and the strip, no errors | met |

## 5. K1 and K2: the kick pixel metric did not reach round 2's, and why

I stopped tuning and report it rather than weaken the bar. The kick pixel metric (`kickpix`: the share of an 832 x 384
frame whose colour moves by dE76 > 10 when a kick is pressed, 46 cases) measures how BIG the change on the screen is.
Round 2 reached its median with two things the palette design removes on purpose: heads that land on the wheel's bright
warm-white slot (the amber Daniel saw) and a colour list chosen to be 90 degrees of hue away from the area (yellow, green
and orange against violet). The palette kick lifts each cell to a lighter colour of its own family instead.

The same 46 cases, the same harness, this machine:

| code | median | minimum | under 10 % | latency | receipts |
|---|---|---|---|---|---|
| round 2 as it is (`8d26641a5`, exported, untouched) | 44.4 % (43.3 / 45.5) | 8.9 % | 1 | 1 frame, 46 of 46 | scratchpad `receipts_base`: it reproduces the KICK report exactly, so the harness is sound |
| round 2 with ONE change: a kick may not send a head to the warm-white slot (12) | 36.4 % (35.9 / 36.8, 38 cases: the build look's burst found the lock taken) | 8.9 % | 1 | 1 frame | scratchpad `receipts_nocto` |
| the palettes, first run (`70176b7ca`) | 26.2 % (26.0 / 26.4) | 8.6 % | 1 | 1 frame | stage-20261029-031834 ... -033018 |
| the palettes with the dealer changes (`c54d0e304` less the last fix) | 27.2 % (26.9 / 27.5) | 8.6 % | 2 | 1 frame | stage-20261029-032619 ... -033152 |
| the palettes, final code | pending (renders paused) | | | |  |

About 8 points of round 2's median were the warm-white slot itself; most of the rest is the lift. Per case, the same area
dealt in both codes:

| case (look, shot, kick, area) | round 2 | palettes | what changed |
|---|---|---|---|
| drop, TOPDOWN_GODVIEW, colour, strand | 75.7 % | 37.5 % | yellow on the violet helix, against pink and lilac on it |
| groove, PROFILE_GRAPH, colour, strand | 91.5 % | 18.5 % | the same |
| intro, CRANE_RISE_REVEAL, colour, rings | 82.3 % | 51.3 % | the same on the ring slats |
| intro, FOH_WIDE, white, beams | 45.9 % | 26.4 % | the beams' heads went to the warm-white slot; now they stay magenta |
| intro, FOH_HOLD_ZOOM, white, halo | 25.9 % | 16.0 % | the dark halo lit warm white; now it lit violet (and the final dealer no longer gives the white kick the halo) |

In emitted light the palette lift is a smaller step by design: Source Violet's violet to its pink kick is dE76 75 and its
magenta to its lilac highlight 62; round 2's yellow on violet was 183 and green on magenta 196. On the screen, the bright
LED kinds (ring slats and rims at 25,000-30,000 nits, strand dots at 60,000) clip to white cores in every palette, so a
lighter colour of the same family changes mostly the glow around them.

What I tried inside the design (each measured, each kept): the dealer weighs an area by its screen share times the share
of its members the hit changes; the white kick is never dealt an area of heads alone that cannot show white (truthful:
it moves white kicks onto the LED areas); the strand rule never forces the strand on one button twice running. The median
went from 26.2 % to 27.2 %. Nothing else inside the rules moves it far: on the violet palettes there is no brighter clean
slot for a head (the violet run 9-12 ends in the pink and the warm-white slots), the renderer conserves a beam's flux (a
wider zoom is dimmer per pixel), and frost and prisms are not drawn.

Reaching 44.4 % would need one of: heads moved to white or to a bright slot in black (the colour lane's way, which broke
the flash gate on rapid taps), the warm-white slot back, or kick colours far outside the palette (the contrast list). All
three reverse what Daniel asked for, so they are his call (section 8, choice 1). The kick is still always visible: no
press unlit, every press on the first frame, every case over 8.6 % of the screen.

## 6. The contact sheet: all thirty, looked at

`stage_verify palettes`: each palette landed through the page's door, the drop look from FOH_WIDE, two seconds to settle,
drawn at 640 x 360; with `--pal-kick` the same view with a colour kick held on the rings and on the strand. The sheets are
in `research/in-flight/palettes-build-2026-10-28/` (our own renders, not Daniel's footage).

What I saw, against each swatch:

- **Read as designed:** Source Violet (the loved violet-to-magenta helix, magenta and violet beams), Violet Hold (magenta
  rings, lilac strand), Dreaming City, Spiral Tunnel, Source Ring, Lantern Walk (blue to magenta through its violet middle),
  **Lime Rows** (the lime truss and lip rows against the violet bed: the split reads at once), Sakura Lavender, **Synthwave
  Dusk** and **Leviathan Royal** (the gold rims ring the violet), Sparkler Pink, **Orion Nebula** (teal ring slats against
  magenta heads), **Neomuna Neon** (one backbone cyan, the other pink: the wing split works), Cyan Hold, Endymion Blue,
  Cherenkov, Blue Hour Amber, Glacier, Pale Heart (white-gold rims), Abyssal Glow, Tangerine Teal, Acid Raw, Emerald Laser,
  Aurora Borealis, Throne World, Molten (the one warm palette, declared), Titanium, Noir.
- **Wrong on the rig, fixed: Moon Hive.** It read as an all-green palette: its heads rested on the wheel's green slot, far
  more saturated than the hive green, and filled the hero view, so the bone-grey bed vanished. Its heads now rest on white
  with green as their alternate (punch only), the grammar Titanium and Noir use; it reads neutral plus one green accent.
- **Observation for Daniel (choice 2):** the seven blue palettes all rest their heads on the sky slot, and the beams
  dominate the hero view, so on the rig those seven read closer to each other than their swatches; the strand and the
  rings tell them apart. A colour-mixing head would let each show its own blue.
- **Observation:** the ring slats and rims clip to white cores in every palette; their colour lives in the glow, so a colour
  kick on the rings reads as a tinted white flash (pink in Source Violet, ice in Violet Hold and Glacier). On the strand
  cubes and on the heads the colour kick reads as colour. (A renderer change, a hue-preserving display curve for the LED
  kinds, would fix this for every palette; not in this build.)

## 7. The phone, the amber, the flash

**The flash runs are pending**: the house GPU lock has been held since 03:53 UTC by "Daniel is gaming: renders paused until he is done". The palette changes that touch the flash budget are covered by node tests meanwhile: the kick's strobe, comb, governor and roll tests (stage_kick, all pass on the palette kick), and a new test that a palette change (the one-beat dip at 128, 150 and 174 BPM, and a crossfade) never makes the final limiter act on the whole rig as one frame (it swings 0.53 to 0 to 0.97 and counts two transitions).

**The amber (A1-A3).** `arsenal/lanes/palette_amber.mjs`, inventory.md section 4's method (per palette and look, 12
colour-kick presses a bar apart, the deck dealing as it deals, held 2 beats at velocity 0.7, the kicked heads' slot read
1.5 beats in; the same for the white kick), on the final code:

| | before (`measure_kick_colour.mjs` on `8d26641a5`) | after (all 30 palettes) |
|---|---|---|
| colour-kicked head frames on the warm-white slot | Source Violet 69.2 % (halo 100 %, beams 56.1 %, strand 15.4 %), Dreaming City 66.3 %, Genesis Indigo 69.8 % | 0 of 59,960 |
| white-kicked heads whose wheel moved | toward white, which from violet is the warm-white slot | 0 of 62,848 |
| colour-kicked heads on a palette colour | | 97.7-98.6 % in the 26 palettes that can lift; Rose Fans, Moon Hive, Titanium and Noir rest on white by their plan and never take a colour kick on the heads-only halo |
| unlit presses | | 0 |

## 8. Daniel's open choices

1. **The kick's size against its care.** The palette kick is a lift inside the palette; on the screen it changes about 27 %
   of the frame where round 2's contrast-and-warm-white kick changed 44 %. Keep it (my recommendation: it is the careful,
   never-amber kick he asked for; judge it on his phone and an OBS recording), or ask for a bigger one: (a) a "vivid" kick
   colour per palette, further from the bed (a palette data change, re-validated), or (b) heads that move to a bright slot
   in black (the colour lane's approach, which cost flash budget on rapid taps).
2. **Wheel heads or colour-mixing heads.** With wheels, the seven blue palettes share one head colour on the rig, and Rose
   Fans, Moon Hive, Titanium and Noir can only punch their heads. A colour-mixing head type would let every palette show
   its own head colours (the renderer already takes rgb per head).
3. **The KeyLab binding for the palette step** (pads 11 and 12 in the Stage's pad map are placeholders until he picks the
   buttons), and on the VJ page Shift+F1-F6 for the palette families.
4. **The phone's colour strip** now wears the palette's two lift colours (a faint wash, changing only with the palette).
   Keep, or plain grey as before.
5. **Warm.** Molten is the only warm bed; five palettes hold a warm split and two a warm pin, never as a kick (the
   design's default, kept).
6. **The three wave-1 set themes that are not palettes** (Genesis Indigo, Vex Conflux, Anti-Sun): keep them reachable by
   `?theme=`, make them palettes, or retire them.
7. **Moon Hive's fix** (heads on white): keep, or back to the design's green heads.

## 9. Commits and files

- `1d4ac9484` Palettes test: a palette change (the one-beat dip at 128, 150, 174 BPM, and a crossfade) never makes the final limiter act
- `61be483de` Stage README: the palettes (?palette=, key P, the PALETTE pad, KeyLab pads 11 and 12, the 16-bar landing, the two kicks)
- `c54d0e304` Palettes: one library for the Stage and the VJ page; the kick dealer tells the truth about white and colour
- `70176b7ca` Palettes, the contact sheet's fix: Moon Hive's heads rest on white (green their alternate), punch only
- `b2991c874` Palettes: thirty palettes drive every colour on the Stage (shared validator, lift kick, wheel plans, 16-bar switching)
- (this report's own commit follows them)

Files: `arsenal/web/palettes.js`, `arsenal/web/palettes.json`, `arsenal/web/stage/{programmer,kick,effects,lasers,lasers3d,stage,formations}.js`,
`arsenal/web/stage/sets/source-v1.json`, `arsenal/web/stage/README.md`, `arsenal/web/lib/touchbar.js`,
`arsenal/web/{vj-themes,vj}.js`, `arsenal/lanes/{palette_amber,stage_verify}.mjs`,
`tests/{stage_palettes,vj_palettes,stage_kick,stage_looks_wave1}.test.mjs`, this report and its sheets in
`research/in-flight/palettes-build-2026-10-28/`.
