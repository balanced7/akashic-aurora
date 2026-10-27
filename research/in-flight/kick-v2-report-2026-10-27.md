# KICK v2 for the virtual Stage: report (2026-10-27)

Branch `stage/kick-v2` (worktree `E:\AI-Setup\.claude\worktrees\kick-v2`, from the VJ V2 integration commit 3b41c1054).

## Pre-registered flash cases (written before any browser run of the new code)

Written 2026-10-27 after the node tests went green and before `stage_verify.mjs` ran a single frame of KICK v2. The
photosensitivity gate is unchanged: the verifier's count (at most 3 flashes a second in each of the 18 windows of a quarter
of the screen or more, luminance and red) and the Stage's final limiter (`flash.js`, untouched).

### Case K1: `kickstorm` (new phase): held top-level kicks, both buttons, a finger wobbling across the strobe band, a tap storm

The demo show, fast-forwarded to bar 14 (two bars before the drop: the build's held laser gate, DROP NOW, the
flythrough, the cut into the drop and the drop's phrase all run underneath), every frame read back, 720 frames (12 s at
60 fps), at half size (640 x 360) so it fits one burst. All kick input goes through the new page-level pad door
(`arsenal:pad`, `arsenal:padlevel` window events), the path the phone's tall pads will use.

| Segment | Frames | Input |
|---|---|---|
| A | 40 to 220 | pad 1 (KICK WHITE) pressed at velocity 1.0 (level 1.0: the strobe) and held 3 s |
| B | 240 to 420 | pad 1 and pad 5 (KICK COLOUR) both pressed at 1.0 and held together 3 s |
| C | 440 to 620 | pad 5 at 0.9, then its level wobbles across the band every half second: 1.0, 0.9, 1.0, 0.92, 1.0 |
| D | 640 to 700 | a tap storm: pads 1 and 5 alternately every 6 frames (10 presses a second) at 1.0, each let go 3 frames later |

Predictions:
- P1 (the gate, pass or fail): the verifier counts at most 3 flashes a second in every window, luminance and red, over all
  720 frames. A failure here is a blocker: I stop and report it, I do not tune the gate.
- P2: in segments A to C (held strobing only) the limiter acts on fewer than 10 % of the frames. Not zero by promise: the
  strobe alone makes at most 4 edges in any 1.01 s (3 at 150 BPM, where it flashes every 2 beats) and leaves the limiter
  a transition to spare, but the show underneath (the laser gate, the cut, the phrase's flashes) shares the windows.
- P3: in segment D (10 presses a second, a rate the player chooses) the limiter acts on some frames. This is its job as
  the backstop; reported, not failed (as the laser pad storm is).
- P4: the worst red count is 0 (the kick paints the theme's white or its colours, and never turns a colour wheel).
- P5: no exceptions and no console errors.

### Case K2: `flash` from bar 30: the demo as programmed, where its KICKs are

The existing `flash` phase starts at bar 14 and its 8 s window ends before the demo's first KICK (the demo presses pad 1
on every downbeat of the drop from its bar 16, that is bar 32 of the plan). A new `--flash-from-bar` option (default 14,
so the phase is unchanged) runs the same phase from bar 30: two bars of the drop, then KICK WHITE at 0.85 (the drive
band: the theme's white and the sweep) on every downbeat, held about a beat, plus the demo's laser hits and FLY-OUT on
the drop's bar 16.

Predictions:
- P6 (pass or fail, the flash phase's own checks): at most 3 flashes a second in every window, red at most 3, and the
  limiter records ZERO interventions (a programmed show stays inside the budget). A failure is a design problem in KICK v2
  for the programmed show, to be fixed in the kick, never in the limiter.

### Addendum, written after the first K1 run and before the second (the case and its predictions unchanged)

The first K1 run (receipt `stage-20261027-194028`) drew 540 of the 720 frames at 640 x 360 (290 ms a frame on
SwiftShader; the burst ran out), so segment D never ran and C only partly. On what it drew: P1 held (worst 2 flashes a
second, window block21; red 0), P2 held (the limiter acted on 0 of the 460 held-strobe frames), P4 and P5 held. It also
showed a design gap: a held kick whose level rose into the strobe band joined the strobe clock only at the clock's next lit
phase (up to about half a second later; in C, 3 strobing frames of 100). Fixed in kick.js before the second run: the first
row to want the strobe joins at once (the clock still keeps 0.263 s from that row's own light-up); later rows still join
only while the clock is lit. The second run uses the same segments and input at 384 x 216 (`--kick-scale 0.3`) so all 720
frames fit one burst; the flash judgement is on 4 x 4 cell means, which do not depend on the frame size to first order.

### Addendum 2, written after the second K1 run (the case and its predictions unchanged)

The second run (384 x 216, receipt `stage-20261027-200612`) still ran out of burst at 600 frames: SwiftShader's cost here
is mostly per frame, not per pixel (242 ms a frame against 290). So K1 was run as the pre-registered 640 x 360 in two
chunks, the way `flash3m` already works: `--kick-from-frame 0 --kick-to-frame 400`, then `--kick-from-frame 330
--kick-to-frame 720` (frames 0 to 329 replayed as logic only, with their input, on the virtual clock), and `--stitch` judges
the 720 stored frames as one run with the same verifier code after checking the 70 shared frames agree.

### The other receipts run unchanged

`load`, `clock` (its "the KICK lift lands on its beat" check is untouched), `engine` (pads 1 and 2 over the fake engine),
`storm` (the laser pad storm), and the new `kick` phase (the pad door, two kicks at once, the live level, the strobe band,
the keyboard's key 5, in the real page; contact frames to the receipt folder for the eye).

## Outcome

KICK v2 is built and every acceptance item holds. Every press of either kick button now changes what is seen, in every
look of the set: 0 dead presses of 400 (5 looks x 2 tempos x 2 buttons x 20 phases), against 38 of 200 on the code before
it. The pinned test was red on that code first. The flash gate was not touched; both pre-registered flash cases pass it
with room to spare (worst 2 flashes a second, red 0).

## The dead-kick table (velocity 0.8, 20 phases across a beat, a press held a quarter beat, measured over the beat after)

Visible = the dealt row's mean rendered level rises by 0.15 or more, or (white kick only) its mean HSV saturation (sRGB)
drops by 0.20 or more toward white. The 0.20 is CIE76 dE 31 on the theme's violet A, 19 on its pink B, 21 on warm; a
just-noticeable difference is about 2.3. The colour kick counts lift only.

Dead presses out of 20, source-v1:

| Tempo | Look | Before (strand lift, cause-1 fix in; one KICK, so both columns are the same press) | After, KICK WHITE | After, KICK COLOUR |
|---|---|---|---|---|
| 128 BPM | intro | 0 (min lift 0.28) | 0 | 0 |
| 128 BPM | build | 6 (min 0.10) | 0 | 0 |
| 128 BPM | drop | 14 (min 0.00) | 0 | 0 |
| 128 BPM | break | 0 (min 0.38) | 0 | 0 |
| 128 BPM | groove | 3 (min 0.13) | 0 | 0 |
| 150 BPM | intro | 0 (min 0.37) | 0 | 0 |
| 150 BPM | build | 0 (min 0.18) | 0 | 0 |
| 150 BPM | drop | 15 (min 0.00) | 0 | 0 |
| 150 BPM | break | 0 (min 0.42) | 0 | 0 |
| 150 BPM | groove | 0 (min 0.22) | 0 | 0 |
| total | | 38 of 200 | 0 of 200 | 0 of 200 |

After, how each press showed: the colour kick always by lift (lowest 0.20, mean 0.62 to 0.77 by look); the white kick by
lift on 13 to 15 presses of 20 (lowest 0.20) and by the shift toward white on the rest (lowest 0.27, 0.68 in the drop and
break). The simulation that first found the dead kicks (source-v0, strand heads only, dead under 0.10, 128 BPM) had
intro 0, build 10, drop 13, break 0.

## What was built

- `arsenal/web/stage/kick.js` (new, pure module): the deck, the two buttons, hold = gate, the live level, velocity's
  animation, the one strobe clock, the visibility judge, the kick block's validation. The programmer runs it as its step 3
  (the playbacks), where v0's strand lift was.
- `arsenal/web/stage/programmer.js`: `pad(kind, vel, pos, {hold})` returns the kick's record; new `padRelease(kind, pos)`
  and `padLevel(kind, level)`; `kickLevel(pos)` kept (now the brightest live kick). The cause-1 fix lives on in kick.js:
  `from = max(onset, press)`, `onset = Math.round(pos)`, and `stats.kicks` still books the onset.
- `arsenal/web/stage/stage.js`: pad 1 = `kick-white`, pad 5 = `kick-colour` (key 5 added; `kick` stays an alias of the white
  one, so a set that maps `kick`, like source-v0, still works); a kick pad is a gate (key-up, note-off or `on: false` lets
  go); `padLevel(n, vel)`; the page-level pad door (window events `arsenal:pad` `{pad, vel, on}` and `arsenal:padlevel`
  `{pad, vel}`, `window.__padDoor = 1` once both listen; pad numbers 1 to 16, velocities clamped to 0..1, a missing `vel` on
  a press reads 0.8); `kicks.push({pressPos, onset, kind, row, band})` (the receipt still reads `onset ===
  Math.round(pressPos)`); the HUD's section row names the live kicks; the scene refuses to start on an invalid kick block;
  the receipts' door gains `level(n, v)` and `state().kick`.
- `arsenal/web/stage/sets/source-v1.json`: the `kick` block and the pad map (`"1": "kick-white", "5": "kick-colour"`).
- `arsenal/web/stage/rig.js`: `rig.kick` carried through `expandScene`.
- `arsenal/web/stage/index.html`: the HUD's key legend (edited by a small script, as the .html hook requires).
- `arsenal/web/stage/README.md`: the controls table and the module table.
- `tests/stage_kick.test.mjs` (new, 11 tests); `arsenal/lanes/stage_verify.mjs` (phases `kick` and `kickstorm`, options
  `--flash-from-bar`, `--kick-scale`, `--kick-seconds`, `--kick-from-frame`, `--kick-to-frame`, `--stitch`).

KICK COLOUR is on pad 5 / key `Digit5`: free in both maps (show0.pads had 1, 2, 3, 4, 6, 7, 8, 9, 10; stage.js KEYPAD had
Digit1-4, 6-9, 0). MIDI pad 1 still kicks (white).

## The deck (`kick.deck`, 17 rows; validation refuses two rows sharing a fixture)

| Row | Zone | Members | Card |
|---|---|---|---|
| truss.heads | truss | 8 heads | pan 90 when dealt dark |
| rings.r0.slats | rings | 384 LED cells | chases round the ring (clock order) |
| lip.heads | lip | 24 heads | pan 90 when dealt dark |
| halo.top | halo | 16 heads | |
| delay.30 | crowd | 8 heads | pan 90 when dealt dark |
| strand.cubes | strand | 144 cells | chases rung by rung |
| rings.r2.slats | rings | 384 cells | |
| vert.towers | towers | 8 heads | pan 90 when dealt dark |
| halo.bot | halo | 16 heads | |
| vert.strips | towers | 224 cells | chases up the columns |
| rings.r1.slats | rings | 384 cells | |
| delay.55 | crowd | 8 heads | pan 90 when dealt dark |
| strand.heads | strand | 12 heads | |
| halo.mid | halo | 16 heads | |
| rings.r3.slats | rings | 384 cells | |
| strand.bars | strand | 768 cells | |
| rings.rims | rings | 1477 cells | |

How it deals: a seeded shuffle-bag (the block's seed 1027 with the programmer's seed). Every row once a round; never the
row the same button had last; never a row any live kick shows (held or still fading), except that a button's re-press
may take over its own fading row as the last resort (v0's one-row KICK always did, and the v0 fallback needs it); and,
when it can, a row in a different ZONE from the last kick's, so consecutive hits hop round the picture. A row is dealt only
if the hit will SHOW on it now: the dealer judges the row's recent peak level (it falls 0.15 a beat, so a row a look
pulses to full on every beat counts as full) and its colour, and asks the visible bar plus 0.03. A row that would not show
it is passed over and stays in the round. When nothing left in the round can show the hit, the round ends early and a
fresh one is shuffled. The zones are distinct regions of the main shots: the truss above, the lip at the deck, the halo's
three altitude thirds and the four rings' slats behind, the towers at the sides, the delay towers over the crowd, the
strand in front.

## What a press does

- WHITE (pad 1) paints LED rows the theme's white (role W, #f0eaff in Source Violet). COLOUR (pad 5) paints LED rows the
  theme's colour (the first of A, B, bumpA that is a colour in the theme); a lit LED whose look colour is already a colour
  keeps it. The paint fades back to the look's colour with the light.
- Moving heads never have their colour wheel turned by a kick. The wheel runs past every slot between at 0.12 s a slot,
  and from lavender to white it passes the red slot. So the white kick takes a head row only while its wheel shows a white
  (saturation under 0.3), the colour kick only while it shows a colour. In practice the colour kick gets the dark beam rows
  (the halo, the towers and the delay towers sit in the theme's violet when dark) and the white kick mostly LED rows,
  plus whichever beam rows a look or phrase has in white.
- The level merges highest-takes-precedence: a kick never dims what the look has brighter.
- Velocity at the press picks the ANIMATION (`kick.bands`):

| Band | Velocity | Heads | LED rows |
|---|---|---|---|
| peak | 0 to 0.45 | come on at the level, stay where they point | come on at the level |
| sweep | 0.45 to 0.85 (keys send 0.8) | a V2 motion (vj-motions.js MotionDealer, class M1 = a bar, beat-locked, looping while held) on tilt, 25 deg x the dealer's amplitude | the same motion as a chase along the row, never under 60 % of the level |
| drive | 0.85 and up (Shift sends 1.0, the demo 0.85) | the same at 50 deg: twice the throw | as sweep |

  Each sweep is cut so its steepest moment asks at most 80 % of the slowest head's tilt speed (270 deg in 1.4 s); its
  acceleration is left to the programmer's motor model (0.2 s to full speed), which rounds a sharp start off as a real
  head does. Measured over 40 deals on the truss: median throw 17 deg (sweep) and 19 to 22 deg (drive), up to 20.5 and
  48.5 deg, never more than 154 deg/s asked, at 128, 150 and 174 BPM. A row dealt dark is aimed by its card (`pan: 90`, so
  the tilt swings left and right as seen from the front of house): the row turning on and panning.
- LEVEL: from the press's velocity (`level.from_velocity` [0, 1]), then live while held through `padLevel` /
  `arsenal:padlevel`, slewed with a 0.06 s time constant (the largest one-frame step for a 0.2 change is about 0.05; 0.4 to
  0.6 settles in about 0.15 s).
- HOLD = GATE: lit while held; let go, it fades with a 0.3 beat time constant; a tap holds an eighth of a beat first. An
  early press waits for its line, a late one lights at once (cause 1). A stuck pad (a lost note-off) lets go after 64 beats.
- STROBE: only while the live level is 0.95 or more. One strobe clock for every kick, locked to the bar: the shortest of
  the divisions 1/2, 1, 2, 4 beats at or under 1.9 flashes a second (the code's cap; a set may only lower it), lit 35 % of
  the period, every edge at least 0.263 s after the last, so at most 4 edges in any 1.01 s. That is a flash every 2 beats
  at 128, 150 and 174 BPM (1.07, 1.25, 1.45 a second) and every beat at 100 BPM (1.67). The first row to reach the band
  joins at once; any other row joins, and every row leaves, only while the clock is lit, so all strobing rows flash
  together and joining or leaving adds no edge; a release freezes the strobe where it is (a dark phase stays dark through
  the fade). LED rows hold still (no chase) while they strobe. The final limiter (`flash.js`) is untouched.

Without a kick block (`source-v0.json`) KICK is v0's strand lift number for number: the strand's 12 heads and 144 cube
cells, 0.6 + 0.4 x velocity, decaying over 0.3 beat from the line, no colour, no motion, no strobe.

## Tests (node)

`tests/stage_kick.test.mjs`, 11 tests, all green:

| Test | What it pins, with the numbers |
|---|---|
| no dead kicks (the acceptance) | the table above: 0 dead of 400; red on the old code first (38 of 200) |
| the deck | the same seed deals the same 90 rows, another seed another order; never the same row twice running, for either button or the deck; no row twice inside a round; the deck reaches at least 15 of its 17 rows |
| hold = gate | held 8 beats at 0.7 the row stays in 0.69..0.71; released, it is at 0.2 to 0.45 of its level a third of a beat later and under 0.01 two beats later; a tap a tenth of a beat early lights from its line, at its level, and goes dark after its eighth of a beat |
| velocity picks the animation | bands at 0.44 / 0.45 / 0.85; a peak moves no head (under 0.5 deg); sweep and drive move them more than 4 deg; drive asks more than 1.5 x sweep's throw and never throws less; no motion asks over 80 % of the tilt motor; an LED row chases (level spread over 0.15 along the ring) |
| two kicks at once | 50 pairs held together in the drop: always two different rows, both lit over 0.25, white LEDs under 0.2 saturation, colour LEDs over 0.3; at least 8 rows visited |
| a fading row is not the other button's | forced at the white kick's fading row, the colour kick is dealt another; the white button's re-press takes its own row over |
| live level | steps 0.2, 0.4, 0.6, 0.8, 0.9 settle within 0.01, each brighter; no frame jumps a third of a step; 0.4 to 0.6 within 200 ms |
| the strobe | at 100, 128, 150 and 174 BPM: no strobe at 0.9; at 1.0 it engages within 400 ms and runs 1.58, 1.08, 1.25, 1.50 flashes a second; it stops below the band; at most 4 edges (3 at 128 and 150) in any 1.01 s; flash.js's FrameLimiter fed the strobing row as the whole screen acts on 0 frames |
| two kicks strobing | white and colour both at 1.0 at 128 and 150 BPM: the rows go dark and light together; the limiter acts on 0 frames |
| without a kick block | source-v0: the strand's heads and cubes, 0.8 at the line for velocity 0.5, then 0.8 e^(-t/0.3) exactly |
| the kick block is checked | source-v1's block valid, no block valid; unknown rows, rows sharing fixtures, a strobe over 1.9 Hz and bands not starting at 0 refused; the dealer's visible bar equals the test's; the roles match the programmer's; pads 1 and 5 |

`tests/stage_programmer.test.mjs`: its 7 tests green, the two KICK tests ("lands on the beat", "pressed late") unchanged.
The whole set, every `tests/stage_*.test.mjs` and `tests/vj_*.test.mjs` on the final code (`node --test
tests/stage_*.test.mjs tests/vj_*.test.mjs`): 364 tests, 364 pass, 0 fail.

## Receipts (arsenal/lanes/stage_verify.mjs, headless SwiftShader under the house GPU lock; receipts under the worktree's state/arsenal/receipts, gitignored)

Each burst took the lock (other lanes held it at times; the runs waited), drew on SwiftShader only, and closed Chrome
before releasing it. No page was opened in a visible browser.

| Run (receipt folder) | Phases | Result |
|---|---|---|
| stage-20261027-202822 (final code) | load, clock, engine | pass, 19 of 19 checks. clock: one beat every 24 frames, the strand's pulse peaks on beat frames (25 peaks, worst 0 frames off), "the KICK lift lands on its beat" (unchanged) passes with the white kicks of the demo's drop (rows vert.towers, strand.cubes, vert.strips...), cuts on bar lines. engine: hello, 140 BPM and the ver re-anchor, pads 1 and 2 reach the rig (kicks 1, laser hits 1), the beat never runs backward |
| stage-20261027-200612 | kick | pass, 8 of 8: `window.__padDoor` is 1; pads 1 and 5 through the door held KICK WHITE (truss.heads) and KICK COLOUR (halo.bot) at once; padlevel 0.3 brought the level to 0.302 in 20 frames; at 1.0 the white kick strobed, back at 0.9 it stopped, the colour kick at 0.8 never strobed; let go, both were gone within two beats; key 5 held KICK COLOUR at 0.8 until key-up; Shift+1 held KICK WHITE at 1.0, strobing; every press booked on its nearest beat; no exceptions |
| stage-20261027-201605 + stage-20261027-202101, stitched in stage-20261027-202317 | kickstorm (case K1) in two chunks at 640 x 360, then `--stitch` | pass, 4 of 4 stitched checks: the chunks agree on all 70 shared frames (max difference 0); frames 0 to 719: worst 2 flashes a second (block21), red 0; the input happened in every segment (A 180 strobing frames, B 180 frames with both rows strobing, C 90 of 180 strobing, D: the 10 taps dealt 9 different rows, ring 1's slats twice, the second time after it had faded); no errors. Each chunk passed its own checks too (worst 2 and 1.5) |
| stage-20261027-201341 | flash (bar 14), storm | pass: flash worst 2 flashes a second (row2), red 0, limiter 0 interventions in 300 frames; storm worst 2 (row2), red 0, limiter 0 in 300 frames |
| stage-20261027-201857 | flash `--flash-from-bar 30` (case K2) | pass: worst 1 (block10), red 0, limiter 0 interventions in 300 frames at 1280 x 720, over the demo's KICK WHITE at 0.85 on drop bars 16 and 17 (frames 192 and 288), FLY-OUT and the laser hits |
| earlier runs, kept for the record | stage-20261027-194028 (load, clock, engine passed; kick failed 3 of 8 because I first set it in the drop, where the demo's own pad-1 press let go of the receipt's held kick; K1 first run 540 frames), stage-20261027-200612 (K1 second run, 600 frames at 384 x 216, gate held: worst 2, red 0) | the K1 runs failed only their frame-count checks; the gate held in both |

The 1280 x 720 flash and storm phases drew 300 of their 480 frames before the burst limit, as their earlier receipts did
(360 on 2026-10-27 morning).

## The pre-registered predictions against what happened

| Prediction | Outcome |
|---|---|
| P1 (gate): at most 3 flashes a second in every window, red included, all 720 K1 frames | held: worst 2 (block21), red 0 |
| P2: the limiter acts on under 10 % of the held-strobe frames (A to C) | held: 0 of 540 at 640 x 360 (the 384 x 216 run: 5 of 520, frames 56 to 60, just after the strobe started over the build's laser gate) |
| P3: the limiter acts on some frames of the 10-a-second tap storm (D) | did not hold: 0 of 60. Each tap went to a different row of a different zone and the rows were small parts of the frame, so no window crossed its budget; the limiter, the backstop, never had to act |
| P4: red 0 | held: 0 in every run |
| P5: no exceptions or console errors | held: 0 in every chunk |
| P6 (K2): the demo's programmed KICKs: at most 3 flashes a second, red at most 3, zero limiter interventions | held: worst 1 (block10), red 0, 0 interventions |

## What I looked at (the contact frames)

From the `kick` phase in the break, FOH_WIDE, 1280 x 720 (state/arsenal/receipts/stage-20261027-200612/kick-*.png): KICK
WHITE on the strand's cubes turns all 24 from violet and pink to white, the plainest change on the screen; KICK COLOUR on
ring 1's slats keeps their violet and lifts them, which is subtler in a wide shot. From the first run (the drop, frames
in stage-20261027-194028): KICK COLOUR lit the side towers' beams in violet straight up, and 30 frames later they had
tilted outward through the sweep; KICK WHITE there landed on LED rows (the rims, the strand's bars), which read less in a
wide shot than beams. These are stills from a CPU renderer; motion and the phone in Daniel's hand are the real test.

## What I could not do

- Lasers are not in the deck. The Stage's laser engine (lasers.js) has no per-group trigger with a gate: its group lines
  are a phrase step's (replaced at every step, anchored on the step, no hold or release). Adding laser rows means a kick
  channel in the laser engine (a list of kick lines it draws after the phrase's, with the kick's level and release) and
  laser-specific flash budgeting; that is its own slice.
- Beam rows cannot go white on the white kick unless they already show white (the wheel rule above), so the white kick
  is mostly LED rows and reads weaker than the colour kick in wide shots. The fix I would propose: model the colour wheel
  as a real wheel, turning the shortest way round (from the theme's deep violet to white is one slot, not thirteen, and
  never via red); that changes every wheel move in the show and needs its own receipts.
- The deck is not camera-aware: in a shot that does not see the dealt row (the delay towers behind a STRAND_FLYTHROUGH
  camera), the press shows off-screen. The dealer's visibility predicate is where a camera check would go.
- The demo show presses only KICK WHITE; KICK COLOUR is exercised by the tests, the `kick` phase and K1, not by the demo.

## Decisions Daniel may want to overrule

1. Velocity bands: peak under 0.45, sweep 0.45 to 0.85, drive from 0.85. Keys send 0.8 (sweep), Shift 1.0 (drive, and level
   1.0, so the strobe).
2. The strobe engages at a live level of 0.95, flashes at most 1.9 times a second, locked to the bar (every 2 beats at 128
   to 174 BPM), lit 35 % of its period. Faster is not possible under the gate by itself; the band and the share are data.
3. One finger, one row: a new press of a button lets go of that button's held kick. In the demo, its scheduled KICK on
   every drop downbeat therefore lets go of a hand-held white kick.
4. The colour kick keeps a lit LED's own look colour when it is already a colour (it lifts it); dark LEDs and near-white
   ones take the theme's A (or B or bumpA). The other reading would be to paint the theme colour over everything.
5. Moving heads keep their wheel colour under a kick (no red pass), at the cost of the white kick on beams.
6. A stuck pad lets go after 64 beats (25.6 s at 150 BPM).
7. Sweeps on tilt only (pan only aims a row dealt dark), sized to 80 % of the tilt motor's speed.
8. The release: a 0.3 beat fade; a tap holds an eighth of a beat.
9. The deck's 17 rows and its zones; lasers not in it.

## Also seen

`tests/vj_lasers.test.mjs` "Round 4: realistic play on fresh seeds" draws a new seed from the clock on every run
(`LASERS_SEED` or `Date.now()`); it failed once on the untouched baseline before any change here ("only 17 held loops",
then "only 16"), and passed in later full runs. It does not touch the Stage.
