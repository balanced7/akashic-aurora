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

---

# ROUND 2 (2026-10-27 evening): override, colour at high intensity, areas, judged on the screen's pixels

Daniel, on his phone with the thumb strips, verbatim: "The kick buttons dont really change anything.  Can we make the kick
buttons override existing scene lights and cause them to change color with a high intensity"

The diagnosis (the conductor's, and mine to own): round 1's acceptance measured the dealt row's dimmer lift (>= 0.15) or
its saturation shift, not what the screen shows. One row (vert.strips, halo.bot) changing by 0.2 inside a busy, bright,
moving scene on a 6-inch phone reads as nothing. The metric was ours and it was too lenient.

## Round 2 pre-registration (written before any round-2 measurement, the round-1 code's included)

### The pixel metric (new phase `kickpix` in stage_verify.mjs)

- The page in engine mode on the receipt's fake engine (no beats sent: the grid free-runs at 150 BPM on the virtual
  clock, the show stays in its groove section with no demo pads and no phrases), at 832 x 384 (the conductor's phone
  checks), quality=receipt. Each look of the set (intro, build, drop, break, groove) is set on the programmer in turn.
- The camera is pinned (setShot, u = 0.5) on the main demo shots of that look: intro FOH_HOLD_ZOOM, CRANE_RISE_REVEAL,
  FOH_WIDE, TRIBUNE_34; build STRAND_FLYTHROUGH, FOH_WIDE, HEAD_ORBIT, TUNNEL_UP; drop TUNNEL_UP, TOPDOWN_GODVIEW,
  TRIBUNE_34, HEAD_ORBIT, FOH_WIDE, CROWD_POV, WORM_RING; break HEAD_ORBIT_SLOW, DJ_OTS, FOH_WIDE, CROWD_POV; groove
  FOH_HOLD_ZOOM, TRIBUNE_34, PROFILE_GRAPH, HEAD_ORBIT. Each shot gets a white case and a colour case: 46 kick cases.
- The SAME frames are rendered twice on the deterministic virtual clock: page A with no kick, page B with the kick pressed
  through the pad door (velocity 0.8, held) at the case's beat. Each case reads a control frame just before the press
  (it must be identical in A and B) and two frames after it (a quarter beat and one beat).
- A pixel CHANGES when its colour moves by more than CIE76 dE 10 (sRGB to CIELAB, D65) between A and B. A just-noticeable
  difference is about 2.3 for two still patches side by side; a phone 40 cm away, a moving picture and a glance need
  several times that, so 10 (about four JNDs) is the "you can see it changed" bar. Coverage at dE 5 and 20 is reported
  beside it.
- A case's COVERAGE is the larger of its two frames' changed fractions.

Predictions:
- R1 (the gate, pass or fail for round 2): EVERY one of the 46 cases changes at least 10 % of the screen's pixels. 10 % of
  an 832 x 384 frame is about a 180 x 180 pixel patch, a thumbnail's worth on a phone: obvious. The distribution
  (minimum, median, maximum per look and kind) and the worst shots are reported.
- R2: on the round-1 code (HEAD 10c27410d's web files, snapshotted to scratch before any round-2 edit) R1 FAILS: most
  cases under 10 %.
- R3: every control frame is identical between A and B (coverage 0): the comparison is sound.

### Flash cases for round 2

K1 (held top-level kicks, both buttons, the level wobbling across the strobe band, a 10-a-second tap storm) and K2 (the
demo's programmed KICKs from bar 30) are re-run unchanged, with the same predictions P1 to P6 as above, and one more:

K3 (new, a segment E added to the kickstorm timeline, after D): rapid alternating taps of both kicks at FULL level
(velocity 1.0): pads 1 and 5 alternately every 8 frames (7.5 presses a second) for 3 s, frames 720 to 900, each released
4 frames after its press; the kickstorm timeline grows to 960 frames.
- P7 (the gate, pass or fail): at most 3 flashes a second in every window, red at most 3, over all of K1 + K3.
- P8: the limiter acts on fewer than 5 % of the K3 frames. If it acts a lot, the kick's envelope is wrong (it would be
  dimming Daniel's hits) and I tune the kick, never the gate.

### Round 2 addition (the conductor, with Daniel's words), pre-registered before it was built or run

Daniel, verbatim: "Also currently kick doesnt always trigger when its pressed. It looks so cool when it does on the color
one, can we make sure that the kick buttons are responsive and work with powerful impact hits and repeat hits so that it
always feels responsive and looks visually stunning and cohesive"

Added to the `kickpix` cases above (same pages, same frames): each case also reads the 1st, 2nd and 3rd frame after the
press, and the press falls at a different phase of its beat in every case (0.37 of a beat apart, half of them in the
second half of the beat, where round 1 waited for the next line).
- R4 (pass or fail): LATENCY. In every case the first frame after the press already changes at least 1 % of the screen by
  dE76 > 10 (1 frame at 60 fps; a head's dimmer motor needs 0.04 s, so a heads-only area may take 2 to 3 frames: I
  predict every case at 1 frame, since every area dealt in a shot shows within a frame or two, and report the worst).
- R5 (pass or fail): no press is ever left unlit: the kick's `presses_unlit` stays 0 over every pixel run (round 1's
  `passed_over` counted AREAS the dealer judged and passed by, not presses; every press always dealt something, but it could
  be off camera or behind its beat line, and that is what Daniel saw as "doesnt always trigger").

New phase `kickrepeat`: REPEAT HITS. The page in engine mode as in kickpix, 832 x 384, the drop look, FOH_WIDE pinned,
every frame drawn (the limiter judges every frame), page A without taps and page B with them. Per run one tap rate r of
4, 6 or 8 taps a second: KICK COLOUR tapped at r for 1.25 s (frames 30 to 105), then KICK WHITE at r for 1.25 s (frames
120 to 195), each tap held 3 frames, velocity 0.8, through the pad door.
- R6 (pass or fail): every tap reads as a new hit. A tap's change is the pixels whose colour moves by dE76 > 10 between
  the frame before the tap and 6 frames (0.1 s) after it in page B, but NOT in page A over the same two frames (the
  scene's own motion taken out). Every tap at every rate changes at least 3 % of the screen (about 9,600 pixels, a
  100 x 100 patch on the phone; a re-strike changes a hit that is already up, so the bar is lower than a fresh hit's 10 %).
- R7 (pass or fail): the limiter acts on at most 2 % of page B's frames at each rate (about 4 frames of 210), and the
  verifier counts at most 3 flashes a second in every window, red at most 3. If the limiter acts more, the repeats are
  flashing and the kick's design is wrong; I fix the kick, not the gate.

### Addendum 3, written after the intermediate round-2 runs and before the final ones (the bars R1 to R7 unchanged)

Intermediate runs on unfinished round-2 code (kept in the record below) found, honestly:
- R1 failing where the dealer picked a visible but small area (the delay towers on FOH_WIDE: 5.8 %; the towers on
  TRIBUNE_34: 8.3 %), and once where the white kick went to the rings the build already lights near white (2.5 %). Fixed
  in the kick, not the bar: the page now tells the dealer how much of the FRAME each area covers (a 16 x 8 grid of the
  frame, a head's points lighting the cells round them), an area must cover 12 % of it, and the best-covered eligible area
  wins; and the dealer counts a member as changed only when the kick makes it brighter or another colour, never dimmer.
- R6 failing (re-strikes changing 2 to 4 % of the frame, the dealt area the towers): the dealer now deals the area the
  shot shows most of; a re-strike steps to the MOST different colour of equal brightness (not the next one round the
  palette, which put lime after green); and a re-strike flips a comb on the area's heads (alternate heads at full and at
  55 %), which shows within the dimmer motor's 0.04 s where a colour wheel needs 0.12 s a slot, the area's mean
  brightness unchanged.
- `kickrepeat` drew only 90 to 120 of page B's 210 frames inside the burst: from here each run taps ONE kind (colour or
  white, `--repeat-kind`), frames 30 to 105 of 120, at each of the three rates: six runs instead of three, the same taps,
  the same bars.
- Also found: `node --check` on a `.js` ES module (every arsenal/web module) does not report early errors such as a
  duplicate `const`; my first view grid redeclared the page's `grid` and the page stopped booting. Parse checks of the
  page modules now go through `vm.SourceTextModule` (as the browser parses them).

## Round 2: what was built

All in `arsenal/web/stage/kick.js` (the programmer's step 3), `programmer.js` (the kick's colours as extra roles; the wheel's
red-free short way; the zoom fix of addendum 7), `stage.js` (the camera's view of each area; the limiter's headroom handed
to the kick; any pad whose action is a kick kind is a kick) and the set's `kick` block. As it stands after the addenda
below (they record how it got here).

- KINDS, as data (`kick.kinds`; the pad map names a kind as a pad's action). Each kind says what it does to its area:
  `colour` ("white", "palette", "keep" or a #rrggbb), `override` (replace the look's light, or lift it), `motion` ("bands":
  velocity's animation, or "none"), `strobe` (the top-band strobe), `repeat` (what a re-strike changes: "colour",
  "motion" or "none"), `punch` (the attack's overshoot). kick-white = white / override / bands / strobe / repeat motion /
  punch 0.15; kick-colour = palette / override / bands / strobe / repeat colour / punch 0.15. "kick" means the first kind.
- AREAS (four): rings (all slats and rims, 3,013 LED cells), beams (truss, lip, towers, pods, strips and both delay
  towers: 68 heads, 224 LED cells), halo (48 heads), strand (12 heads, 1,200 LED cells). No fixture in two areas.
- THE DEALER: only an area the hit visibly changes (60 % or more of its members move by dE76 > 15 without getting
  darker) and that the CURRENT shot shows (a quarter of its points in view and 12 % of a 16 x 8 grid over the frame
  covered; the page computes this from the director's pose); of those, the one covering the most of the frame; then never
  the button's last area and another zone when it can; never an area another live kick shows. When nothing qualifies it
  still deals the best visible area, then any free one: a press is never skipped (`presses_unlit` counts the impossible
  case; `areas_passed_over` counts the areas it judged and passed by).
- OVERRIDE: while live, the area's intensity and colour are the kick's; the look runs on underneath and the area crossfades
  back to it as the kick fades.
- COLOUR: white is #ffffff. The colour kick takes the next palette colour at least 90 degrees of hue from what the area
  shows and 60 degrees from the other live kick's colour. Palette (relative luminance, hue): #00e5ff (0.63, 186),
  #ff2bd6 (0.28, 312), #ffd21a (0.67, 48), #2a5bff (0.15, 226), #19ff4a (0.72, 133), #ff9a1a (0.44, 34),
  #b84bff (0.22, 276), #a8ff2a (0.80, 85); none a saturated red (validation refuses one). Moving heads change colour too:
  each head's wheel goes to the slot nearest the colour among those it reaches the SHORT way round without passing the red
  slot (so never the long way, never through red), at the wheel's real 0.12 s a slot, and back the same way after; and
  (addendum 8) only on a way whose brightness runs clean (no slot on the way more than 35 % darker or brighter than where
  the move has been), never to a slot more than 35 % darker, never to a white slot for a colour, and on a re-strike only
  to a slot of about the brightness it shows. When the colour cannot be reached that way the head keeps its colour at the
  kick's intensity and the area's LEDs carry the colour.
- RESPONSIVE: the light starts at the press (the next frame; a head's dimmer motor needs 0.04 s more), with a punch of
  0.15 over the held intensity settling over 0.15 s. The beat a press belongs to is still the nearest one (`onset`,
  `stats.kicks`, the receipt's "lands on its beat"). The round-1 assertion that an early press waits for its beat line
  (in the hold = gate test) is SUPERSEDED: that test now asserts a tap a tenth of a beat early lights at the press and is
  still booked on its beat. The wait survives only for v0's kick (a set with no kick block), asserted unchanged in
  "without a kick block (source-v0) KICK is the v0 strand lift".
- LEVEL: intensity = 0.5 + 0.5 x sqrt(level): the bottom of the strip is half intensity, a quarter up 75 %, half up 85 %,
  the top full. The strobe band stays on the level itself (0.95 and up).
- HOLD, LINGER, RE-STRIKE: lit while held; at least a second after the last press (a tap is a one-second hit); then a
  0.3 beat fade. A press while the button's area is still lit re-strikes it: the light stays up; the colour kick steps to
  the most different palette colour of about the same luminance (within 35 %), never back to the one before; the white
  kick deals a fresh motion and jumps its chase on; and the area flips a comb (alternate heads, and alternate stripes of a
  twentieth of its LEDs, at full and at 35 %). Each tap is a visible change with no brightness flash.
- THE FLASH GOVERNOR (addenda 6 and 9): each frame the page hands the kick the final limiter's headroom (how many more
  counted transitions its most loaded window can take); under 2, the kick holds back its optional luminance changes (punch,
  colour step, comb flip, a re-strike's motion and chase jump, the start of a fade for up to 2 s, the strobe going dark),
  and a live area's motion and LED chase stand still, moving on from where they stood once there is room for one more. A
  press always lights. `flash.js` is unchanged; the page only reads its counters.
- The strobe needs the pad held 0.25 s in the top band (a tap never strobes); the LED chase floor is 0.8.
- The strobe's clock and its cap, hold = gate, padLevel, the pad door, the late-press bookkeeping and the v0 fallback are
  round 1's, unchanged.

### How a new kind is added (round 3)

1. Add an entry to `kick.kinds` in the set (for example `"kick-move": {"colour": "keep", "override": false, "motion":
   "bands", "repeat": "motion"}`) and map a pad to it in `show.pads` (`"7": "kick-move"`): stage.js routes any pad whose
   action is a kind, and the keyboard map gets a key if wanted.
2. For a behaviour the fields above cannot express (MOVE stepping the panning phrases, BLAST punching narrow full beams
   with zoom, SWAP changing which lights are on), add the field to `KIND_FIELDS` and `DEFAULT_KINDS` in kick.js, validate
   it in `validateKick`, and read it where a kind's behaviour is decided: `press()` (what is dealt, what the kick starts),
   `_restrike()` (what a repeat changes) and `apply()` (what it does to the area each frame). The deck, the view check,
   hold = gate, the level, the strobe clock and the flash budget then apply to it unchanged.

## Round 2: decisions Daniel may want to overrule

1. A tap is a one-second hit (`governor.linger_s` 1.0): long enough that repeated taps re-strike instead of flashing areas
   on and off. Shorter makes taps snappier and rolls flashier (the limiter would start acting).
2. Repeats change colour at about equal brightness, not brightness: a roll is a run of colour and motion changes on one
   area, not a strobe of areas. The area changes only once the last one has faded.
3. The dealer prefers the area the shot shows most of, over variety: in a given shot the two buttons tend to alternate
   among its two or three biggest areas.
4. The level curve's floor (0.5) and shape (square root).
5. The punch (0.15 over 0.15 s) on fresh hits only (it was 0.25; at 0.25 a big area's settle was a flash of its own).
6. The comb's floor (35 %) on a re-struck area, heads and LED stripes.
7. The contrast rule (90 degrees from the area's colour, 60 from the other kick's) and the palette itself.
8. White is pure #ffffff, not the theme's W.
9. The four areas (rings, beams, halo, strand): big enough to read on a phone, so two buttons share four areas and the
   dealer's "another zone" rule has little room. Lasers are still not in the deck.
10. The flash governor: with the limiter's budget nearly spent, a hit stays up and still instead of punching, stepping,
   moving or fading.
   The other way round (the kick does all of it and the limiter dims or freezes the frame) is what the gate is for, but
   it would dim his hits.
11. The strobe needs a 0.25 s hold in the top band: a full-level TAP is a hit, never a strobe.
12. Moving heads take the colour kick's colour only when their wheel reaches it cleanly (addendum 8). On this set's wheel
   (white, red, orange, yellow, lime, green, cyan, light blue, deep blue, violet, magenta, pink, warm white, indigo) the
   looks park the beams on white, indigo or violet, from where cyan, green, blue and orange lie behind the deep blue or
   indigo slots: the colour kick then turns those beams warm white or keeps their colour at full, and the LEDs (rings,
   strand, the beams' strips) carry the vivid colour. The other choice is the wheel running through every slot on the
   way, a rainbow sweep over the beams: it flickers a big area at eight slots a second and the limiter then holds the
   frame (35 % of a roll of taps). A second wheel or CMY mixing on the beam fixture would lift this; that is the rig's
   call, not the kick's.
13. The zoom fix of addendum 7 changes the show outside the kick: every phrase release now hands a head's zoom back to
   its home, and no zoom target leaves its fixture's range. Nothing in the sets asks for a zoom outside it (all are 0.6
   degrees or more); only the blend did.

### Addendum 4, before the final runs (the bars R1 to R7 unchanged)

A third set of runs (intro, build, drop; kept in the record) still had R1 misses, all of one kind: the dealer, after its
"never the button's last area" rule, fell to the thin areas, and on the screen they are thin: the delay towers on
FOH_WIDE 4.9 to 5.8 %, the towers on FOH_WIDE, TRIBUNE_34 and TUNNEL_UP 6.3 to 8.0 %, against rings 60 to 80 %, halo 19
to 69 %, strand 18 to 79 % and the truss and lip beams 13 to 43 %. I checked whether a better screen-cover estimate in the
dealer could tell them apart and it could not (a point-sample grid estimate correlates poorly with the measured pixels:
the strand on TRIBUNE_34 measured 79 % but estimated 7 to 36 %). So the towers, pods, strips and delay towers now ride
WITH the truss and lip beams as one area ("beams": 68 heads, 224 LED cells); the deck has four areas (rings, beams,
halo, strand); and the dealer counts a member as changed only at dE76 15 (the bar is 10). One more case (the build's
near-white rings taking a white kick, 2.5 %) is what that margin is for.

### Addendum 5, before the white repeat runs' final pass (the bar R6 unchanged)

The final colour repeat runs passed R6 at 4, 6 and 8 taps a second (every tap 3.7 % or more, median about 15 %). The
white ones, on the merged beams area, missed narrowly: after the first two taps each re-strike changed 2.8 to 3.9 % of the
frame (minimum 2.75 % at 4 a second, 2.85 % at 6). The white kick has no colour to step, so its repeat is motion plus the
comb, and a 55 % comb on thin beams reads small. Changed in the kick: the comb floor is 35 %, and the comb covers the
area's LEDs too (alternate stripes of a twentieth of the area along its order, wide enough to see on a phone, where a
per-LED alternation would average out). The area's mean brightness still stays put from tap to tap (half and half). The
white runs at 4, 6 and 8 taps a second were re-run on this; both sets are in the record.

### Addendum 6, before the final runs: the flash governor (the gate and the limiter unchanged)

The flash cases on the code of addendum 5 (receipts kept in the record) kept the gate -- the verifier's worst was 3
flashes a second in K1 + K3 and 2.5 in K2, red 0 -- but the limiter had to act: K2 (the demo's programmed white kick on
every downbeat) 27 of 300 frames, where P6 says zero; K1's held strobes 10.2 % of their frames (P2: under 10 %); K3's
rapid full-level taps 43 % (P8: under 5 %). That is the warning case the conductor named: the limiter dimming Daniel's
hits. Round 2 had made each kick's area big and full-intensity, so every luminance change the kick makes (the rise, the
fall, the punch settling, the LED chase's travelling band, colour steps, comb flips, strobe edges) now counts in the windows
it covers, on top of the show's own. Fixed in the kick, not the gate:
- THE FLASH GOVERNOR: each frame the page reads the final limiter's counters (`flash.js` is unchanged; the page only
  reads `limiter.trackers[*].count(t)`) and hands the kick its headroom: how many more counted transitions the most loaded
  window can take in the next second. With fewer than 2 left the kick makes none of its optional luminance changes: no
  punch, no colour step or comb flip on a re-strike (it still deals a fresh motion), the start of a release's fade waits
  (up to 2 s), and the strobe does not go dark. A press always lights at once; that alone is never held back.
- The strobe needs a deliberate hold: the pad held 0.25 s with the level in the top band (`strobe.hold_s`). A tap is a hit,
  never a strobe.
- The LED chase floor is 0.8 (was 0.6) and the punch 0.15 (was 0.25): less luminance swing inside a held hit.
- `kickstorm` in chunks: since the governor reads the limiter's history, which a chunk's logic-only replay does not have,
  chunks need not agree where they overlap. Each chunk is judged on its own with the verifier's count; the chunks now
  overlap by a second (frames 0 to 360, 300 to 660, 600 to 960), so every one-second window of the case lies wholly inside
  one chunk; each segment's limiter count comes from the chunk that holds it.
Every receipt was re-run on this code; K2 and K3 still failed (addenda 7 and 8 have why).

### Addendum 7, before the final runs: case K2 and a 0-degree beam (the gate, the limiter and the kick's envelope unchanged)

The governor code passed every case but one: K2 (the demo's programmed white kick on every drop downbeat, from bar 30)
still had 27 of 300 frames limited, where P6 says zero. I did not tune anything until I knew why. A new verifier option,
`--flash-debug`, keeps every frame's 4 x 4 cells and the kick's state (live areas, headroom, the governor's counters, beam
count and beam power) in the receipt, and `--flash-shots` saves screenshots after chosen frames (scratch only):
- The first white kick (frame 112, the halo, with the cut to TUNNEL_UP and FLY-OUT) lit, then the windows counted a fall
  and, at frames 136 to 140, a fall and a rise of up to 0.37 in the centre windows: a ONE-FRAME collapse at frame 139.
  That spent every window's budget, and the limiter froze 8 windows over frames 146 to 172 while the scene drifted.
- A/B on the same frames: the white kick's motion off, still 25 limited frames; the punch off, still 27; NO kick, zero
  (and no dip). Beam count and beam power were steady through frame 139, so no dimmer dipped. The screenshots of frames
  138, 139 and 140 showed it: the halo's 48 beams vanish for one frame and come back, their lenses still lit.
- The cause, found in the frame state: the halo's ZOOM went 0.66, 0.6, ... 0.01, 0.00 (frame 139), 0.01, rising. In the
  drop the look leaves the halo's Zoom unset (0 in the programmer's targets, which means the fixture's home), and the
  phrase layer's release crossfaded the halo's 1.2 degrees toward that literal 0. A 0-degree beam is narrower than a
  pixel and, by the renderer's photometry (flux over the beam's solid angle), unboundedly bright: a line that blinks out.
  The fixture's own end stop is 0.5 degrees. While the halo was dark nobody could see it; the white kick lit it.
- Fixed at the root, in `programmer.js`: a phrase's release blends a head's zoom toward its home when the look leaves it
  unset (never toward 0), and every zoom target is held inside the fixture's range (`attrs.Zoom.min` / `max`, 0.5 to 4
  degrees for every head here). New test in `tests/stage_phrases.test.mjs`: "a phrase's release hands a head's zoom back to
  its home, never through 0 or past the fixture's end stops". The kick, the governor, `flash.js` and the verifier's bars
  are untouched by it.
- K2 on the fix: zero interventions in 301 frames, worst 1.5 flashes a second (col2), red 0 (receipt
  stage-20261028-021614). The chain was then re-run on this code; addendum 8 has what it found.
This was a defect of the show that the kick exposed, not one the kick made; I record it because the conductor's rule
("If the limiter acts a lot, the design is wrong ... tune the kick envelope, not the gate") pointed at the kick first,
and the A/B said otherwise.

### Addendum 8, before the final runs: the colour wheels (P8 and the gate unchanged)

The chain on the zoom fix (kept in the record: K2 zero interventions again; kickstorm's gate held, worst 3 flashes a second,
red 0; P2 9.8 %) still failed P8: the limiter acted on 63 of K3's 180 frames (35 %). The K3 windows counted a transition
every 6 to 7 frames in the lower rows, and a logic-only replay of K3 (scratch `k3_sim.mjs`) showed why: on every colour
re-strike the beams' 68 wheels set off for the new palette colour's nearest slot, the short way, and the short way from
the look's indigo to cyan runs through warm white, pink, magenta, violet, deep blue and light blue. The heads' emitted
brightness went 0.49, 0.26, 0.19, 0.16, 0.07, 0.25, 0.47 at the wheel's 8 slots a second, and the next tap re-aimed the
wheels before they arrived. The same run, once, after a fresh hit, is the limiter's 36 frames in K1's segment B (both
buttons held, the colour kick's wheels running while the strobe began).
Fixed in the kick (`kick.js`, with the programmer's way back): a kick's wheel move must run CLEAN -- the brightness of the
slots on the way never turns back by more than `governor.equal_luma` (35 %) of the move's running extreme -- and never
to a slot more than 35 % darker; a colour (saturation 0.3 or more) never picks a white slot; a re-strike's move only goes
to a slot of about the brightness the wheel shows (within 35 %); when nothing qualifies the wheel stays. The red rule and
the short way are unchanged. New test: "a kick never runs a wheel through a flash: clean ways only, never to a much darker
slot, a colour never white, a roll's wheels hold their brightness" (every slot to every kick colour on the beam wheel, and
a K3 roll in the programmer with no head's brightness turning back). What it costs is decision 12 above.

### Addendum 9, before the final runs: the motion stands still; segment D's input check (the bars unchanged)

On the wheel fix (receipts kept: the gate held, worst 3, red 0; P8 down from 35 % to 17 %; P2 up to 13.9 %, failing) the
limited stretches all began within a few frames of the director's cuts (every bar in the drop: frames 496, 592, 688, 784,
880): a cut onto big kicked areas spends a window's budget at once, and the live area's motion (the drive band's
one-bar gesture) and its LED chase kept moving light across the windows after it. Changed in the kick: while the
headroom is under `governor.need` the live area's motion and chase stand still (their own clock pauses), and they move
on from where they stood once the headroom is back to need + 1 (the step between the two is a hysteresis, so they do
not stutter). Counted in `governor_held_back.still` (frames). New test: "the flash governor stands a live area's motion
still while the budget is spent, and moves it on from there".

The same run failed kickstorm's INPUT check for segment D ("the 10-a-second tap storm dealt at least two row
combinations"), a sanity check that the input happened, written for round 1, where every tap dealt a new row. In round
2 a tap while the button's area is lit re-strikes that area, so a tap storm shows as both buttons' areas live for the
whole segment, which is what the check now asks (both kicks live on at least 30 of its 60 frames). It is not one of the
pre-registered predictions; I record the change because I made it after seeing the run fail it.

On this code the kickstorm chunks (stage-20261028-031937, -032121, -032321, -032530; stitched in stage-20261028-032720):
P1 held (worst 2.5 flashes a second, red 0), P2 7.8 % (held), P3 0 of 60 (the prediction that the limiter
would act on the tap storm did not hold: it never had to), P4 red 0, P5 no errors, P8 11 of 180 frames (6.1 %): NOT
held, narrowly. All 11 are frames 889 to 899, right after the director's cut at frame 880 to UNDER_LAYERS, a shot looking
up into the two kicked areas (rings and beams), where the full frame jumps from 0.24 to 0.56 and the lower windows
jitter by up to 0.1 from frame to frame before the limiter starts; the rest of K3 (frames 720 to 888) has no limited
frame. I stopped tuning there; the record of P8 across the fixes is 43 %, 27.8 %, 35 % (with the zoom fix, before the
wheel fix), 17 %, 6.1 %.

## Round 2: the final receipts (2026-10-28, on the code of addenda 7 to 9; headless SwiftShader under the house GPU lock)

Node: `node --test tests/stage_*.test.mjs tests/vj_*.test.mjs`: 376 of 376 pass (the kick's 22 tests, the new zoom test in
stage_phrases). The vj_lasers fresh-seed rounds passed in every full run today; they draw a new seed from the clock each
run and failed once on the untouched baseline (see "Also seen"); not trivial to fix without changing what they test
(realistic play on fresh seeds), so reported, not changed.

### The pixel metric (`kickpix`, 832 x 384, page A without the kick and page B with it on the same virtual-clock frames)

Before = the round-1 code (HEAD 10c27410d's web files), after = this code; the same 46 cases, the same pages. Coverage is
the share of the frame whose colour moves by dE76 > 10 (the larger of the quarter-beat and one-beat frames); latency is
the first frame after the press with 1 % or more of the frame changed.

| | Round 1 (before) | Round 2 (after) |
|---|---|---|
| minimum coverage | 0 % (11 cases at 0) | 8.9 % |
| median | 5.6 % | 44.4 % |
| maximum | 61.5 % | 91.5 % |
| cases under 10 % (R1's bar) | 32 of 46 | 1 of 46 |
| latency | 1 frame in 16 cases, 3 in 5, over 3 in 25 | 1 frame in all 46 |
| control frames identical in A and B | | all 46 |
| limiter frames over every case | | 0 |
| presses left unlit | | 0 (R5); the dealer passed over 185 AREAS in all (judged not to show, a better one dealt) |

By look and kind:

| Look | Kick | Round 1 min / median / max (%) | Round 2 min / median / max (%) |
|---|---|---|---|
| intro | white | 6.1 / 7.95 / 16.1 | 25.9 / 41.35 / 63.4 |
| intro | colour | 1.7 / 7.2 / 11.8 | 15.8 / 56.55 / 82.3 |
| build | white | 1.2 / 4.75 / 9.8 | 11.9 / 26.85 / 43.3 |
| build | colour | 0 / 9.25 / 18 | 18.2 / 21.4 / 79.3 |
| drop | white | 0 / 10.2 / 52.3 | 27.1 / 40.2 / 72.4 |
| drop | colour | 0 / 0 / 11 | 19.3 / 36.6 / 75.7 |
| break | white | 0 / 4.25 / 16.5 | 32.8 / 63.35 / 79.8 |
| break | colour | 0 / 2.45 / 53.8 | 8.9 / 30.6 / 67.5 |
| groove | white | 0 / 11.45 / 61.5 | 23.5 / 60.25 / 72 |
| groove | colour | 0 / 3.35 / 11.1 | 23.1 / 56.85 / 91.5 |

Every case (the area or row dealt, coverage, latency in frames):

| Look | Shot | Kick | Round 1: row dealt, coverage, latency (frames) | Round 2: area dealt, coverage, latency |
|---|---|---|---|---|
| intro | FOH_HOLD_ZOOM | white | vert.strips, 6.1 %, 1 | halo, 25.9 %, 1 |
| intro | FOH_HOLD_ZOOM | colour | halo.bot, 11.8 %, > 3 | beams, 47.8 %, 1 |
| intro | CRANE_RISE_REVEAL | white | strand.cubes, 7.7 %, 3 | strand, 36.8 %, 1 |
| intro | CRANE_RISE_REVEAL | colour | vert.towers, 1.7 %, 1 | rings, 82.3 %, 1 |
| intro | FOH_WIDE | white | rings.rims, 16.1 %, > 3 | beams, 45.9 %, 1 |
| intro | FOH_WIDE | colour | halo.mid, 4.9 %, 1 | halo, 15.8 %, 1 |
| intro | TRIBUNE_34 | white | strand.bars, 8.2 %, 1 | strand, 63.4 %, 1 |
| intro | TRIBUNE_34 | colour | delay.30, 9.5 %, > 3 | beams, 65.3 %, 1 |
| build | STRAND_FLYTHROUGH | white | vert.strips, 4.5 %, 1 | beams, 32.3 %, 1 |
| build | STRAND_FLYTHROUGH | colour | halo.bot, 17 %, > 3 | halo, 22.5 %, 1 |
| build | FOH_WIDE | white | strand.cubes, 1.2 %, 3 | strand, 11.9 %, 1 |
| build | FOH_WIDE | colour | vert.towers, 1.5 %, 1 | beams, 20.3 %, 1 |
| build | HEAD_ORBIT | white | truss.heads, 5 %, > 3 | halo, 43.3 %, 1 |
| build | HEAD_ORBIT | colour | halo.mid, 18 %, 1 | rings, 79.3 %, 1 |
| build | TUNNEL_UP | white | lip.heads, 9.8 %, 1 | strand, 21.4 %, 1 |
| build | TUNNEL_UP | colour | delay.30, 0 %, > 3 | beams, 18.2 %, 1 |
| drop | TUNNEL_UP | white | vert.strips, 4.4 %, 1 | beams, 40.2 %, 1 |
| drop | TUNNEL_UP | colour | halo.bot, 11 %, > 3 | halo, 23.8 %, 1 |
| drop | TOPDOWN_GODVIEW | white | strand.cubes, 21.9 %, 3 | strand, 57.5 %, 1 |
| drop | TOPDOWN_GODVIEW | colour | vert.towers, 0 %, > 3 | strand, 75.7 %, 1 |
| drop | TRIBUNE_34 | white | rings.rims, 52.3 %, > 3 | beams, 29 %, 1 |
| drop | TRIBUNE_34 | colour | halo.mid, 5.5 %, 1 | halo, 24.2 %, 1 |
| drop | HEAD_ORBIT | white | strand.bars, 0 %, > 3 | rings, 72.4 %, 1 |
| drop | HEAD_ORBIT | colour | delay.30, 0 %, > 3 | halo, 68.8 %, 1 |
| drop | FOH_WIDE | white | rings.r0.slats, 6.2 %, 1 | beams, 27.4 %, 1 |
| drop | FOH_WIDE | colour | halo.top, 2.4 %, 1 | strand, 19.3 %, 1 |
| drop | CROWD_POV | white | rings.r3.slats, 10.2 %, > 3 | rings, 62.2 %, 1 |
| drop | CROWD_POV | colour | delay.55, 0 %, > 3 | halo, 36.6 %, 1 |
| drop | WORM_RING | white | rings.r1.slats, 12.1 %, > 3 | beams, 27.1 %, 1 |
| drop | WORM_RING | colour | vert.towers, 0 %, > 3 | rings, 73 %, 1 |
| break | HEAD_ORBIT_SLOW | white | vert.strips, 7.5 %, 1 | halo, 79.8 %, 1 |
| break | HEAD_ORBIT_SLOW | colour | halo.bot, 53.8 %, > 3 | beams, 45.5 %, 1 |
| break | DJ_OTS | white | strand.cubes, 1 %, 3 | strand, 32.8 %, 1 |
| break | DJ_OTS | colour | vert.towers, 0 %, > 3 | strand, 8.9 %, 1 |
| break | FOH_WIDE | white | rings.rims, 16.5 %, > 3 | beams, 48.1 %, 1 |
| break | FOH_WIDE | colour | halo.mid, 4.9 %, 1 | halo, 15.7 %, 1 |
| break | CROWD_POV | white | strand.bars, 0 %, > 3 | rings, 78.6 %, 1 |
| break | CROWD_POV | colour | delay.30, 0 %, > 3 | beams, 67.5 %, 1 |
| groove | FOH_HOLD_ZOOM | white | vert.strips, 5.7 %, 1 | halo, 23.5 %, 1 |
| groove | FOH_HOLD_ZOOM | colour | halo.bot, 11.1 %, > 3 | beams, 45.8 %, 1 |
| groove | TRIBUNE_34 | white | strand.cubes, 17.2 %, 3 | strand, 69.5 %, 1 |
| groove | TRIBUNE_34 | colour | vert.towers, 1 %, > 3 | halo, 23.1 %, 1 |
| groove | PROFILE_GRAPH | white | rings.rims, 61.5 %, > 3 | beams, 51 %, 1 |
| groove | PROFILE_GRAPH | colour | halo.mid, 5.7 %, 1 | strand, 91.5 %, 1 |
| groove | HEAD_ORBIT | white | strand.bars, 0 %, > 3 | rings, 72 %, 1 |
| groove | HEAD_ORBIT | colour | delay.30, 0 %, > 3 | halo, 67.9 %, 1 |

R1 (every case 10 % or more): NOT held, 45 of 46. The miss is the break look, DJ_OTS, KICK COLOUR on the strand: 8.9 %.
On the code before addendum 8 the same case measured 10.4 %; addendum 8's wheel rule cost it: the strand's heads, parked
on indigo, cannot reach the colour's slot cleanly and now keep their colour at full where before their wheels had set off
through the brighter warm-white slot on the way to cyan. The LEDs (1,200 of the strand's members) take the colour either
way. I did not tune further: the fix is either decision 12 (let a fresh hit's wheel run through the dark slots, and the
flicker comes back) or a tie-break that sends an unreachable colour's heads to the brighter of the near slots (warm white
here), which changes every case and needs the whole chain again. R2 held (round 1 fails: 32 of 46 under 10 %). R3 held. R4
held (1 frame in all 46). R5 held (0 unlit presses).
Worst five after: break DJ_OTS colour 8.9 % (strand); build FOH_WIDE white 11.9 % (strand); break FOH_WIDE colour 15.7 %
(halo); intro FOH_WIDE colour 15.8 % (halo); build TUNNEL_UP colour 18.2 % (beams).

### Repeat hits (`kickrepeat`, drop look, FOH_WIDE pinned, 832 x 384, every frame drawn)

| Kind | Taps a second | Taps | Each tap's own change, min / median / max (% of the frame) | Limiter frames, page B / A | Worst flashes a second, red | Re-strikes | Receipt |
|---|---|---|---|---|---|---|---|
| colour | 4 | 5 | 6.8 / 11.3 / 15.7 | 0 / 0 | 0, 0 | 4 | stage-20261028-034109 |
| colour | 6 | 8 | 5.9 / 8.3 / 15.7 | 0 / 0 | 0, 0 | 7 | stage-20261028-034651 |
| colour | 8 | 10 | 6.0 / 8.1 / 15.7 | 0 / 0 | 0, 0 | 9 | stage-20261028-034857 |
| white | 4 | 5 | 4.4 / 7.3 / 18.3 | 0 / 0 | 0, 0 | 4 | stage-20261028-040339 |
| white | 6 | 8 | 4.3 / 4.7 / 18.3 | 0 / 0 | 0, 0 | 7 | stage-20261028-041126 |
| white | 8 | 10 | 4.4 / 4.8 / 18.3 | 0 / 0 | 0, 0 | 9 | stage-20261028-041616 |

R6 (every tap 3 % or more) held at every rate; R7 (limiter at most 2 % of the frames) held: 0 frames at every rate. No
press unlit; the governor never had to hold anything back in these runs (headroom stayed up).

### Flash cases

| Case | Prediction | Outcome |
|---|---|---|
| K1 + K3 (`kickstorm`, 640 x 360, frames 0 to 959 in four chunks: 0-300, 220-520, 420-720, 640-960, each one-second window inside one chunk; stitched in stage-20261028-032720) | P1 (gate): at most 3 flashes a second in every window, red at most 3 | held: worst 2.5 (block10, block02), red 0 |
| | P2: the limiter acts on under 10 % of the held-strobe frames (A to C) | held: 42 of 540 (7.8 %) |
| | P3: it acts on some frames of the tap storm (D) | did not hold: 0 of 60 (it never had to) |
| | P4: red 0 / P5: no errors | held / held |
| | P8: the limiter acts on under 5 % of K3's frames | NOT held: 11 of 180 (6.1 %), all 11 in the 20 frames after the director's cut at frame 880 (addendum 9) |
| K2 (`flash --flash-from-bar 30`, 1280 x 720, stage-20261028-033426) | P6: at most 3 flashes a second, red at most 3, ZERO interventions | held: worst 1.5, red 0, 0 interventions in 300 frames |
| `flash` (bar 14) and `storm` (stage-20261028-045109) | unchanged from round 1 | flash: worst 2, red 0, 0 interventions in 360 frames; storm: worst 2, red 0, 0 interventions in 360 frames |

The governor's held-back counts over the kickstorm chunks (cumulative from frame 0 in each chunk; frames before a chunk
are replayed as logic only, where the limiter has no history): chunk 0-300: punch 2, comb 1, motion 1, fade 20, strobe
62, still 320 frames; chunk 220-520: strobe 53, still 448; chunk 420-720: punch 2, colour 2, comb 6, motion 6, strobe 2,
still 220; chunk 640-960 (37 presses, 31 re-strikes): colour 5, comb 11, motion 11, fade 6, still 360. Every press lit
(presses_unlit 0 in every chunk).

### The other receipts

- `kick` (stage-20261028-045014): 8 of 8, the pad door, both kicks held at once on two areas, padlevel, the strobe band, the
  release, the keys, every press booked on its nearest beat.
- `load`, `clock`, `engine` (stage-20261028-050013): 19 of 19; "the KICK lift lands on its beat" holds with the demo's white
  kicks (onset = the beat the press fell on).
- The early-press wait: superseded for the v2 kinds (the light starts at the press; hold = gate test), kept for v0 only.
