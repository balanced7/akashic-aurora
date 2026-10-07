# Crystal studies

Open `/piano-crystal-studies.html` when serving `arsenal/web` (or `/web/piano-crystal-studies.html` with the Arsenal server). Query parameters: `study=aether|solstice|nocturne`, `resolution=native|4k|1440` and `canopy=ribbons|fan|halo|sails` (Solstice).

This is a standalone, playable look-development gallery. It reuses `instruments/glass-piano.js` for the 88-note mechanism and derives its rim geometry, materials and strings in `crystal-studies.js`. It does not replace the main visualizer or register saved looks.

- **Aether:** a lowered, tapered rim, a single swept crystal canopy, curved crystal runners, platinum action, and thin rear light arcs.
- **Solstice:** a scalloped rim, a choice of three overhead LED forms or the original opal sails, brass supports, resonator petals, and warm ambient light.
- **Nocturne:** a raised curved rim, two separate smoked-glass wings, titanium buttresses, and a translucent aurora behind the instrument.

Each study has 352 instanced soft fireflies. Surfaces are tessellated geometry and physically based materials, with no downloaded mesh or image texture for the new forms. The existing small soundboard grain texture remains part of the original instrument.

## Solstice overhead lights

The selector next to Solstice switches between layered ribbons (default), a curved radial fan, nested halo bands, and the original opal sails. A switch replaces only the overhead geometry, preserving the piano, camera and current notes. The selected form is saved in the URL and retained when switching away from Solstice and back.

The LED forms have three rows and twelve pitch positions. Columns represent C through B, combining octaves by maximum velocity. The front/lower ribbon responds to new attacks and fades quickly; the middle ribbon shows notes held by fingers; the back/upper ribbon shows notes that are sounding only because the pedal holds them. In the halo layout, the same rows run inner/lower to outer/higher; C begins at the front of each ring. A pitch can occupy both held and pedal rows if different octaves have different hold states.

A small live matrix explains the mapping. “Show how the lights respond” plays a nine-second silent example through the real performance state: strike C/E/G, hold, release fingers under pedal, add D/A, release pedal and fingers. Manual keyboard/MIDI input takes over from this demonstration. The form picker keeps the demonstration running so forms can be compared under the same notes.

LED color moves gently inside active pitch segments. Reduced motion stops color travel while retaining meaningful note-state illumination. Rounded brass housings, solid opal diffuser geometry and HDR emission provide the glow without image sprites or one point light per LED. Only 36 energy values and one phase uniform update per frame. Canopy geometry is disposed on each form switch; the material and light state persist.

The demo is silent. Use Connect MIDI for a live keyboard, or A–K/WETYU and Space for computer-keyboard notes/sustain. MIDI access is requested only after clicking the button. A disconnected device and window focus loss clear held manual notes. Ornament motion respects reduced-motion preferences; the playable key/hammer/damper mechanism remains responsive.

Native mode allocates one drawing-buffer pixel per device pixel. The fixed 4K setting is exactly 3840 × 2160, with a 16:9 image fitted inside the available space. Antialiasing combines a 4-sample half-float scene target, derivative-aware string edges and SMAA before OutputPass (Three.js r186). A checkbox allows an honest AA-off comparison. No timer caps the animation to 60 Hz.

Studio controls include a 15-second frame-interval measurement after 3 seconds of warmup. Changing study, camera, resolution, performance, AA, motion or visibility cancels an in-progress sample. `p95Ms` includes long frames; simulation-delta clamping does not hide them. The result measures browser animation delivery, not physical scanout. CPU time is command submission time, not a GPU timer.

Verification: `node --test tests/piano_*.test.mjs` (expand the glob in PowerShell) and visible browser review of all three studies, fixed 4K, native sizing, switching and close-up mode. Hardware MIDI needs a connected keyboard for an end-to-end proof; state semantics have automated tests in `tests/piano_crystal_performance.test.mjs`.
