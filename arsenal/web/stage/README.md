# Virtual Stage ("Source"), v1: the halo levels

A concert hall inside the computer, with a show rig that behaves like real gear, in the spirit of Qlimax 2014 "The
Source Code of Creation". v0 was the first slice of the design dated 2026-10-24 (the architect's "The Virtual Stage:
Source"; its code name is `arena`, the page lives under `stage/`). v1 (2026-10-25) answers what Daniel said after seeing
v0:

> The parts that are super impressive to me from the light shows are when they have 3 levels of light all shooting over
> the crowd, you have the vertical elements, you can have top, midle then bottom pan up and down sequentially. or
> horizontal flash and pan, then vertical 1, 2, 3 then back to lasers, then a cool pattern of lights from the circular
> halo.

> the three levels seems to be altitudes on the circular array where they group the lasers into thirds. i think it was
> once per beat. we could also do top and bottom, middle, top and bottom again

Open it from the Arsenal server:

- `http://127.0.0.1:8793/web/stage/index.html?demo=1` plays the built-in demo show at 150 BPM: intro 8 bars, build 8,
  drop 24 (Daniel's phrase twice, then the classic drop), break 8, with its own pad presses and camera flypaths.
- `http://127.0.0.1:8793/web/stage/index.html` listens to the VJ engine on 8794. Its beats drive the clock, and the
  KeyLab's pads and faders play the stage. The engine is only read from: the page never posts to it.
- `?set=source-v0` still loads the v0 rig.

| Control | What it does |
|---|---|
| Pad 1 / key `1` | KICK: the strand's cubes and heads lift on the beat. An early press waits for the line. |
| Pad 2 / key `2` | LASERS: a hit. The tier depends on how soon it follows the last one. Holding it gates the lasers on quarter notes. |
| Pad 3 / key `3` | PHRASE GO: Daniel's phrase starts on the next bar line (a press just after a line lands on it). Pressed while it runs, the next repeat (a new variant) starts on the next bar line. |
| Pad 4 / key `4` | PHRASE NEXT: the current step ends on the next bar line; the rest follow from there (the camera plan moves with them). |
| Pad 7 / key `7` | PHRASE STOP: the phrase ends on the next bar line and hands the rig back to the section's look over a beat. |
| Pad 6 / key `6` | FLY-OUT: the truss and lip beams burst outward from the centre. |
| Pad 10 / key `0` | DROP NOW: the drop starts on the next downbeat (and with it the drop's phrase). |
| F1, F4, F5, F6, F9 | Strand master, lasers, haze target (it moves over minutes), speed (detents 1/4 to 4; a phrase's own timing is in beats and ignores it), grand master. The sliders in the HUD do the same. |
| `C` / `Esc` | Hold the next camera shot / give the camera back to the director (or the phrase). |
| `H`, `F` | Hide the HUD, go full screen. The HUD's phrase row names the step, the variant, the repeat and the beats left. |

## Daniel's phrase ("Halo Levels", `sets/source-v1.json` → `phrases.halo-levels`)

Eight bars, five steps, each landing on its bar line:

| Step | Beats | What happens | Camera |
|---|---|---|---|
| A levels | 12 | The circular array's altitude thirds fire top, middle, bottom, one per beat (four cascades, landing back on the bar line), each third shooting out over the crowd at its own height (26, 15 and 8 m where the rays cross z = 30 m) and nodding its tilt. The halo lasers fire with their third. The slats swap a luminance-matched blue and pink once a beat. | HALO_LOCK (the footage's locked long lens), UNDER_LAYERS on alternate repeats |
| B horizontal | 4 | The 24-head lip row flashes once on the ONE (through the FlashGate), then pans -40 to +40 over beats 2-3, rippling across the row. | WING_LAYERS, cut one beat early so the cut never lands on the flash frame |
| C verticals | 4 | V1 (the pods under the x = +-5 PA hangs, with their LED columns), V2 (+-13), V3 (the +-22 pods and side towers) on beats 1, 2, 3; beat 4 dark. | FOH_WIDE |
| D lasers | 8 | Moving heads at 0, LEDs at 8 %; the lasers enter on the ONE (a bloom), then the ceiling on Bank B and scissors on Bank A and the towers. The halo heads move in black to the corona aim. | CROWD_POV, then WORM_RING |
| E halo | 4 | The corona (heads radially out, tipped 25 degrees to the crowd) and the chopper on the slats: two opposite blades, a turn a beat; the halo lasers' spokes follow the blades. The halo moves in black back to the layers on beat 4. | HALO_ORBIT |

Never static: each repeat is dealt a variant from a deck without replacement (daniel first; then pinch: top+bottom,
middle, top+bottom, Daniel's second pattern; ascend: the cascade and the verticals run the other way; depth: the
verticals step out over the crowd on the delay towers; rush: the footage's speed, a third every sixteenth, for builds
and breaks only), and every repeat changes the halo's colour role, the chopper's start angle and direction, the pan's
direction, the layers' height (+-2 m), the nod size and which rings carry the halo pattern.

## The rig additions (v1)

- The halo: 48 narrow beam heads on the outer rims of rings 0-2 (24, 16, 8), standing on the ring face, grouped by the
  ring-local clock angle into `halo.top`, `halo.mid`, `halo.bot` (16 each; a tilt never moves a head between thirds)
  and `halo.tb`; per ring `halo.r0`..`halo.r2`. Twelve lasers on ring 0 (bank R, four per third).
- The verticals: 2-head pods under the PA hangs at x = +-5 (V1), +-13 (V2) and +-22 (V3, with the side towers' four
  upright heads and LED columns); 24-cell LED columns on the V1/V2 hangs; four heads on each delay tower (z 30, z 55)
  for the depth variant.
- The lip row grows from 8 to 24 heads (`hrow`).
- Groups take `where` (tag, level, ring, side) and `union`; order keys clock, level, level_mirror, column, depth.
- Laser groups (`laser_groups`): Bank A, Bank B, towers, hero, the halo's thirds, and combinations.

## Files

| File | Holds |
|---|---|
| `sets/source-v1.json` | The v1 rig and show as data (`arsenal.arena/v1`): v0's types, objects, groups, effects, looks, lasers, atmosphere, themes and cameras, plus the halo, the verticals, laser groups, presets, the ring-effect library and the phrases. |
| `sets/source-v0.json` | The v0 rig, unchanged. |
| `rig.js` | Validates the scene and expands it deterministically. Polar repeats by ring parameter, clock angles and levels, `where`/`union` groups, ring-mounted projectors, `aimAt` (world-locked aiming). Also the MVR bridge and the head geometry. |
| `phrases.js` | The cue sequencer: phrases as data, variants and per-repeat values, the camera plan, the runner (Go, Next, Stop, loop), and the glue that plays its events. |
| `grid.js` | The one beat position for everything, plus the demo clock. |
| `effects.js` | Spreads (MA, ChamSys and Hog in one object), waveforms, beat-locked phase accumulators, the unison floor rule; v1: block "ties", cue-anchored phase, one-shots, clean starts, sparkle. |
| `programmer.js` | Looks, effects, pads (HTP), masters, theme colours, the colour wheel, motor physics; v1: the phrase layer (LTP over the look) and the FlashGate. |
| `kinetics.js` | The hoists (jerk-limited), the formations, and time-priority landing on bar lines. |
| `lasers.js`, `lasers3d.js` | A minimal laser brain on the Lasers v2 contract (v1: laser group lines with shapes and gates, heads past the 21, an aim side channel), mapped onto 33 projectors in 3D with physical power sharing. |
| `atmos.js` | The haze medium: the hazers, the lag, the cap, and our own tileable noise. |
| `camera.js` | Shots as data, centripetal Catmull-Rom paths driven by the beat position, the director that cuts on bars; v1: a phrase's camera plan. |
| `show.js` | Sections (v1: a section may name a phrase), the demo plan, and DROP NOW. |
| `flash.js` | The final-frame flash limiter: at most 3 flashes a second, red included. |
| `render.js`, `shaders.js` | The three.js r186 renderer and our own GLSL, composed with the house library; v1: the crowd near the lens is not drawn (4 m) and its arms hold still (10 m). |

Tests: `node --test tests/stage_*.test.mjs`. The browser receipt: `node arsenal/lanes/stage_verify.mjs` (default phases
load, clock, phrase, engine, flash, storm and the picture measures; `--phases flash3m --flash-scale 0.75` runs the
three-minute crowd-on run in ten-second bursts; `--phases sheet-phrase --sheet-dir <scratch>` the phrase's sheet). It
runs headless SwiftShader only, under the house GPU lock, on the test band.
