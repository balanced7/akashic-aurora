# Arbor: three-dimensional chord study

Open `piano-chord-tree.html` from the same server as the Crystal Studies gallery. This is a separate interactive chord builder; it is not connected to MIDI or the live piano yet.

## Visual grammar

- A connected trunk and its labelled primary limbs form one chord family. The twelve root pitch classes each have one persistent hue, arranged in fifths around the hue wheel. Changing the root recolors the whole tree.
- Interval roles progress through lighter shades of the same hue: root, third or suspension, fifth, seventh, ninth, eleventh, thirteenth. Labels and the tone buttons retain the exact note and interval, so color is not the only way to read it.
- Major opens outward; minor curves inward. Suspended seconds and fourths replace the third and use a forked tip with paired rings. Diminished contracts the crown and facets the lowered fifth; augmented stretches the raised fifth. A raised eleventh has a spiral tip.
- Leaves and smaller twigs are ornament, not additional notes. A tone button highlights its primary limb. Orbiting reveals the depth; labels that overlap or fall outside the view are hidden while the tone list stays accessible.

## Controls and rendering

The root picker, foundation and seventh selectors, extension switches, and raised-eleventh control build an explicit chord. The shared `spell.js` interval speller preserves musical spelling, including double accidentals. Duplicate pitch classes are represented once: for example, sus4 already supplies the pitch of a natural eleventh. Names distinguish a full eleventh from an added eleventh without a ninth.

`Pause orbit` stops camera motion. `Pause render` cancels animation frames and GPU scene submissions entirely, preserves the view, and cancels an in-progress measurement. `Resume render` continues without a time jump. Chord edits made while paused appear on resume. Hidden tabs skip drawing.

Native mode applies device pixel ratio exactly once to the scene's CSS dimensions. 4K uses a 3840 × 2160 drawing buffer with a fitted 16:9 image. Both use four-sample MSAA, SMAA, and restrained bloom. Branches interpolate ordinary position/normal goal attributes on the GPU; fixed instanced leaf buffers update during transitions. Shape changes reuse geometry and materials rather than accumulating meshes.

`Measure 10s` runs after a two-second warmup and records browser animation intervals, p95, maximum interval, CPU submission time, draw calls, geometry/texture counts, and adapter identity in the measurement output's `data-report`. It measures animation delivery, not physical display scanout. Changes to shape, camera, render size, visibility, or rendering state cancel the run. Run with other GPU-heavy applications idle; concurrent gaming substantially affected an early measurement.

URL state: `root=0..11`, `quality=major|minor|sus2|sus4|dim|aug`, `seventh=none|minor|major|dim`, `ext=9,11,13` (any subset), `sharp11=0|1`, and `resolution=native|4k`.

Focused checks: `node --test tests/piano_chord_tree.test.mjs tests/piano_crystal_performance.test.mjs tests/piano_solstice_signals.test.mjs`. Browser verification and measured results are recorded in `logs/chord-tree-3d-20260919/`.
