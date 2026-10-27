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
- Looks wave 1 (2026-10-27): `?phrase=<name>` makes pad 3 start that phrase instead of Daniel's: `single-thread`
  (one hero beam in a dark room), `pillars` (the delay towers' square columns straight up), `drumroll-iris` (the rings'
  chop halving every 2 bars into a black last beat), `scissor-gates` (the towers' X on the push-pull), `tunnel-spokes`
  (a beam tunnel with the rings' spiral, one way per repeat). `?theme=<name>` picks one of the set's themes:
  `dreaming-city` (the VJ library's colours measured from Daniel's stills), `genesis-indigo`, `vex-conflux`, `anti-sun`.
  For example `index.html?demo=1&theme=dreaming-city&phrase=pillars`, then pad 3.
- Kinetics wave A and the orrery (2026-10-27): `?ring=orrery` (or `spiral`, `vortex`, `crown`, `portal`) opens with the
  rings in that formation; pad 8 (key `8`) MORPHs to the next one on the next bar line and pad 9 (key `9`) fires the
  energy beam's discharge. Drawn for the Dreaming City palette: `index.html?demo=1&theme=dreaming-city&ring=orrery`.
  `?strand=arch` (or `valley`, `ramp`, `stairs`, `helix-sine`) lands a strand shape on the S-curve instead of the sections'
  waves.

| Control | What it does |
|---|---|
| Pad 1 / key `1` | KICK WHITE (v2, `kick.js`): the next row of the set's kick deck (the truss, the lip, a third of the halo, a ring's slats, the towers, the delay towers, the strand...) comes on in the theme's white, chosen so the hit always shows in the look that is running (a row with no headroom for it is passed over). Held, the row stays lit; let go, it fades over a third of a beat; a tap is a quick hit. An early press waits for its beat line, a late one lights at once. Velocity picks the animation: under 0.45 a peak, from 0.45 a sweep (heads tilt through a V2 motion, LED rows chase it), from 0.85 the sweep with twice the throw (within the tilt motor). |
| Pad 5 / key `5` | KICK COLOUR: the same, in the theme's colour (a lit LED keeps its own look colour when that is already a colour). Held together with KICK WHITE, the two light two different rows. Moving heads never have their colour wheel turned by a kick: the white kick takes a head row only while it shows white, the colour kick only while it shows a colour. |
| Kick level | While a kick is held its brightness follows its live level: the press's velocity, then the page-level pad door's `arsenal:padlevel` events (the phone's tall pads: the finger's height), slewed so it never zippers. At a level of 0.95 or more the row strobes, on one bar-locked strobe clock shared by every kick, at 1.9 flashes a second at most (2 beats a flash at 150 BPM): under the flash gate by itself; the final limiter stays the backstop. Shift with a key presses at velocity 1. |
| Pad 2 / key `2` | LASERS: a hit. The tier depends on how soon it follows the last one. Holding it gates the lasers on quarter notes. |
| Pad 3 / key `3` | PHRASE GO: Daniel's phrase starts on the next bar line (a press just after a line lands on it). Pressed while it runs, the next repeat (a new variant) starts on the next bar line. |
| Pad 4 / key `4` | PHRASE NEXT: the current step ends on the next bar line; the rest follow from there (the camera plan moves with them). |
| Pad 7 / key `7` | PHRASE STOP: the phrase ends on the next bar line and hands the rig back to the section's look over a beat. |
| Pad 6 / key `6` | FLY-OUT: the truss and lip beams burst outward from the centre. |
| Pad 10 / key `0` | DROP NOW: the drop starts on the next downbeat (and with it the drop's phrase). |
| Pad 8 / key `8` | MORPH: the rings move to the next formation of the deck (home, orrery, spiral, vortex, crown, portal), starting on the next bar line and landing on the bar line their slowest ring can make; the camera glides while they move and cuts on the landing to the formation's hero view. Dream formations (orrery, spiral) turn their rings; the rest are real-capable. |
| Pad 9 / key `9` | HERO: the energy beam's discharge up the rings' axis through the core, on the next ONE, once per eight bars (a press while it recharges does nothing; the HUD shows the charge). Its flash goes through the FlashGate. |
| F1, F4, F5, F6, F9 | Strand master, lasers, haze target (it moves over minutes), speed (detents 1/4 to 4; a phrase's own timing is in beats and ignores it), grand master. The sliders in the HUD do the same. |
| `C` / `Esc` | Play the next camera shot in motion, looping over its own bars (v2; every shot in the set, the held RING_THREAD included) / give the camera back to the director (or the phrase). |
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

## The ring formations (v2, `formations.js`, `sets/source-v1.json` → `ring_formations`)

Daniel, before sleep on 2026-10-26: "we could have the light rings morph possibly and re-arrange into other patterns ...
or they form some sort of spiral with an energy beam inside, or perhaps an array that looks similar to the [Destiny
place]". The place is the Dreaming City's orrery; his words about it are the brief: "really complex motion that you could
stare at for a long time", "how it flickers when you get close to it", "wireframe elements", "the effect on a spinning
ring", "beautiful no matter where you look at it from", "the way it gets revealed, but it has depth".

- **The orrery** (dream): the rings tilt apart into nested gimbals (55 / 80 / 60 / 30) round a glowing violet core (a
  swirling LED sphere with a meridian line, a dotted equator, port lights and a glow in the haze) and turn at prime beats
  per turn (R0 spins in 113, R1 precesses in 89, R2 the other way in 67, R3 in 37): each is beat-locked, the set repeats
  after about 25 million beats. Five thin wireframe bands hug the core at their own rates; eight planets ride the rings
  on short arms; 1,600 star motes hang in the haze, densest near the core; the line-work shimmers as the camera comes near
  (per cell, so the frame's sum holds still); the halo heads and the ring lasers draw spokes into the core, which stops
  them. It reveals in depth order: the core, the bands, ring 3, 2, 1, the dial's ticks written on clockwise, the planets,
  the heads, the lasers' lock-on, the motes.
- **The spiral tunnel** (dream, the Well of Rings): the rings coplanar at 55 and stepped 3 m apart up their shared axis (a
  true funnel), each lit on a 300-degree arc whose gap steps 40 degrees ring by ring into a turning spiral staircase; a
  ladder chase falls down the well each beat; a bead rides ring 1; the energy beam (a narrow column from the floor upstage
  of the deck, through every ring's centre, to the roof) wrapped in a twisted cage of the ring lasers that the discharge
  straightens.
- **08 Vortex Cone** (real): every halo head aims at a circle round the axis turned by an offset that swings +-60 degrees
  over two bars; the HERO laser draws a tube up the axis.
- **09 Hyperboloid Crown** (real): rings 1 and 2 tilt flat; their heads aim up at circles on the roof turned +D and -D,
  D breathing 0 -> 180 -> 0 over 16 bars: cylinder, hourglass, every beam through one knot, and back.
- **10 Portal Membrane** (real, after the lift): the cluster lifts 4.5 m before ring 0 stands upright; its heads converge
  on a point 10 m behind it (the beams cross and end on the back wall).

The real numbers (`ring_rig`, the one source): each ring is 3-point hung at its outer rim on 0.5 m/s hoists, so its tilt
rate is the hoist speed over its radius: R0 2.0 degrees a second (a 35-degree tilt takes about 17 s), R3 9.5. A ring lifts
before it tilts and lowers after; every tilt is clamped into the ring's legal window at its height (ring 0 at its 14 m hang
clears the deck and the back wall only between 47.5 and 63 degrees). Every beam a formation owns ends on the roof, the
deck, the floor upstage of it, the back wall or the core, never on the crowd or the audience stands (the hit check now
models the stands); the Qlimax-faithful home keeps the 2014 rule: the ring is still and the looks own its light.

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
| `sets/source-v1.json` | The v1 rig and show as data (`arsenal.arena/v1`): v0's types, objects, groups, effects, looks, lasers, atmosphere, themes and cameras, plus the halo, the verticals, laser groups, presets, the ring-effect library, the phrases and (KICK v2) the kick block: the deck of rows, the velocity bands, the level, the strobe. |
| `sets/source-v0.json` | The v0 rig, unchanged. |
| `rig.js` | Validates the scene and expands it deterministically. Polar repeats by ring parameter, clock angles and levels, `where`/`union` groups, ring-mounted projectors, `aimAt` (world-locked aiming). Also the MVR bridge and the head geometry. |
| `phrases.js` | The cue sequencer: phrases as data, variants and per-repeat values, the camera plan, the runner (Go, Next, Stop, loop), and the glue that plays its events. |
| `grid.js` | The one beat position for everything, plus the demo clock. |
| `effects.js` | Spreads (MA, ChamSys and Hog in one object), waveforms, beat-locked phase accumulators, the unison floor rule; v1: block "ties", cue-anchored phase, one-shots, clean starts, sparkle. |
| `programmer.js` | Looks, effects, pads (HTP), masters, theme colours, the colour wheel, motor physics; v1: the phrase layer (LTP over the look) and the FlashGate. |
| `kick.js` | KICK v2: the set's kick deck (a seeded shuffle-bag that only deals a row the hit will show on), the two buttons, hold = gate, the live level, velocity's animation (peak, or a V2 motion as a sweep or a chase, sized to the tilt motor), the one bar-locked strobe clock under the flash gate. Without a `kick` block (source-v0) it is v0's strand lift exactly. |
| `kinetics.js` | The hoists (jerk-limited), the formations, and time-priority landing on bar lines; v2: the S-curve with cruise, the strand shapes (arch, valley, ramp, stairs), and the RingRig (lift and tilt on the rim hoists, lift before tilt, the dream rotators). |
| `formations.js` | v2: the ring formations (home, orrery, spiral, vortex, crown, portal): MORPH, HERO, the reveal, the light layer, the scenery (core, bands, planets, motes), the energy column, the camera's annuli, and the safety check of every beam's end. |
| `lasers.js`, `lasers3d.js` | A minimal laser brain on the Lasers v2 contract (v1: laser group lines with shapes and gates, heads past the 21, an aim side channel), mapped onto 33 projectors in 3D with physical power sharing. |
| `atmos.js` | The haze medium: the hazers, the lag, our own tileable noise, and two caps since VJ V2 (haze and fog 0.26 /m, CO2 and smoke plumes 15 /m: opaque white CO2 is possible; the white-out guard is flash.js and the FlashGate, receipts in tests/stage_atmos.test.mjs). |
| `camera.js` | Shots as data, centripetal Catmull-Rom paths driven by the beat position, the director that cuts on bars; v1: a phrase's camera plan; v2: the strand frame (shots round the live centre line, the under-ride), the formation-validity filter and the guard (never a shot within 1.5 m of a rung), roll curves, the easings arrive_fast, snap and arrive_u, the dolly zoom, and the landing grammar: one glide while the hoists move, the cut ON the landing bar line to the formation's hero view (`cameras.formation_views`, the ring formations' among them). |
| `show.js` | Sections (v1: a section may name a phrase), the demo plan, and DROP NOW. |
| `flash.js` | The final-frame flash limiter: at most 3 flashes a second, red included. |
| `render.js`, `shaders.js` | The three.js r186 renderer and our own GLSL, composed with the house library; v1: the crowd near the lens is not drawn (4 m) and its arms hold still (10 m). |

Tests: `node --test tests/stage_*.test.mjs`. The browser receipt: `node arsenal/lanes/stage_verify.mjs` (default phases
load, clock, camera, phrase, engine, flash, storm, the picture measures, and v2's orrery and spiral: the gimbals' prime
rates, the core and its scenery drawn, the spiral's landing with the camera's cut on its bar line, the HERO discharge on
its ONE through the FlashGate, and every frame through the near view and the discharge judged by the flash counter; `--phases flash3m --flash-scale 0.75` runs the
three-minute crowd-on run in ten-second bursts; `--phases sheet-phrase --sheet-dir <scratch>` the phrase's sheet). It
runs headless SwiftShader only, under the house GPU lock, on the test band.
