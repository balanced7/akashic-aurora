# Piano atmosphere

Open `/piano`, refresh the page, and use **Atmosphere**. Everything in the scene is
drawn into the existing piano canvas, so the environment is included in recordings.
The conversation panel, replay cue trails, MIDI input and practice log keep their
existing paths. The settings panel stays outside the recorded image.

## Moonwater, 15 September 2026

**Moonlit lake** and **Rainforest at midnight** now share a new environment. Water
reflects the actual keyboard, terrain, trees and note paths through a planar reflection
pass. The existing persistent ripple field distorts that reflection, bends the note
strands, and displaces fog and fireflies. Eighteen depth-tested fog samples occupy a
continuous noise field. Eight bounded note lights colour the water, mist and stone;
four physical lights illuminate the keys. The keyboard has a subtle mineral surface,
an optical-glass front edge with transmission and iridescence, and a fine metal inlay.

Quiet notes form slender, coloured reeds. Hard notes grow taller and wider, bend
further, and spread more light through their surroundings. A repeat retains the
part's phase, identity, position and spring height. Short high notes settle quickly
without pedal; pedalled notes remain suspended. Recently released neighbouring
pitches can continue the same visual part, while exact common tones take priority.
This is a bounded nearest-neighbour visualization heuristic, not a transcription of
the performer's intended counterpoint. A sustained old pitch remains a separate part.

The chord title uses light Segoe UI letterforms with smaller raised extensions. The
existing detector supplies its spelling, key and Nashville number, including the
numbers-only preference. Unclassified dense pitch sets are labelled by their note
count, without inventing a chord. Note letters have separate octave figures and
collision packing; fine leaders connect displaced labels to the moving parts.
**Harmony + staff** uses the original theory overlay. **Pure performance** hides the
title, note labels and submerged letterforms. The lake's twelve inlays follow the
circle of fifths; active pitches reveal a polygon, and the root gets a warm ring.

The other four environments retain their existing rendering. Weather overrides and
the real-input waveform work in both renderers. The old airborne particle simulation
is paused while Moonwater is shown, rather than running a hidden second effect.
Moonwater's reflection targets are 768, 1024 and 1536 square pixels for Studio, Ultra
and Cinema respectively; the main canvas retains the output sizes listed below.
The reflection is planar, fog is layered scattering, and glass uses screen-space
transmission. This is not a full 3D fluid solver or a path-traced scene. Output is SDR;
no new claim about smooth 4K recording is made by this pass.

New source: `web/piano/moonwater.js`, `web/piano/harmonic-voices.js` and
`tests/piano_harmonic_voices.test.mjs`. The small `ownsTheory()` hook in `web/piano.js`
allows the environment to own its heading without drawing both titles.

Fresh checks for this pass: both JavaScript gesture/voice test files passed, including
common tones, E-to-F continuation, repeat continuity, dry/pedalled release, phrase
gaps, backward seek, bounded capacity, fifths order and dense layout in both aspect
ratios. The model's matched velocity-119 chord reaches over 2.6 times the height of
velocity 38. The 117 Python conversation, replay and cue tests passed. Private browser
receipts under `state/arsenal/receipts/spectacle/moonwater-study/` cover soft/hard chords,
inner-voice movement, repeats, a twelve-note cluster, all six worlds, display modes,
classic restoration and 1080p/1440p/4K canvas sizes. Browser shader logs were clear.
These are local checks, not a full-repository ship result. No user service was restarted
and the fixture stores all test playing in its own private session roots.

The sections below describe the earlier multi-world renderer and its capture history;
the Moonwater-specific behavior above supersedes their lake/rain description.

## Playing the worlds

| Environment | Scene |
| --- | --- |
| Moonlit lake | Displaced water, distant ridges, layered aurora, moon and stars |
| Ember sanctuary | Warm lacquer, ember weather and amber light |
| Velvet nebula | Procedural spiral dust, stars and a distant planet |
| Winter mountains | Snow, frosted ridges and cool piano materials |
| Rainforest at midnight | Instanced pines, layered mist and rain |
| City of light | One tower per MIDI key, rising with velocity and settling on release |

Velocity changes launch speed, spread, light and chord impact. Notes above C5 released
within 240 ms scatter as short shards without pedal; with pedal they stay suspended.
Held gentle chords gather slower light and strengthen the aurora. Strong simultaneous
strikes create expanding floor rings and displace nearby particles and weather.
The pedal slows weather; lifting it releases the suspended notes.

Each key has a continuous emission phase and a spring carrying height, momentum and
light. Repeated strikes add momentum without rewinding that phase or existing particle
positions, ages and velocities. Individual motes are born throughout the phase with
different lifetimes, rather than replacing a whole puff. A separate bounded history
retains up to 256 recent strikes for gesture accounting; history overflow never resets
the GPU flow. The surface-wave gradient also pushes nearby motes and bends note paths.

Glass note markers carry the detector's spelling and octave. Their anchors follow the
same paths as the luminous strands, with pitch-ordered screen packing and fine leaders
to keep dense voicings readable; thin connections join adjacent audible voices and carry
travelling points of light. The golden-ratio phase offset distributes these accents;
it does not claim a Fibonacci relationship in the music. Note light scatters through
a stylized mist layer. City paths become straight, with angular connections; rainforest
paths recede into depth. Soft framing bounds reduce labels drifting out of the picture.

Quiet playing has a visible pearl-and-silk focus. Forceful playing creates faster,
wider sprays and taller ribbons, while the phrase's central form opens out. These
forms have different silhouettes: liquid loops at the lake, flame contours for ember,
precessing orbits in the nebula, facets in winter, hanging veils in rain and travelling
circuit shapes in the city. The central form is composed within the camera's portrait
or landscape framing. City towers retain spring momentum on a repeated key.

The water maintains a 256 x 256 height/velocity field at 120 simulation steps per
second, with additive note/chord impulses, wave propagation and damped boundaries.
Its moving surface and highlights retain earlier ripples through later strikes.
This is a surface-wave simulation; airborne particles follow a flowing force field.
The visual language, research sources and review criteria are in
[SPECTACLE-DESIGN.md](SPECTACLE-DESIGN.md).

Harmony can tint the scene after a chord settles. Minor colour, suspensions, close
intervals and a detected dominant-to-tonic movement affect different visual properties.
These are artistic mappings, not claims about the player's emotions or a definitive
analysis of harmonic function. **Travel with the music** optionally chooses worlds
after four seconds of a stable gesture, with at least fourteen seconds between moves.
Manual selection, weather overrides, intensity and motion remain available.

**Camera drift** adds a small orbit while retaining the keyboard in the composition.
It is not a free-flight navigation system. The default Harmony display shows chord,
Nashville numbers and note glass. Full adds the staff; Chord omits the Nashville row;
Pure performance hides the text. The glass Nashville plaque consumes the piano's
published `__piano.stats().nns/key/nnsMode` reading at 10 Hz; it performs no independent
key or number inference. Full retains the original theory overlay. An unset key is displayed as unknown rather than
inventing a Nashville degree. Turning off cinematic atmosphere restores
the original piano presentation.

Select a loopback device in the existing audio menu to draw its waveform. The effect
uses the actual time-domain analyser samples, and disappears when the input is
disconnected. It does not request an input automatically, generate substitute audio,
or feed the analyser back to the speakers.

## Quality and capture

| Setting | Landscape / portrait pixels | Simulated particles |
| --- | --- | ---: |
| Studio | 1920 x 1080 / 1080 x 1920 | 32,768 |
| Ultra (default) | 2560 x 1440 / 1440 x 2560 | 65,536 |
| Cinema | 3840 x 2160 / 2160 x 3840 | 131,072 |

Note particles use floating-point GPU ping-pong textures for position and velocity,
with drag, gravity, attraction, flow and impulse forces. Additional weather, stars,
instanced geometry and translucent ribbons use bounded allocations. The HDR composer
keeps four-sample antialiasing and bloom. Chord/staff canvas textures scale with output
size; the individual note atlas has 128-pixel cells and mipmaps. The present browser
output is SDR: the floating-point internal lighting does not constitute HDR10 or
wide-gamut HDR display output.
Cinematic rendering targets 60 fps to leave room for capture on high-refresh displays.
Quality changes are blocked while a recording is arming or running.

Browser recording chooses H.264 levels from the actual output size, and scales bitrate
with pixel count. On the tested Chromium/AMD path, requested H.264 5.2 was downgraded
to 5.1 and stalled at 4K. Cinema therefore prefers VP9 WebM; lower settings prefer MP4.
Earlier decoded short local tests on the RX 9070 XT produced about 54 fps at 1440p
H.264 and 21 fps at 4K VP9, both with picture and audio. In the current visual pass,
six-world live checks ran around 48 fps. Two consecutive 1440p H.264 captures exposed
a first-take loss: 52 of 166 requested frames (18.4 fps), then all 135 of 135 requested
frames (48.1 fps), both with audio. A fresh 4K VP9 capture produced an empty blob.
These capture limitations are not resolved by the visual pass. **4K rendering is available; smooth
4K60 browser recording has not been achieved. Ultra is the current capture default.**
Render-loop fps alone is not evidence of encoded video cadence.

## Implementation and verification

- `web/piano/spectacle-motion.js`: pure gesture and slow world-selection model.
- `web/piano/spectacle.js`: GPU simulation, luminous strands, weather, impact rings,
  harmonic constellation, controls and material transitions.
- `web/piano/spectacle-worlds.js`: procedural sky, terrain, water, trees, towers,
  stars, fog and actual-input waveform.
- `web/piano/spectacle-voicing.js`: shared paths, glass spelling atlas, adjacent-voice
  connections, packed labels, Nashville plaque and note-lit mist.
- `web/piano.js`: additive note/pedal/frame hooks, scaled render/overlay dimensions,
  recording quality guard and resolution-aware capture profiles.
- `tests/piano_spectacle.test.mjs`: velocity, staccato, pedal release, gentle sustain,
  cadence, repeated notes, bounded history and world-transition hysteresis.

The shaders are original code informed by the local aurora-ribbons preset, the
`design/vfx-sketches/daniil-curtains.frag` and `daniil-snowfield.frag` studies, and the
house highlight-control studies. External references were
[Three.js GPUComputationRenderer](https://threejs.org/docs/pages/GPUComputationRenderer.html)
and [Lusion](https://lusion.co/) for the direction of spatial visual storytelling.
No third-party shader bodies or image assets were copied into this module.

Verification receipts live privately under `state/arsenal/receipts/spectacle/`:
gesture tests; 558 focused theory/cue/replay/conversation/practice Python tests;
an isolated piano server and headless Chrome using the actual AMD GPU; six rendered
worlds; dry/wet staccato; actual analyser input; 4K and portrait dimensions; recording
guards; no MIDI feedback; all-off cleanup; and stable GPU texture/geometry counts
after repeated quality changes. Saved video is independently decoded with PyAV.
This is local work, not a full-repository ship claim. The user's running service
was not restarted, and no synthetic test performance entered its log.

The expression refinement adds private `continuity.cjs` / `continuity.json` and
`worlds-check.cjs` / `worlds-check.json` receipts. Matched velocity-38 and velocity-119
chords were rendered in both orientations. GPU readback samples a persistent pitch's
particle population and checks that living particles continue aging and moving after
the same key is struck again, with births spread across time. A right-hand
ripple retained the preceding left-hand wave; after silence the wave energy decayed
below 0.001 in the test's units. Repeated quality changes kept resource counts bounded.
The pure model tests also exercise history exhaustion, independent strike tails,
emission-phase continuity and spring consistency at 30 versus 120 updates per second.
Default-atmosphere pixel-exact replay from a held frame clock is not established:
an explicit simulation reset/seed seam is still needed for identical starting state.
Vandor's clean-Claude capture test currently disables atmosphere. A first-take recorder
warm-up loss was also reported by that separate jam test; its four-second warm-up is
a test accommodation, not a demonstrated production fix.

`voicing-ui.cjs` additionally checks the actual Harmony plaque (Am = 1m in a locked
A minor key), optional staff, text hiding, drawer exclusion and a twelve-note cluster.
The existing main chord header can still overflow in portrait for a fully chromatic
cluster; the individual glass notes are packed separately. Conversation and Cards
now share the right edge by closing the other drawer, without stopping band transport.
