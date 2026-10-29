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
- PALETTES (2026-10-28, `../palettes.js`, `../palettes.json`; design `research/in-flight/palettes-2026-10-28/DESIGN.md`):
  thirty palettes drive every colour (the roles, both kicks, the heads' wheel plans, the splits and pins, the strand's
  gradient and tempo, the lasers' fans, the air). `?palette=<id>` picks one (`?theme=` is read the same way first; the
  three wave-1 set themes that are not palettes, `genesis-indigo`, `vex-conflux`, `anti-sun`, still load by name);
  the show's own is `show.palette` (Source Violet). Live: key `P` (Shift+`P` back), the phone bar's PALETTE pad, or
  the pad map's `palette-next` / `palette-prev` (KeyLab pads 11 and 12): the change lands on the next 16-bar line, a
  neighbour crossfading over 4 bars, anything else through a one-beat dip. The white kick is the palette's white and never
  turns a wheel; the colour kick lifts each cell inside the palette and keeps the strand's helix.
- HAL 4000 cubes (2026-10-29, `cubes.js`, shaders.js `CUBE_HAL_*`): the strand's cubes drawn as light. Round 2: two
  pillowy rounded-square loops a face (the outer one hot on the face that looks at the viewer and dim on the others, the
  inner a hairline in the glow's colour), only the outer loop on the far faces, a low inner bloom, edge-on faces faded out,
  and the cubes BLEND BY MAX so faces and neighbours never sum to cream. They spin slowly on the rung's axle with a gentle
  wobble (the rung's dot strip always meets the inner face square). The core is the programmer's own cube colour; the
  glow runs the whole strand from the palette's deep to its B (each end at unit brightness, mixed through OKLCh), and a
  kick on a cube's cells takes its glow with it (a white kick turns the whole cube white, as the solid cube does). A setup
  names its own colours through `window.__stage.cubeTint({glowTop, glowBottom, coreTop, coreBottom, glowMix})` (linear
  RGB, null fields keep the palette's; `cubeTint(null)` clears); as a URL A/B `?cubeglow=0040ff,ff2000&cubecore=a0f0ff,ffb040`
  (first and last rung). `?cubes=hal|solid` (a viewer gets HAL, automation the solid cubes), key `U` toggles,
  `?cubetumble=0` (or `window.__stage.cubes({style, tumble})`, tumble 0..1) holds them square.
- Kinetics wave A and the orrery (2026-10-27): `?ring=orrery` (or `spiral`, `vortex`, `crown`, `portal`) opens with the
  rings in that formation; pad 8 (key `8`) MORPHs to the next one on the next bar line and pad 9 (key `9`) fires the
  energy beam's discharge. Drawn for the Dreaming City palette: `index.html?demo=1&theme=dreaming-city&ring=orrery`.
  `?strand=arch` (or `valley`, `ramp`, `stairs`, `helix-sine`) lands a strand shape on the S-curve instead of the sections'
  waves.

| Control | What it does |
|---|---|
| Pad 1 / key `1` | KICK WHITE (`kick.js`, round 2): the next AREA of the set's kick deck (four: all the rings' LEDs; the beams, that is the truss, the lip, the towers, the pods and both delay towers; the halo; the strand) that the current camera shot shows most of goes FULL-INTENSITY WHITE, overriding the look (which runs on underneath) and crossfading back to it on release. The light starts at the press (the next frame), with a short punch over the held level. Held, it stays lit; a tap is a one-second hit. A press while the area is still lit re-strikes it: the white kick deals a fresh motion, so a roll of taps keeps the area up and moving instead of flashing it. Velocity picks the animation: under 0.45 the area simply on, from 0.45 a sweep (heads tilt through a V2 motion, LEDs chase it), from 0.85 twice the throw (within the tilt motor). |
| Pad 5 / key `5` | KICK COLOUR: the same, in a vivid colour of the set's contrast palette at least 90 degrees of hue from what the area shows (and 60 from the other kick's); a re-strike steps to the next palette colour of about the same brightness, so every tap of a roll is a new colour without a brightness flash. Moving heads change colour too: their wheel goes to the nearest slot the short way round that never passes the red slot. Held together with KICK WHITE, the two light two different areas. What each pad does is data: `kick.kinds` in the set, named by the pad map. |
| Kick level | While a kick is held its brightness follows its live level: the press's velocity, then the page-level pad door's `arsenal:padlevel` events (the phone's tall strips: the finger's height), slewed so it never zippers, through a curve that keeps the whole strip high (intensity = 0.5 + 0.5 x sqrt(level): the bottom of the strip is half intensity). Held 0.25 s at a level of 0.95 or more the area strobes (a tap never does), on one bar-locked strobe clock shared by every kick, at 1.9 flashes a second at most: under the flash gate by itself; the final limiter stays the backstop. The page hands the kick the limiter's headroom each frame: with the budget nearly spent a hit stays up and still instead of punching, stepping colour, moving or starting its fade, so the limiter does not have to dim it. A kick turns a moving head's colour wheel only on a way that does not flicker (never through red, never through a slot much darker or brighter than where it has been); when the kick's colour lies behind the wheel's dark slots the head keeps its colour at full and the LEDs carry the colour. Shift with a key presses at velocity 1. |
| Pad 2 / key `2` | LASERS: a hit. The tier depends on how soon it follows the last one. Holding it gates the lasers on quarter notes. |
| Pad 3 / key `3` | PHRASE GO: Daniel's phrase starts on the next bar line (a press just after a line lands on it). Pressed while it runs, the next repeat (a new variant) starts on the next bar line. |
| Pad 4 / key `4` | PHRASE NEXT: the current step ends on the next bar line; the rest follow from there (the camera plan moves with them). |
| Pad 7 / key `7` | PHRASE STOP: the phrase ends on the next bar line and hands the rig back to the section's look over a beat. |
| Pad 6 / key `6` | FLY-OUT: the truss and lip beams burst outward from the centre. |
| Pad 10 / key `0` | DROP NOW: the drop starts on the next downbeat (and with it the drop's phrase). |
| Pad 8 / key `8` | MORPH: the rings move to the next formation of the deck (home, orrery, spiral, vortex, crown, portal), starting on the next bar line and landing on the bar line their slowest ring can make; the camera glides while they move and cuts on the landing to the formation's hero view. Dream formations (orrery, spiral) turn their rings; the rest are real-capable. |
| Pad 9 / key `9` | HERO: the energy beam's discharge up the rings' axis through the core, on the next ONE, once per eight bars (a press while it recharges does nothing; the HUD shows the charge). Its flash goes through the FlashGate. |
| F1, F4, F5, F6, F9 | Strand master, lasers, haze target (it moves over minutes), speed (detents 1/4 to 4; a phrase's own timing is in beats and ignores it), grand master. The sliders in the HUD do the same. |
| `C` / `Esc` | Play the next camera shot in motion, looping over its own bars (v2; every shot in the set, the held RING_THREAD included) / give the camera back to the director (or the phrase), and the distance with it. |
| `Q` `W` `E` | Camera DISTANCE (2026-10-29, `distance.js`): CLOSE, MEDIUM, FAR on top of whatever shot is running (left hand, near to far, left to right). The camera starts moving at once and lands on a beat line; the lit key again hands distance back to the director over two beats; Shift + key cuts on the next beat instead. Phone: the CLOSE · MID · FAR segment in the pad bar (on a phone under about 770 CSS px wide the bar takes two rows and the kick strips stand above it). |
| F8 | Camera distance as a continuous fader (KeyLab CC 112) with soft takeover: it does nothing until it passes the distance the camera has now. The HUD's F8 slider shows the live value. |
| `H`, `F` | Hide the HUD, go full screen. The HUD's phrase row names the step, the variant, the repeat and the beats left. |
| Chords, strums, fades | THE CHORD PHRASING (below): keys pressed together are one gesture, a fast run is a strum, a slow run of neighbouring number keys is a fade (descending out, ascending in); `B` held makes the number row a fader. `Esc` also hands a fade back over four beats. `?grammar=0`: every key is a single, as before. |

## The chord phrasing (2026-10-29, `grammar.js`, `ensemble.js`)

Daniel, after recording two takes: "for parts of it i played the "wrong" buttons on my keyboard but it felt like an
intuitive way to express fade in and fade out for the calmer moments" / "i mean like 8 7 6 5 4 then 456789"; "like 5 7 6
could become laser sections 1-4 sections 8-12 then everything in the middle, then all of them could flash together";
then "lets also land the chord phrasing." The design of record is the round-3 design
(`docs/library/design/20261028_kick-vocabulary-round3-codex-2026-10-28_4a3a13.md`, sections 4-8); this is its
recogniser and the ensembles it names, not its focus selectors, combos or phrase library.

**A single never waits.** Every key is decided on its own keystroke: its action fires on the frame it is pressed, exactly
as before. What follows a key is what can change:

| You play | It is | On the Stage |
|---|---|---|
| Keys within W = clamp(beat / 4, 60, 110) ms of the first (97 ms at 154 BPM) | a chord | every key's own action (the union of their areas), under ONE attack: a later kick joins the first one's punch at its age, never a second punch. A join only ever makes a punch older or leaves it: a punch the flash governor refused stays refused, and a kick still lit from a tap (a re-strike) keeps its old punch; a re-strike is never the chord's attack, so a fresh kick later in the chord keeps its own. `C` in a chord asks for one shot at most; GO / NEXT / STOP collapse to the strongest (STOP > NEXT > GO). |
| Three or more neighbouring number keys one way, each within 90 ms, all within 300 ms | a strum | the same, lit in the order played inside the one attack; any other key within W of the strum's first joins it too (a mash of 4 5 6 and 1 is one attack) |
| Three neighbouring number keys one way, each 110-450 ms apart (within 0.28-0.95 of a beat) | a fade (BREATH) | the first two keys did their thing; the third takes over and fires nothing: the look's own light (heads, LEDs, the room's fill, the lasers' master) moves a ninth per key, down for a descending run, up for an ascending one, ramping a ninth per 120 ms. Any neighbouring key within 450 ms keeps fading, either way (a deliberate hit on a neighbour inside that gap is a fade step too); a longer gap or a jump ends it and the level stays where it was left. Only when the fade can move the light that way: a run up the row at full light (or down it at black) is ordinary playing and every key fires; a step past full or black ends the fade and that key fires. While the light is below the look's, a quiet corner label (`breath 44 % · Esc back`) says so, with the HUD hidden too. The kicks and the grand master are never faded: a vivid hit over a candlelit room. A run's first two keys' still-pending commands are withdrawn where they can be (a HERO still armed, a phrase GO still armed, a tapped kick's linger); MORPH's travel and anything already shown stay. |
| `B` held, then number keys | a fade from the first key | no key fires; the first anchors, each next one moves the level by (its position - the last) / 9. The clean way to fade through 9 (HERO) and 8 (MORPH). |
| Two-key chords of one gap, moving (0+8, 9+7, 8+6 ...) | a moving interval | recognised and counted as one gesture; each pair plays as a chord (the moving-band look is not built yet) |
| `Esc` | | the camera back to the director, and the fade back to the look over four beats |

Sources never mix: the keyboard (real keystrokes), the phone (its pad bar and strips) and the KeyLab (pads 1-10 through
the engine) each make their own chords. Strums and fades read neighbours on the PC number row only: the phone bar's pads are
not in number order and the KeyLab's pad layout has not been captured, so there it is chords only. Focus or visibility lost
lets go of every key of the keyboard and the phone; a dropped engine link lets go of the KeyLab's.

Not built, on purpose: the design's focus selectors (K camera, V light, L laser, P order) -- `L` (look) and `P` (palette)
are already taken, so they need new keys or the phone's buttons first; the named combo (3,3,3,1); LAND timing; the BREATH
ribbon on the phone; KeyLab pad 11 as BREATH (the design's proposal) -- pad 11 is PALETTE NEXT today.

Receipts: `node --test tests/stage_grammar.test.mjs` (the design's table rows this covers, with the boundaries W-1 / W / W+1,
89 / 90 / 91 and 109 / 110 / 111 ms); `node arsenal/lanes/stage_verify.mjs --gpu --lock-dir <the GPU lock> --phases chords`
(real keystrokes on the Stage: one attack per chord against two as singles, the limiter and the flash count unchanged, the
fades' level path, stills); `node arsenal/lanes/grammar_replay.mjs <take.jsonl> ...` (Daniel's private takes through the
recogniser: counts and interval distributions only).

## Camera distance: close, medium, far (2026-10-29, `distance.js`)

Daniel: "can we think of a control scheme for camera distance so that i can trigger between closeup medium and far."

Distance is shot SIZE, its own axis on top of the director's shots: how wide a slice of the room the frame holds at the
shot's subject (its look point). CLOSE holds 14 m across (the inner rings fill the frame), MEDIUM 34 m (ring 0 with its
halo), FAR 80 m (the whole deck and its towers); the scale is logarithmic and MEDIUM is its middle. Measured on the GPU
(receipt `stage_verify --gpu --phases distance`): on HALO_LOCK the dolly runs 22.9 / 54.7 / 104.8 m from the rings and their
on-screen box is 5.7x larger at CLOSE than at FAR; on FOH_WIDE 11.6 / 27.8 / 66.6 m and 9.9x.

- **A dolly, never a zoom.** The camera slides along the line from the subject through the shot's own position, by one
  factor over the whole move, so a crane still rises, an orbit still orbits and a crash zoom still lands; the lens, the
  look point, the roll, the handheld wander and the shot's exposure stay the director's (a lit surface or a beam in haze
  has the same radiance from 14 m as from 80 m: only its size changes, so the shot's EV is right at every distance).
- **Limits, every frame.** The shot's comfort range (a fast shot is never scaled past the house drone's 15 m/s; never
  nearer the subject than 3 m; a dolly zoom keeps its own size), the venue's walls, roof and the crowd's heads, the
  RIGGING GRID (a shot below it never lifts the lens within 1 m of its beams: FAR on the top-down and high crane shots is
  held there, where it used to rise into the beams and render black), the hall's structure, and the strand and rings
  live: never within 1.5 m (camera.js's rule; the camera aims for 2.5 m). A shot whose own camera stands outside the
  floor (the side-stand platform, a camera rising out of the crowd) has the room widened to its camera. The room is read
  along the shot's own path half a second ahead, so the camera eases away from a rung or a wall before it arrives; it
  never jumps: the size changes at most e^4.5 a second and accelerates at most 25 (ln) a second a second, braking into
  a limit. When the rig still reaches the lens faster than any move could keep it clear (a formation swinging into it),
  the camera CUTS to a clear size -- on the next beat line when that comes first -- and the cut is logged like any other.
  A press is planned to what the room allows, and the HUD's camera row says "held at" what holds it (the venue's edge,
  the rigging grid, 1.5 m+ from the rig); the stop itself stays asked for, so the next shot gets the full stop.
- **Timing** (the round-3 design, sections 3, 5, 6): a press starts at once and lands ON the first beat line at least half
  a beat and the comfort time away (the subject's size changing at most e^4.5 per second at the move's peak: at 150 BPM a
  step lands on the next beat or the one after, CLOSE to FAR in two or three). A second press bends the move from its
  current speed. Shift: a clean cut on the next beat line, never within 2 beats of the last cut (the director's, a C-key
  shot or a distance cut), and with the director's own next cut (his next entry, or a guard or swap he has scheduled)
  when that is under 2 beats away; a move already under way eases to rest within a quarter second, then nothing moves
  until the cut. The handback blends over two beats. A key press lets go of the F8 fader: it must pass through the new
  stop before it drives the camera again.
- **State and doors.** The HUD's camera row: `distance auto (as shot: far) · Q W E`, `distance CLOSE manual → beat 133`,
  `distance 0.42 (F8) manual`. The page's window event `arsenal:camdist` {mode, stop, v, ...} fires only on a change
  (`window.__camdist` keeps the latest); the pad map may name `distance-close`, `distance-medium`, `distance-far`,
  `distance-auto`; the set's `show.faders` may name another control `distance` (else F8 = CC 112). A shot may carry
  `distance: false` (it keeps its size) or `distance: {k_min, k_max}`.

## Flash protection: the viewer's choice (2026-10-28, `../lib/flash-consent.js`)

Daniel: "have it be a toggle, as it should be, you get a siezure warning and its up to you what you do with it, default
is on, on the warning you can uncheck it". On a first visit, before the show starts, the page shows a photosensitivity
warning with one checkbox, **Flash protection**, checked, and **Start**. The choice is remembered in this browser (one
key, `arsenal.flashProtection`, for the Stage and the VJ page); the HUD has a quiet **Flash protection** checkbox to
change it later. Nothing reminds the viewer afterwards.

| URL | |
|---|---|
| `?flash=on` / `?flash=off` | decides from the address, no screen, not remembered (tests, kiosks) |
| `?flash=ask` | shows the screen again |

A browser driven by automation (`navigator.webdriver`: every house lane) gets protection on and no screen. With
protection on, `flash.js` judges every frame as it always has. With it off the page asks no limiter: no meter, the apply
pass is the identity (the canvas is the frame as drawn, receipt `arsenal/lanes/flash_toggle_verify.mjs` phase
identity), and the kick's flash governor sees a full budget. The FlashGate and the kick strobe's own cap are unchanged.

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
| `programmer.js` | Looks, effects, pads (HTP), masters, theme colours, the colour wheel, motor physics (every zoom target held inside its fixture's range), v1: the phrase layer (LTP over the look; a release hands a head's zoom back to its home) and the FlashGate. |
| `kick.js` | KICK v2: the kinds (what a kick does, as data), the deck of areas (a seeded shuffle-bag that deals only an area the camera shows and the hit visibly changes, the most visible first), the override of intensity and colour, the palette lift (each cell its own role's lift, the helix kept; the re-strike swaps the luminance-matched ladder; the heads by the palette's wheel plan), the wheel's red-free short way (with programmer.js), the punch, hold = gate and the linger, the live level and its curve, velocity's animation (a V2 motion as a sweep or a chase, sized to the tilt motor), the one bar-locked strobe clock under the flash gate, and the flash governor (the limiter's headroom holds back the kick's optional changes). Without a `kick` block (source-v0) it is v0's strand lift exactly. |
| `kinetics.js` | The hoists (jerk-limited), the formations, and time-priority landing on bar lines; v2: the S-curve with cruise, the strand shapes (arch, valley, ramp, stairs), and the RingRig (lift and tilt on the rim hoists, lift before tilt, the dream rotators). |
| `formations.js` | v2: the ring formations (home, orrery, spiral, vortex, crown, portal): MORPH, HERO, the reveal, the light layer, the scenery (core, bands, planets, motes), the energy column, the camera's annuli, and the safety check of every beam's end. |
| `lasers.js`, `lasers3d.js` | A minimal laser brain on the Lasers v2 contract (v1: laser group lines with shapes and gates, heads past the 21, an aim side channel), mapped onto 33 projectors in 3D with physical power sharing. |
| `atmos.js` | The haze medium: the hazers, the lag, our own tileable noise, and two caps since VJ V2 (haze and fog 0.26 /m, CO2 and smoke plumes 15 /m: opaque white CO2 is possible; the white-out guard is flash.js and the FlashGate, receipts in tests/stage_atmos.test.mjs). |
| `distance.js` | Camera distance (2026-10-29): shot size on a log scale, the quintic moves landing on beat lines, the clean cut, the handback, the fader's soft takeover, and the per-frame limits (comfort, venue, the rigging grid, structure, the 1.5 m rule) along the shot's own line to its subject, read half a second ahead and followed at a capped rate and acceleration. |
| `camera.js` | Shots as data, centripetal Catmull-Rom paths driven by the beat position, the director that cuts on bars; v1: a phrase's camera plan; v2: the strand frame (shots round the live centre line, the under-ride), the formation-validity filter and the guard (never a shot within 1.5 m of a rung), roll curves, the easings arrive_fast, snap and arrive_u, the dolly zoom, and the landing grammar: one glide while the hoists move, the cut ON the landing bar line to the formation's hero view (`cameras.formation_views`, the ring formations' among them). |
| `show.js` | Sections (v1: a section may name a phrase), the demo plan, and DROP NOW. |
| `grammar.js` | The chord phrasing's recogniser (pure): singles on their own call, chords, strums, fades (slow sweeps and `B`), moving intervals, auto-repeat, releases by press id, cancel per source. |
| `ensemble.js` | What a chord, strum or fade does, as intents over the page's own actions: one attack identity per lineage, transport collapsed, one camera composition, the BREATH level and its layer. |
| `flash.js` | The final-frame flash limiter: at most 3 flashes a second, red included. v2 (2026-10-28): the same windows, counters and limits, met with smooth fields over the cells' corners (a soft dimming, or a glow in the region's own colour) instead of v1's per-cell holds, which froze whole tiles with hard edges; see "Flash protection" below. |
| `render.js`, `shaders.js` | The three.js r186 renderer and our own GLSL, composed with the house library; v1: the crowd near the lens is not drawn (4 m) and its arms hold still (10 m). |

Tests: `node --test tests/stage_*.test.mjs`. The browser receipt: `node arsenal/lanes/stage_verify.mjs` (default phases
load, clock, camera, phrase, engine, flash, storm, the picture measures, and v2's orrery and spiral: the gimbals' prime
rates, the core and its scenery drawn, the spiral's landing with the camera's cut on its bar line, the HERO discharge on
its ONE through the FlashGate, and every frame through the near view and the discharge judged by the flash counter; `--phases flash3m --flash-scale 0.75` runs the
three-minute crowd-on run in ten-second bursts; `--phases sheet-phrase --sheet-dir <scratch>` the phrase's sheet; `--phases distance --gpu`, attended, the camera distance's
receipt: the same shots at the three sizes, the keys, the fader and the phone segment). It
runs headless SwiftShader only, under the house GPU lock, on the test band.
