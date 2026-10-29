# Kick 5 colour bank and haze fader: review fix round (stage-v3, 2026-10-29)

Daniel's request: "also pressing 5 never seems to change the full stage worth of lights, just a few accent lights. I want
5 to change light groups using a palate across all the elements".

## Outcome

Seven of the nine review findings are fixed: V1, V2, V3, V4, V5, V6 and S3, each with a test that fails on acee2b2c8 and
passes now. S2 is also fixed against the bars this round registered for it. S1 is not fixed: the KICK v2 P2 bar still
fails, at 55 of 540 frames (10.19 %) against a bar of under 10 %. HEAD was at 57 (10.56 %) and the base before the bank
was at 39 (7.22 %). The safety gate itself holds in every run: at most 3 flashes a second and 0 red. Whether to
re-register P2 is Daniel's decision (see "Open for Daniel").

Commits on stage-v3, never pushed:
- cf149f781: the haze fader's curve (V4).
- 72b8fe68c: kick 5's bank fixes: the beams' move in black (V1), steps at least 0.2 s apart (S3), no white or washed-out
  twin in a cycle (V6), spread laser colours (V2, V3).
- 9c6e30332: stage_verify additions: bank B6 and B7 (V5), haze H6, the bankroll phase (S2), and kickpix starting each
  case at bank 0.

Tests: all 221 stage tests pass (`node --test tests/stage_*.test.mjs`); there were 216 before this round. Five tests are
new, and all five fail on acee2b2c8. The existing "every press changes every group" test no longer exempts the
white-resting palettes' lit heads.

All GPU runs used `--gpu --lock-dir E:\AI-Setup\state\arsenal\gpu-render.lock` on ports 8910-8919 and 8946/8947, with
flash protection on and the classic look (automation). The one exception is the HDR bank diagnostic, which used
`--query look=hdr` with protection still on. Receipts are under `state/arsenal/receipts/` in the worktree.

## Findings

| id | reproduced | result |
|----|-----------|--------|
| V1 (high) | yes. Lit heads on their bank slot 4 beats after a press, acee2b2c8: Noir and Titanium 0-4 of 36-44, Rose Fans and Moon Hive the same | fixed. Every lit head now reaches its bank slot in all 4 palettes and all 5 looks. |
| V2 | yes. Molten's lasers turned only between #ebb432 and #dcd838 | fixed. They now turn between amber #cd7d00 and yellow #dcd838, 42 degrees apart. |
| V3 | yes. Titanium's laser banks included grey #c0ccd7 and white #f2f6f9 | fixed. They now turn between sky #4aa8ff and cyan #2ad5e5, and no palette's laser bank holds a white or a grey. |
| V4 | yes. The linear fader saturates: k 3.3 fitted on the review's numbers | fixed. Each quarter of the fader's travel gives 29.5 / 22.9 / 22.3 / 25.2 % of the rise on the GPU. |
| V5 | yes | B6 and B7 added. B1 is kept as registered. HDR run as a diagnostic. |
| V6 | yes. Molten's cycle included peach #ffcc9e; 5 palettes dealt near-whites | fixed. The worst bank's chroma is now 56 % of the look's or more in every colour-bedded palette; it was as low as 27 %. |
| S3 (low) | yes. In node (the review's double.mjs), bank counts at frames 62 and 63 were 1 then 2 | fixed. Two steps never land less than 0.2 s apart. |
| S2 | yes. The review's logs, plus three palettes rerun on the review's scratch phase | fixed against the registered bars BR1-BR3. |
| S1 | yes. P2 was 57/540 (10.56 %) on acee2b2c8 | **not fixed**. P2 is now 55/540 (10.19 %), still over the bar. Cause narrowed below. |

### V1: the move in black (programmer.js `bankDip`, kick.js `canDip`)

When the bank sends a lit head further than one clean wheel slot, all such heads now dip their dimmers to black
together. The wheel moves while they are dark, and the dimmers come back. Each dip lasts at most 12 frames.

The dip starts only when the flash governor has room for the dip and its return (headroom need + 1). Until then the
heads wait, as they did before. In the four white-resting palettes the lit beams now blink once and come back in the new
colour.

### S3: bank steps at least 0.2 s apart

The new setting `governor.bank_min_s` (0.2 s) applies both in the set and as the default. If a press comes inside that
interval right after a held-back step landed, the press counts that step as its own (`gov.bank_taken`). Any other press
inside the interval waits for it to end.

A roll at 8 presses a second therefore steps about 5 times a second.

### V6: no white and no washed-out twin in a cycle

In a palette whose bed has a colour:
- A role with OKLCh chroma under 0.04 is no longer a bank colour.
- A washed-out twin leaves the cycle while more than three colours remain. A twin is a role with less than 0.6 of the
  most colourful role's chroma that sits within 10 degrees of a more colourful role's hue.
- The bed and its partner always stay. Palettes with a grey bed (Noir, Titanium, Moon Hive) keep their greys.

The worst bank's mean lit chroma, as a share of the look's, before and after:

| palette | before | after |
|---|---|---|
| Molten | 69.9 % | 95.1 % |
| Leviathan Royal | 27.4 % | 73.2 % |
| Synthwave Dusk | 35.8 % | 84.7 % |
| Pale Heart | 30.7 % | 71.5 % |

Molten's cycle is now three warm colours 44 degrees apart. It therefore joins the four one-family palettes at the 75 %
LED bar (76.7 % measured). This is a bar change; it is stated in the test and in the commit message.

### V2 and V3: spread laser colours (palettes.js `bankLasers`)

The bank's laser colours are now chosen in this order of rules:
1. Every two colours at least 30 degrees of hue apart.
2. If rule 1 cannot be met, every two colours dEOK 0.1 apart.
3. If neither can be met, dEOK 0.05 apart (the old rule).

Candidates are taken in this order: the palette's own laser colours, its lasers gradient, its kick colour, the heads'
rest and alt slots, its bed, its partner, and its highlight. Further candidates are added while no starting point would
move every laser off its own colour on the first press.

### V4: the haze fader's curve (atmos.js `hazeCurve`)

The fader position f now sets the haze through `hazeCurve(f) = -ln(1 - f (1 - e^-3)) / 3`, the inverse of the haze's
visible saturation. F5 at 0 is still exactly no haze, and F5 at 1 is still full (SIGMA_MAX). The hazers' plumes follow
the same curve.

The page's default F5 moves from 0.55 to 0.85, which gives the same density as the old default (within 0.1 %). The
default look is therefore unchanged.

### V5: two new bank bars

- **B6:** at least 70 % of lit pixels change colour by dE76 > 10.
- **B7:** every bank group lit in both pages moves its mean colour, measured on the programmer's own arrays, by
  dEOK > 0.04.

The bank phase was also run with `--query look=hdr` as a diagnostic.

### S2: the bankroll phase

The review's scratch roll phase is now a lane phase. Its three bars were registered before its first run in the lane:
- **BR1:** kick 5 taps alone never make the limiter act.
- **BR2:** at most 3 flashes a second and no red.
- **BR3:** limiter frames at or under the base before the bank.

My exploratory runs of the review's scratch copy came before this registration.

### S1: what it is and what it is not

Every experiment below is a kickstorm run on the GPU (P2 limited frames out of 540):

| run | P2 limited frames |
|---|---|
| this round's code | 55 |
| no bank step at all (the bank kind kept, `bankAdvance` disabled) | 16 |
| dips disabled | 55 |
| lasers not following the bank | 57 |
| LEDs held at exactly the look's luminance | 62 |
| the look's white kept white | 55 |
| the dealt area bursting in the old palette lift | 62 |

So the step at frame 240 drives it: that is segment B, where pads 1 and 5 are held at the top. It is not the LEDs'
luminance, the lasers, the heads' dips, or white-to-colour. The governor and limiter feedback is chaotic: variants
range from 16 to 62 frames.

The review allowed "either restore P2 or re-register it with Daniel". I could not restore it at the root. None of these
diagnostic variants were committed.

## GPU receipts against the pre-registered bars

| receipt | bars | result |
|---|---|---|
| haze (stage-20261029-142418) | H1-H6 | all PASS; quarters 29.5 / 22.9 / 22.3 / 25.2 % |
| bank, classic (142444), Source Violet | B1 | FAIL 1.7-3.8 % (kept as registered) |
| | B2 | FAIL: 65.0-87.2 % of laser pixels changed; 4 of 8 cases are under 80 % |
| | B3 | PASS |
| | B4 | PASS (limiter 0) |
| | B5 | PASS 18.1-41.4 % |
| | B6 (new) | PASS 78.9-88.4 % |
| | B7 (new) | PASS: 8 of 8 lit groups moved in every case |
| bank, HDR diagnostic (142512) | B6 | 87.5-96.7 % |
| | B7 | PASS |
| | B2 | 66.7-92.4 % |
| | B1 | 1.7-3.8 % |
| bankroll (142553) | BR1 | PASS: R1 limited 0 in all four palettes |
| | BR2 | PASS: worst 2.5 flashes/s, red 0 |
| | BR3 | PASS: limited frames 16 / 76 / 62 / 93 against base 168 / 80 / 117 / 130 (Source Violet, Synthwave Dusk, Lime Rows, Violet Hold); acee2b2c8 measured 162 / 149 / 68 on the last three |
| flash (143118) | 3 flashes/s gate | PASS: worst 2, 0 interventions |
| storm (143118) | 3 flashes/s gate | PASS: worst 2, 0 interventions |
| kickstorm, whole (143208) | P1 | PASS: worst 3, red 0 |
| | P2 | **FAIL** 55/540 = 10.19 % (bar < 10 %) |
| | P3 | 0 frames |
| | P4, P5 | PASS |
| | P8 | PASS 0/180 |
| kickstorm in chunks + stitch (143138, 143145, 143152, 143200) | P1 | PASS: worst 3, red 0 |
| | P2 | **FAIL** 57/540 = 10.56 % |
| | P8 | PASS 0 |
| | input in every segment | PASS |
| kickpix, 5 looks (143559-143659) | control | PASS in all five looks |
| | R4, R5 | PASS |
| | R1 | PASS in 4 looks; build FAIL |

About the kickpix results:
- The control check failed in every look on acee2b2c8 as well (build 30.7-91.4 %), because the bank latches. Each case
  now starts at bank 0.
- The build R1 failure is one case: kick 1 WHITE on HEAD_ORBIT's rings, at 3.4 % of the screen. It measured 5.8 % on
  acee2b2c8. This is the white kick on the build's white rings, not the bank.
- About P3: the lane's note calls P3 a prediction ("the limiter being the backstop for a tap storm"). Its `held` flag is
  true when the limiter acts, so 0 frames reads as "not held".

## Open for Daniel

1. **KICK v2 P2 (S1).** P2 is now 10.19 % against a bar of under 10 %. The safety gate holds (3 flashes a second, 0 red,
   in every run). Two options:
   - Re-register P2 for the colour bank.
   - Have the first whole-stage step wait while a held strobe is coming. That would change his "lands on the next
     frame".
2. **Bar change in the bank tests.** Molten moved to the one-family 75 % LED bar (76.7 % measured), after the V6 pastel
   rule shortened its cycle.
3. **B1 and B2 stay registered and failing.** B1 cannot be met by a one-family palette; B6 and B7 are the bars that hold
   for every palette. B2's laser pixels: 65-87 % on classic and 67-92 % on HDR.
4. **The haze default is now 85 % on the HUD.** It is the same density as the old 55 %. Each quarter of the fader's
   travel now shows about the same change.

## Try it

Open `http://127.0.0.1:<port>/web/stage/index.html?demo=1`; Vandor will serve this branch. Then:

1. Press **5** (the key or pad 5) a few times. Every press re-colours the whole stage with the palette's next bank: rings,
   halo, strand, towers, beams and every laser. Kick 5's own area also bursts. Fast rolls step at most 5 times a
   second.
2. Add `&palette=noir`, or `&palette=titanium`, to the URL and press 5. The beams blink to black for a moment and come back
   in the other colour of their pair: white to violet and violet to white in Noir, white and sky blue in Titanium. Before
   this round they never changed.
3. Add `&palette=molten` and press 5. The lasers switch between amber and yellow on every press.
4. Move **F5**. Zero is no haze at all and the top is full haze. Each quarter of the fader's travel now changes the haze
   about as much as any other. The page starts at 85 %, the same haze as the old 55 %.
