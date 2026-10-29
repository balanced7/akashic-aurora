# Stage camera distance: the review's six findings, fixed (2026-10-29)

Daniel, 2026-10-29: "i dont want blacks to be crushed, i just want black to be black for us to truly have an hdr
fidelity light setup that has pure black as something that is just in the scene without crushing other things."

All six findings reproduced and are fixed at the root, each with a test that fails on the previous code and passes now.
The GPU receipt passes 21 of 21 in Classic and in HDR Night, and load and camera still pass. Branch `stage-cam`, three
commits, not pushed.

The black frames in the review were never an exposure problem. FAR lifted the lens into the rigging grid's beams, and
the beam filled the frame. That is now impossible. The high shots at FAR render a mean luminance of 0.020 to 0.062,
where the review's black stills measured 0.0005. In HDR Night the true-black share is 0 to 0.10, and it comes from the
room itself: the black is the scene's own, and the LEDs and beams next to it keep their detail. There is still no
auto-exposure and no added crush.

## What each finding was, and what changed

| # | Reproduced | Root cause | Fix |
|---|---|---|---|
| F1 grid (high) | yes: pure census, FAR above or inside the grid on 5 shots | The room had no rigging grid: the ceiling was roof_y - 2 = 36 m, and the beams are at 32.75 to 33.78 m | `makeRoom` models the grid layer as a ceiling 1 m under the beams for a shot below it (or a floor 1 m over them for a shot above). The room widens to the shot's own camera where that stands outside the floor. The HUD says "held at the rigging grid". |
| F2 jolts (high) | yes: jumps of 0.894 to 0.919 ln in one frame, 35 to 91 reversals | Each frame re-walked the room and jumped to the result; escapes snapped; the walk used 4 % steps | The walk keeps path continuity, is sphere-traced and bisected, and reads the room 0.15 / 0.3 / 0.45 s ahead on the shot's own path. Escapes have hysteresis (2.0 m trigger, 2.5 m target) and stop at the director's own place. The camera follows its goal at no more than e^4.5 a second and 25 a second a second, braking for bounds ahead. If the rig still reaches the lens, it cuts (logged), on a beat line when one comes first. |
| F3 held FAR (med) | yes: E on HALO_LOCK gave 59.8 m and the HUD said plain "FAR" | The planned short value replaced the stop | The stop stays the stop. `heldWhy` names what held it, and a director cut starts the next shot at the full stop (FOH_WIDE: 80.0 m). |
| F4 fader (med) | yes: a brush from 0.60 to 0.61 after Q grabbed the camera | The fader's side of the live value was kept stale | A key press, a handback or a receipt stop forgets the fader's side and value, and the live value is where the camera is going (the stop pressed). |
| F5 phone bar (med) | yes: 667, 740 and 780 wide wrapped onto the strips | The strips sat 60 px from the bottom whatever the bar's height | The strips stand on the bar's measured height. Pads may shrink to 44 px before the bar wraps, so 780 x 360 (the S24) stays one row. The utility buttons are 44 px (they were 38). |
| F6 cut rules (low) | yes: the camera dollied up to the cut; cuts landed 0.7 and 1 beat apart | Moves were not settled; the director's override and C cuts were invisible; distance cuts were invisible to the director | Shift eases a move to rest within 0.25 s. distCtx passes the director's scheduled override. C sets `lastCutPos`. Distance cuts go into the director's cut log (why "distance") and set `pose.cut`. |

## Numbers against the bars

**Pure tests.** `node --test tests/stage_distance.test.mjs` passes 20 of 20. The 6 new tests all fail on the previous
`distance.js`.

**Regression.** distance, camera, palettes, looks_wave1, kick and formations together pass 103 of 103 (44 s).

**Every shot, every stop, through its whole move at 60 fps on the home strand:**
- Largest step 0.052 ln a frame, against a cap of 0.075.
- Acceleration within the cap of 0.0069 a frame a frame.
- At most 2 reversals.
- No forced cut.
- Closest approach 2.00 m.
- Never outside the room.

**Every formation, 213,822 frames.**
- Forced cuts fell from 108 to 9. Seven are in shots whose own camera enters that formation's rig, which the director's
  guard deals away. Two are CRANE_RISE_REVEAL at CLOSE in the high and low waves.
- Closest approach 1.51 m.
- Cost per frame: median 0.03 ms, p99 0.54 ms, worst 2.3 ms. The original build reported at most 0.24 ms a frame, so
  the lookahead costs more at the tail.

**GPU, RX 9070 XT (ANGLE D3D11):**
- Classic `stage-20261029-141951`: pass, 21 of 21.
  - HALO_LOCK: the rings' on-screen box is 5.8x larger at CLOSE than at FAR.
  - FOH_WIDE: 9.9x.
  - The high shots' lens stays at 25.4 to 31.2 m, with a mean luminance of 0.020 to 0.062.
  - Rides: largest step 0.009 and 0.032, no cut, closest approach 14.6 m and 3.19 m.
  - Shift+E after C: the C cut at beat 67.2, the distance cut on 70.
  - F8: largest step 0.075.
  - Phones: no pad over a strip at any width.
- HDR Night `stage-20261029-142019`: pass, 21 of 21. Mean luminance 0.012 to 0.045, true black 0 to 0.10.
- load and camera `stage-20261029-142038`: pass, 13 of 13. The guard never acted, and the corkscrew by hand came no
  closer than 2.908 m.

**Stills I looked at:**
- The 7 high FAR stills: rig content in every one, none black, and HALO_ORBIT is no longer framed through the beams.
- The HDR Night stills: black stays black next to detailed LEDs and beams.
- The phone at 780 x 360: one row, the strips clear.

## One bar changed after a fail

The new ride check first failed on the flythrough's last frame at 1.37 m. That frame is where the director's own camera
enters the rig (1.43 m), and the distance layer had stepped one notch nearer than his pose. Two things changed:

- **The rule for those frames.** Frames where the director's own camera is inside 1.5 m are now judged as "never nearer
  the rig than his own camera" (1 cm tolerance). That is the rule the pure test always used.
- **The camera itself.** Past the end of the shot, with the director's own camera within 2.5 m of the rig, the layer now
  holds. On the rerun it was 0 cm nearer.

The phone check's "one row" became "no pad over a strip" because a narrow phone now takes two rows.

## For Daniel

1. The two forced cuts that remain are CRANE_RISE_REVEAL at CLOSE in the wave formations. The crane's scaled rise
   meets a rung that no move can clear, so the camera cuts, on the beat line when one comes first. The alternative is
   to hold the size and cut to a different shot.
2. Below about 770 CSS px wide the pad bar takes two rows and the strips get shorter (about 145 px tall at 360 px
   high). The S24 at 780 x 360 stays on one row.
3. Still open from the build: FAR is absolute (80 m); the shots that cannot reach CLOSE; the comfort constants
   (LOG_RATE_MAX 4.5, LOG_ACCEL_MAX 25) want his feel on the live stage; F8 = CC 112 moves into show.faders after the
   stage-v3 merge.

## Not verified

- His S24 itself; I checked headless touch emulation only.
- His live stage at :8796; I never touched it.
- The default-list phases clock, phrase, flash and storm were not rerun. Auto mode leaves the pose untouched, and a
  unit test proves it.
