# Live harmony modes

Build acceptance, recorded before implementation (Asta, 2026-09-15):

- Eight original modes inside the real piano canvas: Tonnetz, Chromatic folds,
  Spiral harmony, Stained glass, Flowing rings, Blooming petals, Interval threads,
  Harmonic compass. The reference list's fifth family contains three modes.
- One shared live/pedal/replay input and one existing chord/Nashville reading.
  No new MIDI connection, audio output, or independent chord naming.
- Mode changes preserve held notes and visual voice identities. Repeated strikes
  add energy and travelling pulses without restarting a part. Pedal preserves
  released notes; silence and backward seek clear stale visual state.
- The new mode replaces foreground note effects, retaining the chosen environment.
  Original atmosphere remains selectable. Labels/off/full and numbers-only work.
- Pitch-class geometry is paired with an octave-aware voicing rail and key leaders.
  Eighty-eight voices are bounded; dense labels summarize rather than overlap.
- Browser review: all modes with held and changing chords, soft/hard/repeat, pedal,
  silence, portrait/landscape, mode switching, and clean shader logs. Use a private
  fixture with isolated performance roots; do not restart user services.
- Pure-model tests: Tonnetz adjacency and triad topology, enharmonic vertical
  separation, fifths spiral, finite non-overlapping weighted cells, common-tone
  identity, repeated attacks, pedal release, bounded pulses and seek reset.

These are adaptations of visual ideas, not copies of the referenced software,
their detection algorithms, assets or source. Sources:

- https://cifkao.github.io/tonnetz-viz/
- https://ztonnetz.com/
- https://alexandrefrancois.org/MuSA_RT/
- https://www.musanim.com/Voronoi/
- https://www.musanim.com/Renderers/
- https://isotonikstudios.com/product/tritonet/

The risky seam is ownership of the recorded foreground: drawing two note layers
or two headings defeats clarity. Verification must inspect the actual canvas,
not just mode names in a select element. Geometry is an explanation of harmony;
it must not claim an inferred voice assignment or tonal centre is ground truth.

## Using the modes

Open or refresh `http://127.0.0.1:8793/piano`, then choose **Atmosphere → Chord
visualization**. Tonnetz is the initial choice when no mode has been saved.
The eight modes and Original atmosphere can be changed while notes or pedal
remain held. The selection is saved with the existing atmosphere preferences.

The diagram uses pitch classes; the strip above the keyboard preserves octaves,
continuous voice identity and leaders to the actual keys. The strip smoothly
adapts to the played range. More than 24 simultaneous voices retain all dots
but omit crowded individual strip labels. Pitch-class views still name their
nodes; rings/petals/threads omit crowded floating labels above 18 voices.

Chord + Nashville is the normal performance view. Pure performance hides text.
Harmony + staff gives the centre to the existing staff instead of drawing a
diagram behind the notation; switching back restores the selected diagram and
the same held voices. The existing numbers-only and key-lock controls apply.

These are original, playable adaptations, not complete ports of MuSA_RT,
Z-Tonnetz or Tritonet. In particular, the spiral's centre is the weighted centre
of sounding pitch classes, not a new key detector. Folds separate accidentals
from natural-note sites. Part matching is a bounded nearest-neighbour visual
heuristic, not an analysis of the pianist's intended counterpoint.

## Local verification (2026-09-15)

- Three Node test programs pass: harmony modes, harmonic voices, spectacle
  gestures. They cover triad topology, fifths, weighted cell boundaries,
  continuous/repeated voices, pedal, capacity and backward seek.
- 117 focused Python tests pass across conversation, replay and pianocue.
- Private MIDI fixture, separate performance/takes/jam roots and fake MIDI
  access: `state/arsenal/receipts/spectacle/harmony-study.py`.
- Fifteen browser assertions passed through the real piano MIDI handler:
  repeated identity/birth, added repeat energy, stronger hard strikes, E→F
  continuity, six pedal-held notes, all nine mode changes preserving identity,
  and complete retirement after release. Receipt:
  `state/arsenal/receipts/spectacle/harmony-study/frame-1789452613953-4.json`.
- Actual canvas captures for all eight modes in both 9:16 and 16:9. Final
  landscape capture series starts `frame-1789452738651-1`; portrait series
  starts `frame-1789452759602-9` in the same receipt directory. Images include
  the new foreground inside the piano's recording canvas.
- Real UI selector exercised. Live service 8793 serves all new module assets
  with HTTP 200; no user service restart. Port 8796's replay service does not
  serve `/web/piano/spectacle.js`; this feature belongs to the realtime piano.
- All eight modes also rendered a 36-note chromatic voicing without JavaScript
  or shader errors; dense capture series starts `frame-1789452939017-3`.
  Numbers-only, staff, and pure-performance displays were checked on canvas.

The browser review caught and corrected the piano's off-centre camera
projection, text entering water reflections, texture storage on aspect resize,
and staff/diagram overlap. User MIDI hardware and sustained 4K recording
throughput were not measured. This is a local integration, not a repository-wide
ship or an independent visual-quality review.
