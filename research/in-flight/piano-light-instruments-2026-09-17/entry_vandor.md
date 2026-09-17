# Vandor's entries — "Instruments of light" (2026-09-17)

Two entries from the claude seat, one section each, in the order they landed. Both are contract modules under
`arsenal/web/piano/instruments/`, built on `../harmony-feel.js` and `../moment.js`, and both were self-rendered on the lane
harness (a scratch copy of the current `arsenal/` with `state.sounding`, ports 8983/9083 and 8984/9084, GPU lock around
every burst, synthetic MIDI only). Tests: `tests/piano_light_vandor.test.mjs`. **Repair round 1 (2026-09-17 afternoon)**
answered the verifier's must-fixes: the Ornithopter's chromatic cluster whiting out at the roots (a flash budget, a
knuckle core in key units, a per-channel sustained cap, and the flash claiming its pixel), the Abyssal's intermittent black
frames (the bell shader's `pow` terms), and the measurements below that did not survive a same-lane re-measurement.
**Repair round 2 (2026-09-17, late afternoon)** answered the second pass: repair 1's knuckle core had hidden behind the
clasp and the piston standing in front of the wing root, so a lone strike lost its spark and never reached the bloom line;
the core now runs up the wing from the blow (`KNUCKLE`), the flash budget was re-tuned for it (`FLASH_SHARE` 3.0 over one
semitone), and the two claims about the strike and about fixture 6 below were rewritten from the re-measured lane.

## light-vandor-ornithopter — Ornithopter

**Module:** `arsenal/web/piano/instruments/light-vandor-ornithopter.js` · **name:** Ornithopter

### The idea

Daniel asked for the Dune ornithopter wings. So the instrument *is* an ornithopter: a long insect lies behind the keys,
head at the bass end, tail at the treble. An armoured head with two compound lenses (they take the lowest sounding colour)
and antennae reaching forward, a thick thorax on six jointed legs planted on the floor, a segmented chitin abdomen tapering
to a tail with two cerci, propped by four prolegs. Sand-gold spars on shadow. From its back rise 88 wing membranes, one per
key, in two ranks like a dragonfly's fore and hind wings (white keys forewings, black keys hindwings): long, wide and soft
in the bass (A0 a 30-unit wing), short and stiff in the treble (C8 10.5 units).

### The strike

A thorax piston under each wing root snaps up and hits the wing: a spring model (`PISTON`), fired at 44 units/s for a
ppp note and 78 for fff, free flight on the way up, a rebound off the root, then it rests on its check while the finger is
down. The membrane lights in the note colour and **beats**. The knuckle flashes where the piston lands (`FLASH_EXP` 2.0,
`FLASH_GAIN` 1.8, `TAU_FLASH` 0.09 s): a hot core a third of a key wide **across** the wing (`exp(−12 u²)`, u in key units
whatever the wing's length, so the cores of neighbouring wings never overlap) that runs **up** the wing from the blow
(`exp(−((s − 0.07) / 0.08)²)`, s in wing units: over half height at the root, gone by a fifth of the wing), at a gain of 5.5
over the note colour times the flash (the `KNUCKLE` block, one vec4 uniform); the host's bloom draws its halo, and a runner
carries the flash up the wing over `flashTravel` 0.17 s. Repair round 2 put the core there: repair 1's core was a disc
centred on the root itself, and the clasp and the piston that stand in front of the root hid its brightest part, so a lone
v120 strike showed no spark and never crossed the bloom line (C4's column peak 0.867, 0 px over 0.9; round 1's 0.917 / 613
px had come from a disc four times the radius spilling round them). Measured on the final bytes by the verify lane (ports
8985/9085, 16:9 and 9:16 Ultra, `verify/out/r2/probe-x6`: a lone v120 strike on each pitch class of octave 4, the note's column on
the strike frame): every one of the 12 hues crosses 0.9 on screen in both framings, 16:9 C4 0.948 (1444 px over 0.9), Db4
0.915, D4 0.923, Eb4 0.981 (3365), E4 0.918, F4 0.951 (1452), Gb4 0.917, G4 0.921, Ab4 0.929, A4 0.930, Bb4 0.947 (965),
B4 0.920; 9:16 0.927 (Db4) to 0.983 (Eb4); 0 near-white on every frame. Round 1 had crossed on four hues only (C4 0.918,
Eb4 0.967, F4 0.921, Bb4 0.909; the rest 0.82–0.88): the on-screen number is hue-dependent because the host's Neutral tone
map holds a saturated hue's colour, so the dim hues (Db, E, Gb, B) need the most light to read as luma 0.9, and the lens
of the rule is the bloom line itself, which every hue's core now clears by a wide margin. That flash is the only light
allowed over the bloom line, and three rules keep it there when wings meet (repair round 1: before them a chromatic
cluster at fff whited out at the roots, 845 / 1351 px):

- the light pass blends with `MaxEquation` and caps every sustained **channel** at 0.85 in the shader (the max over ten
  hues is a neutral whose luma is the channel cap, so overlapping wings never stack over the line; a luma cap let a blue
  wing's blue channel reach 1.8 and ten hues stack to 2037 hot pixels);
- the flash claims its pixel instead of stacking on the capped membrane: the sustained part gives way as the flash nears
  0.9, so a pixel is never more than the larger of 0.9 and the flash itself;
- **wings flashing together share one flash, steeply and only next door** (repair 2): each wing's flash is divided by
  (1 + n)^`FLASH_SHARE` (3.0; 1.0 before), n the wings flashing within `FLASH_REACH` 1 semitone (3 before), counted smoothly
  below `FLASH_NEIGH` 0.25 so a neighbour's decay never pops a flash. A lone strike keeps its whole flash; a semitone pair
  shows an eighth each; the middle of a chromatic cluster a twenty-seventh; wings two or more semitones apart keep whole
  sparks, so a chord in thirds strikes with every spark. The host's hues alternate round the wheel (C cyan, Db red, D blue,
  Eb yellow, E magenta, F green, Gb red, G azure), so semitone neighbours are near-complementary and the light pass's
  per-channel max of two such cores is a neutral, which the bloom takes to white at about two linear: with the restored
  core an fff D4 + Eb4 dyad whited out at `FLASH_SHARE` 1.0 (364 px) and 2.0 (389) and cleared at 3.0 (`out/repair2/share-*`),
  while two whole fff sparks at 2, 3, 4 and 5 semitones never did (`x12`: 0 near-white, up to 6155 px over 0.9 on the
  strike frame for cyan + yellow at a minor third, 10185 for the ten-note spread chord at v127 in 16:9, 18106 in 9:16).

Measured after repair 2 (lane ports 8983/9083, 16:9 and 9:16 Ultra, the stage above the keys): **0 near-white pixels** on
the 10-note chromatic cluster C4–A4 at v127 (strike, +0.5 s, +2 s), on E4–C#5, on the spread 10-note chord, on D4 + Eb4 at
v127 struck together and 0.12 s apart (strike, +1, +3 and +6 frames, the runners crossing), on a close C major triad and a
five-note cluster at v127, on same-frame fff dyads at 1 to 5 semitones over C4 and over D4, on all 12 pitch classes at
v120, and on every shared fixture (`out/repair2/clusters-final`, `x6`, `orn`); sustained light is under the line again by
+0.5 s in every cluster (0 px over 0.9 except the pastel of ten stacked hues, below).

### The beat (the Dune blur as physics)

Nothing is animated frame by frame to fake the blur. Every pixel of a beating wing draws the exact time average of a blade
sweeping a sinusoid: the arcsine density, `F(x) = 1/2 + asin(x/A)/π`, coverage `F(φ − c + hw) − F(φ − c − hw)`. It is
bright at the two ends of the stroke where a real wing dwells and translucent in the middle — what a film camera saw of the
ornithopter wings. The stroke half-amplitude is `AMP_BASS` 19° at A0 to `AMP_TREBLE` 3° at C8 (power 1.7 over pitch), the
tip sweeps further than the root (`bend` 0.75), and the two spars are swept the same way, so a beating bass wing is bounded
by two bright arcs and nearly hollow between them. A slow breathing of the amplitude (`VIB_HZ` 2.2 → 6.0 Hz, ±12 %) and a
strobe ghost of the blade in the bass only (`GHOST_HZ` 1.6 → 5.0 Hz, fading out toward the treble) keep it alive without
strobing: over the 60 Hz window after a strike the note column's luma moves at most 3.2 % (16:9) / 2.7 % (9:16) frame to
frame at A0 (0.7–0.9 % on average) and about 1 % at C2-C8. In the treble the blade stays crisp and a slow travelling shimmer runs along the membrane
instead.

### Velocity

Stroke amplitude, membrane brightness and piston speed all rise with velocity. Body = v^1.35, shown light =
1.6 · body^0.75 (the 0.75 keeps a soft note readable: v30 shows 24 % of ff), stroke = AMP(pitch) · body^0.8. Measured at C4
in 16:9 Ultra (mean luma of the note's column at +0.5 s / +4 s): v30 0.110 / 0.095, v70 0.167 / 0.145, v120 0.228 / 0.200,
the same numbers before and after repair round 1 (C2: 0.084 / 0.073, 0.130 / 0.107, 0.166 / 0.145).

### The pedal and the sound

`state.sounding` drives everything (guarded `?? null`; older hosts fall back to `pressed` + `pedal`, and the strike ring
`state.notes` still flashes a note shorter than a frame). The envelope is the concert grand's, number for number, so the two
answer a held pedal identically: flash, prompt decay (1.00 s at A0 → 0.45 s at C8), pitch-dependent aftersound (7.0 s →
1.2 s), then a velocity-scaled floor (33 % of the strike body at vel 1 → 50 % at vel 127) held for the whole sound, finger
or pedal. The wing stands up while its note sounds (`FOLD_UP` 0.05 s) and beats at a settling amplitude while the pedal
holds it; when the sound ends the light falls at `TAU_DAMP` 0.16 s inside a `DAMP_FADE` 0.30 s window that closes it to
exactly zero, and the wing folds to rest (`FOLD_DOWN` 0.10 s, about 0.3 s in all). A re-strike re-flashes from the level it
finds (fixture 6: eight repeats, eight re-flashes; every v90 re-strike lifts Eb4's column to 0.97 on screen, with about
1,700–1,800 px over 0.9 in the column on the strike frame, and it falls back to 0.53 between strikes; a re-strike's
re-flash crosses the bloom line by design, as any strike's flash may, and nothing sustained does). The pedal alone lights nothing: it opens the clasps on the body,
which is the frame showing the pedal. Measured (repair 1 lane): fixture 2's A0 column falls from 0.071 to 0.032 within
0.5 s of the pedal lift in 16:9 (0.113 to 0.029 in 9:16; E2 0.197 to 0.039); fixture 3's G4 damps after the lift (0.145 to
0.049) while C4/E4 keep their floor under the fingers (0.176 / 0.140 to 0.165 / 0.116).

### The material (harmony-feel)

- **Lushness** raises the membranes' thin-film iridescence (a hue ramp on the fresnel term, `uIrid`) and lets a **sand
  haze exhale from the thorax**: four noise-textured translucent quads (a 128² value-noise `DataTexture`, `RepeatWrapping`,
  soft radial edges), each breathing on its own, alpha capped at `HAZE_MAX` 0.3, rising over ~1.2 s and clearing over ~2 s.
- **Tension** tightens the wing-beat (breathing and ghost rate × (1 + 0.6·tension)) and cools the palette *around* the
  note colour: the spars lerp from sand-gold toward steel, the grazing edge and the haze toward cold blue. The note colour
  itself never changes.
- **Simplicity** stills everything: tremor and shimmer fade, clean chitin and bare spars.

### The dance (harmony-feel)

A hairline filament from the bass wing to the solo wing (attached half-way up each wing), two strands braided in the vertex
shader as a screen-space ribbon (~2 px at 1440p): the twist is 1.0 turn at rest, +4 turns easing in under **contrary
motion**, +1 with **pull**; the braid radius tightens with pull and the sag straightens with **stretch**; the colour follows
**consonance** (gold for an octave or fifth, indigo for a second or seventh). Its rotation rides harmony-feel's `phase`, so
every voice step turns it. Under a walking bass against a climbing melody it reads as a clear double helix.

### The moment (moment.js)

- **Intensity builds an artifact:** a cluster of 30 sand-glass shards grows between the wing roots of the held chord
  (`artifact.growth` staggers them in), in the chord's mixed colour pushed back toward saturation. On `artifact.released`
  they fly apart with `releaseStrength`, tumble, fall and fade over 1.4 s. Two clusters alternate, so the next chord can
  start building while the last one is still flying.
- **`mood.valence`** warms (sand) or cools (blue-grey) the haze.
- **Energy** scales the creature's breathing (a peristaltic vertex wave along the body, 0.04 → 0.26 units, 1.2 → 3.2 rad/s)
  and the stir of the dust above the wings.

### Craft

- Draw calls: **13**, fixed at 0, 1, 2, 5 and 10 sounding notes and on a strike frame (body, lenses, keybed, pistons,
  clasps, wing membranes, wing light, dust, haze, braid, artifact A, artifact B, pool); everything is `frustumCulled =
  false` and an idle part collapses in its vertex shader.
- No allocation in `update`: typed-array state, the sounding Map walked with `forEach`, cross-frame doubles in a
  `Float64Array`; the flash budget is a 7-wide window over the flash array, no allocation.
- **p95 at 16:9 Ultra with the 10-note pedalled chord: 4.3 ms** (p50 3.7) against the concert grand's **3.6 ms** (p50 3.0)
  and the bare page's 2.8 ms (p50 2.3), the three measured on the same lane within four minutes (repair 1, ports
  8983/9083); 9:16: 4.6 ms (p50 3.9) against the grand's 3.1 (2.7) and the page's 2.6 (2.1). The Ornithopter is the slower
  of the two, by 0.7 ms in 16:9 and 1.5 ms in 9:16, inside the 2 ms rule; the verifier's own same-lane pair (ports
  8985/9085) read 4.3 / 4.2 against the grand's 3.9 / 3.6. Free-running rAF p95 4.3 ms at 60 fps in both.
- Dispose to baseline: 11 geometries, 2 textures, 10 programs return exactly in the 16:9 A-burst (`toBaseline: true`); the
  +1 program the B-bursts show is the host's own (identical in the bare-page run), and the 9:16 A-burst's +1 geometry is
  unchanged from the first pass and the verifier's lane.
- Nothing downloaded; the noise texture is built in code. Keys stay ivory (`whiteColor 0xe9e3d6`); nothing gold sits
  behind them at rest.
- Known limits, measured on the stage above the keys: the pedalled glissando (44 strikes a second) puts up to 652 (16:9) /
  370 (9:16) pixels over the lane's 0.9 screen-luma line on most sampled frames of the run (50 of 72 in 16:9), all of them
  the flashes of just-struck wings, 0 near-white (before the repair 73 / 504 near-white). Fixture 4's staccato run shows
  497 (16:9) / 1,309 (9:16) px over 0.9 on the first strike frame only, a lone-strike flash, and 0 hot pixels on any frame
  more than 0.1 s after a strike, 0 white (before: 16 / 55 white). The 48 px that persist after 2.1 s in the 9:16 glissando
  are the host's ivory key tops inside the stage region, not the instrument. Where ten saturated hues overlap in a chromatic cluster the membranes read as a pastel (the
  per-channel max of ten colours), at most 0.85 linear per channel, so 0 white and no bloom, but the lane's screen-luma
  proxy counts about 1500 such pixels as hot at +0.5 s (screen luma 0.90–0.92, which is the 0.85 cap after the Neutral tone
  map). Outside the stage, the host's own key light on the lit ivory key tops reaches white for a few pixels under a
  fortissimo cluster (3–36 in 16:9, up to 207 in 9:16): the page's key rendering, not the instrument's light.
- Both framings composed: 16:9 shows the whole creature with the bass wings fanning into the frame; 9:16's follow camera
  fills the upper frame with the wings and keeps the keys readable.

### Tuning constants

`PEAK_EXP 1.35 · FLASH_EXP 2 · FLOOR_LO/HI 0.33/0.50 · AFTER_SHARE 0.55 · TAU_PROMPT 1.00→0.45 s · TAU_AFTER 7.0→1.2 s ·
TAU_FLASH 0.09 · TAU_DAMP 0.16 · DAMP_FADE 0.30 · TAU_VIB_OFF 0.07 · LIGHT_EXP 0.75 · SUS_GAIN 1.6 · FLASH_GAIN 1.8 ·
AMP_BASS/TREBLE 19/3° (AMP_POW 1.7, AMP_EXP 0.8) · VIB_HZ 2.2→6.0 (VIB_DEPTH 0.12) · GHOST_HZ 1.6→5.0 · FOLD_UP/DOWN
0.05/0.10 · FLINCH 0.4 (τ 0.16 s, 1.9 Hz) · HAZE_MAX 0.3 · WING lengths 30→10.5, chords 2.5→1.05, back 54°→43° (+7° hind),
rest sweep 11°/15° · PISTON k 1100, c 42, vSoft/vHard 44/78, rebound 0.32 · FLASH_REACH 1 · FLASH_SHARE 3.0 · FLASH_NEIGH
0.25 (repair 2) · KNUCKLE across 12 (key units), along 0.07, width 0.08 (wing units), gain 5.5 (repair 2) · sustained
channel cap 0.85 (repair 1).`

### Stills (lane, 16:9 and 9:16 Ultra)

`scratchpad/vandor-entries/light-vandor-ornithopter/out/repair1/orn/` (the six fixtures after repair 1),
`out/repair1/probe2/` (the clusters and the pair: `16x9/x7-cl60-strike.png`, `x9-pair-strike.png`) and
`out/repair1/probe2b/` (the v127 dyad, pair, triad and five-cluster, the 12 hues at v120). Earlier: `out/run2/` (first-pass
fixtures) and `out/probe2/` (lush chord, shatter, braid, ppp, ff10). Best: `repair1/orn/16x9/f2/f2-p0.15.png` (pedalled bass
chord), `16x9/f5/f5-half.png` (glissando fan), `9x16/f1/f1-C4-v120-p0.5.png` (one wing), `probe2/16x9/x1-lush3.png` (haze +
crystal), `probe2/16x9/x1-change+0.3.png` (the shatter), `probe2/16x9/x2-d1.45.png` (the braid).

## light-vandor-abyssal — Abyssal

**Module:** `arsenal/web/piano/instruments/light-vandor-abyssal.js` · **name:** Abyssal · **draw calls:** 6, fixed

### The idea

A bioluminescent deep-sea instrument on a blue-black stage. Above the keys hangs a school of seven jellyfish, one per
octave: the A0–B1 animal large and high, the C7–C8 one small and low, the school hanging at staggered depths so it reads
as a school and not a row. Every one of the 88 keys owns a translucent tentacle that falls from its bell's rim to a
photophore bead sitting just behind that key, so the piano is literally strung with living light — and it never stops
being a piano: each tentacle lands exactly on its key (the beads are placed at `keyX(m)`, 0.5 unit behind the key backs,
never over the keybed). The bells rest **dim** (the fix from the look-dev sketch, where they sat lit at full and a strike
had nothing to fight out of): a faint blue-grey water-glass with rim light, canals, a ring canal and rhopalia bulbs, so a
strike's flush of colour has contrast. The host's own keys stay readable in a cool ivory (`keyStyle` white 0xdde6ee).

### The strike

The bead behind the key sparks on the strike frame (the hammer: `F = v^2`, `TAU_FLASH` 0.09 s, a shock ring spreading
into the water over 0.3 s), the bell over it flinches in a swim stroke (`PUMP_CONTRACT` 0.14 × `v^1.4`, up in 45 ms,
relaxing over 0.3 s), and a pulse of light leaves the bell and races **down** the tentacle to the key: a bright head with
a short wake behind it, the sustained glow filling in behind the head so the light descends from the animal instead of
appearing at once. Velocity sets the pulse's brightness (`PULSE_GAIN` 2.4 × v²: a single v120 strike peaks just under the
bloom line in 16:9 and touches it only in the taller 9:16 framing or as a re-strike onto a lit tentacle; see Measured), its speed (`TRAVEL_PP` 0.40 s → `TRAVEL_FF` 0.13 s bell to key) and how many plankton it sheds
(`SPARKS_MIN` 3 + `SPARKS_VEL` 34 × v^1.5, born as the head passes them). Only the flash, the head and the bead's spark may
cross the bloom line; every sustained term is capped in its shader (0.57 linear, which is 0.85 on screen after Neutral
tone mapping) before the transient is added, so neighbouring tentacles can stack under the line.

### Velocity and the sustain (the envelope)

The tentacle's light runs the concert grand's envelope, number for number, so the three instruments answer a held pedal
identically: body at the strike `v^1.35`, a prompt decay (1.00 s at A0 → 0.45 s at C8) and a pitch-dependent aftersound
(7.0 s → 1.2 s), settling on a **velocity-scaled floor** (33 % of the body at vel 1 → 50 % at vel 127; 46 % at vel 96)
held for the whole sound, finger or pedal. On top of it the tentacle breathes: a slow sine (0.16–0.31 Hz, quickened by
`energy`) that is shallow (12 %) under a finger and deep (32 %) when only the pedal holds the sound, so a pedal-held
tentacle visibly "lets go" and breathes. v30 lights a body of 0.14 with a soft pulse and 4–5 sparkles; v70 0.45; v120 0.93.

### The pedal

Everything lives exactly as long as `state.sounding` (guarded `?? null`, falling back to `pressed` + `pedal`, with the
top 20 damperless notes ringing on). A note held only by the pedal keeps its floor with no time limit; a pedal-up release
damps with `TAU_DAMP` 0.16 s inside a `DAMP_FADE` 0.30 s smoothstep window (a fade whose steepest 60 fps step is 11 % of
the level at release, landing at exactly 0 with zero slope), the blur dies faster (`TAU_VIB_OFF` 0.07 s) and the note's
sparkles die with it (each plankton reads its note's damper window from the note texture). The pedal alone never lights an
unstruck tentacle or a bell; it only relaxes the bells open by 5 %. A re-strike sends a new pulse from the level it finds
(the carry folds any light above the new peak into the prompt term, so the light never dips to dark first).

### Low notes (the Dune wing)

Bass tentacles are thick (`CORE_BASS` 0.13 units → `CORE_TREBLE` 0.018) and sway; while they sound they vibrate as a wide
translucent motion blur: the ribbon widens to the swing envelope (`ENV_BASS` 1.05 units at A0 → `ENV_TREBLE` 0.03 at C8,
geometric in pitch, × body^0.8 so it narrows as the note settles and never stops while it sounds), filled with the
time-averaged arcsine density of a sine swing (brightest at the turning points) and **three phase-offset ghost strands**
sweeping inside it at `GHOST_HZ` 2.2 Hz in the bass → 7.5 Hz at the top. Light is conserved (a wider blur is a dimmer one),
so a bass blur never stacks toward white and nothing strobes at 60 fps. Treble tentacles are sub-pixel filaments drawn
with a pixel floor that dims rather than thins, with a fast shimmer.

### The material (harmony-feel)

- **Lushness** thickens a marine snow: 1400 motes drifting through the water column behind the keys in a cheap curl field
  (no texture, no CPU), each with a rank, shown when `rank < snow`; `snow` rises from `SNOW_MIN` 0.05 toward
  `0.05 + 1.15·lushness·(1 − 0.35·simplicity) + 0.1·density`, in over 1.4 s, out over 2.6 s (fog lingers). The motes are
  lit by the bells' tints and the artifact.
- **Tension** quickens the bells' breathing (`BREATH_HZ` 0.22 + 0.35·energy + 0.5·tension) and darkens the water toward
  indigo (the water column's tint × (1 − 0.45·tension)).
- **Simplicity** clears the water (the snow's term) and stills the bells (breath amplitude × (1 − 0.6·simplicity)).

### The dance

A current runs between the bass tentacle and the solo (melody) tentacle, from mid-height to mid-height: two strands
braided round the line between them. The braid twists faster in contrary motion (`twist` 1.5 + 7·braid, braid 1.0 for
contrary, 0.45 oblique, 0.25 similar/parallel, 0.12 static), sags as the voices spread (`f.dance.stretch`) and tightens as
they pull together (`f.dance.pull`), the strands' radius 0.16 + 0.5·stretch; light flows along it from bass to solo
(3.5 + 4·pull + 2·energy units/s), and `f.dance.phase` turns it. Its colour follows the consonance of the interval:
sea-green (0.42, 0.92, 0.82) when sweet, hot magenta (0.95, 0.22, 0.6) when sour. A voice change dips it to 35 % and
regrows it, so a jump reads as the old current dying and a new one born. Each strand is capped at luma 0.4 so a crossing
never reaches the bloom line.

### The moment

- **The artifact:** `m.intensity` inflates a luminous mass inside the bell over the chord's root register (`bellOf(f.voices.bass)`):
  `art = growth · (0.55 + 0.45·intensity)`, a lobed core (3–6 lobes and a phase from `artifact.seed`, so every chord's
  artifact is its own shape) that pulses slowly, widens the bell by 20 % and raises its dome by 10 % at full `art`, lifts
  it 0.4 unit and lights the marine snow around it. Its colour is the root bell's chord colour, warmed as the intensity
  climbs, luma capped at `0.7 · (0.4 + 0.6 · art)`: 0.28 as it starts, 0.7 fully grown.
- **The release:** on `artifact.released` the mass bursts into a cloud of plankton from the bell's centre
  (50 + 190·releaseStrength motes at `(3 + 6·rand) · (0.5 + 0.5·releaseStrength)` units/s, so 1.5–9 units/s, living
  1.8–4.2 s) and the bell strokes hard.
- **mood.valence** shifts the water's hue: teal when bright, violet when dark; **energy** drives the bells' breathing rate
  and the snow's drift.

### Tuning constants

`PEAK_EXP 1.35 · FLASH_EXP 2 · FLOOR 0.33→0.50 · AFTER_SHARE 0.55 · TAU_PROMPT 1.00→0.45 s · TAU_AFTER 7.0→1.2 s ·
TAU_FLASH 0.09 · TAU_DAMP 0.16 · DAMP_FADE 0.30 · TAU_VIB_OFF 0.07 · ENV 1.05→0.03 units (^0.8) · GHOST_HZ 2.2→7.5 ·
TRAVEL 0.40→0.13 s · PULSE_GAIN 2.4 · CONTACT_GAIN 2.3 · SUS_GAIN 0.78 · SPARKS 3 + 34·v^1.5 · BELL_SUS_CAP 0.16 ·
BELL_FLASH_CAP 0.9 · BREATH_HZ 0.22 · PUMP_CONTRACT 0.14 (45 ms up, 0.3 s down) · CORE 0.13→0.018 · SWAY 0.5→0.05 ·
SNOW_MIN 0.05 (in 1.4 s, out 2.6 s) · FLOOR_Y −8`. All of them sit in `ABYSSAL` at the top of the module.

### Craft and performance

Six draw calls, fixed: one instanced ribbon (88 tentacles + 35 oral arms + 2 dance strands, 56 segments), the seven bells
(one hand-built lathe, instanced), the 88 beads (instanced quads), one `Points` (1400 snow + 2800 plankton ring), the water
column and the sea-bed pool. One shared uniform block; every per-note number lives in typed arrays and one 88 × 6 float
texture; the `harmony-feel` and `moment` helpers refresh one object each in place; `state.sounding` is walked with
`forEach`; nothing is allocated in `update()`. Nothing is downloaded and nothing of the host's is written. `dispose()`
returns the 6 geometries, 6 materials and 1 texture.

### Measured (lane harness, Chrome 152 headless, RX 9070 XT, three r186, Ultra, both framings; pass v4 and, after repair round 1, the same fixtures re-run on the same ports 8984/9084)

- **Dark frames (repair round 1):** the verifier found about one frame in 150–300 coming back partly black while the
  Abyssal was mounted (a vertical cut or a rectangle in the composer's output; zero on the bare page and the concert
  grand), and traced it to the bell fragment shader's high-exponent `pow()` terms. `pow` is undefined for a base a rounding
  error under zero (`1 − |n·v|`, `0.5 + 0.5·cos`), and one NaN pixel spreads through the host's bloom mips into a black
  rectangle. The bell's four terms are now products and `exp` of a bounded argument (`fres³·(0.8 + 0.2·fres)`,
  `fres·(0.5 + 0.5·fres)`, `exp(−90·(1 − |cos 2φ|))`, `exp(−7·(1 − cos 24φ))`), its fresnel base is clamped, every
  `pow(x, 2.0)` is a product, and every other shader `pow` goes through `ppow` (base floored at 1e-4). Hunt (the
  verifier's probe: pedalled 10-note chord, 16 rows of the drawing buffer read back after every stepped frame, dark = mean
  under half the median): **0 dark of 1500 twice in 16:9 and 0 of 1500 in 9:16** (before: 5 of 1500, 7 of 3000).
- **Draw calls:** 6, fixed (the page's total is 113 at rest, in a chord and on a strike frame in 16:9; 73 / 85 in 9:16 where
  the page's own key-glow frames come and go).
- **Frame time, 10-note pedalled chord, 16:9 Ultra:** stepped p95 2.9 ms (p50 2.4); 9:16 p95 2.8 ms (p50 2.2) (repair-1
  lane; the first pass read 2.8 / 2.7). The honest pair is the verifier's, measured on one lane within the hour: concert
  grand p95 3.7 ms (16:9) / 3.6 (9:16) against the Abyssal's 3.1 / 2.9; on the Ornithopter's lane this afternoon the grand
  read 3.6 / 3.1. The Abyssal is the faster of the two by about 0.6 ms, not the 3.5 ms the first pass implied: the 6.3 ms
  quoted for the grand was lane 1's number from earlier in the night, not a same-lane measurement.
- **Dispose:** geometries 0, textures 0, programs +1 in the same bursts where the bare page also leaves +1 (the page's own);
  the 9:16 fixture-1 burst shows +1 geometry, the same as the Ornithopter's on its lane, not seen in 16:9.
- **Bloom and white:** sustained light stays under 0.9 on screen in fixtures 2 and 3 (hot pixels only on the strike frame);
  0 near-white pixels in the 10-note chord, the pedalled bass chord, the C major lift and the fast repeats; the 88-note pedalled glissando shows one near-white pixel for one frame (t 2.05 s, 16:9), at the keyboard's far right where
  the host's own rail highlight sits under the C8 bead's spark; a five-semitone cluster at v110 (`aby-extra/tense`) stacks
  at most 31 hot pixels in 16:9 and 33 in 9:16 after its 0.17 s strike window, where its five ribbons overlap (both left
  as known edges).
- **Velocity:** fixture 1 mean luma in the note's column at +0.5 s, 16:9: A0 v30 0.035 / v70 0.041 / v120 0.063; C4 0.085 /
  0.100 / 0.119; a v30 note reads (a lit body and a soft pulse). The v120 strike's column peak sits just **under** the
  bloom line in 16:9 (A0 0.835, C2 0.897, C4 0.895, C6 0.882, C8 0.865; no hot pixel on the strike frame) and crosses it
  only in the taller 9:16 framing at C2, C4 and C6 (0.918 / 0.911 / 0.905, 28 / 11 / 1 hot pixels; C8 0.893); a re-strike
  onto a lit tentacle crosses in both (fixture 6: eight of eight at 0.94). The same numbers on the verifier's lane and on
  the repair-1 re-run; the first pass wrongly said the v120 flash crosses at C2, C4, C6 and C8.
- **Sustain:** a pedalled A0 E1 A1 C#2 E2 keeps its column mean for the whole 8 s (0.051 → 0.049 at A0, 16:9), then falls
  within 0.3 s of the pedal lift; the C major's G4 damps within 0.35 s of the lift while the fingered C4 and E4 stay lit;
  eight Eb4 repeats in 2 s each peak at 0.94–0.95.
- **Stills:** `out/v4/16x9/f2/f2-p2.png` (the pedalled bass chord: wide violet wing blurs), `f1/f1-C4-v120-strike.png`,
  `f5/f5-top.png` (the glissando: 88 tentacles each in its own colour), `v4-extra/16x9/lush-p4.4-artifact.png` and
  `lush-p5-burst.png` (the artifact and its release), `dance-p1.7.png` (the braid in contrary motion), 9:16 `f2/f2-p2.png`.
