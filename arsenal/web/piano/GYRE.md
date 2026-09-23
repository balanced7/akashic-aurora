# Gyre

For future visual work, read the [visual quality baseline](../../VISUAL-QUALITY-BASELINE.md).
It preserves the design approach, review criteria, evidence limits and
[five reference recipes](../../visual-references/2026-09-21/gyre-recipes.json)
from the 2026-09-21 session.

Open `/piano-gyre.html` on the local studies server. A standalone light sculpture with seven starting studies, a browser preset library and optional MIDI-driven shaping. It does not produce sound or listen to audio.

Axial spin aligns the long stem with local Y: spinning leaves the stem on its axis while the bent end circles it. The complete axis tilts with sinusoidal nutation and precesses around world up. The JavaScript arm and GLSL light paths share the same rotation order: spin Y, tilt Z, precession Y. Optional Planar sweep retains the original arm in the XZ plane, rotating perpendicular to its plane. The motion selection persists across presets and in the URL (`motion=axial` or `motion=sweep`); axial is the default. This is designed motion, not a torque / inertia / string-tension simulation.

Silk uses camera-facing strips whose centerlines are world-space paths; Beads uses round point sprites without drift; Sparks adds age-dependent drift. Pulse and color are evaluated at each sample's emission time so the historical paths don't blink together. Motion and pulse sliders clear the current exposure; presets, style changes, and edits while paused preview a complete exposure of the new settings. Nothing is recorded to disk.

Stem length and Bent arm length independently reshape the L. CPU emitters, the visible rods and the GPU path use the same dimensions; the camera's minimum distance grows with the arm. Tail finish offers the original fade, a flicker limited to older samples, and a dissolve with a glowing edge and gentle breakup. Tail character and Tail flicker rate control these effects. Geometry buffers are reused.

Tidal braid follows three toroidal strands; Weave depth opens them and Petals / winding changes the weave. Pendulum garden draws nested rosettes with fine suspension lines. Both use the same CPU and GPU parametric equations for light heads and histories. These are designed kinetic paths, not simulated forces. Radial reach controls their size; L-specific controls disable when irrelevant.

Solar wind attaches the camera rigidly near the final L leg, looking back into the wake. Its transformed up vector keeps the leg fixed in the view during spin, tilt and precession. Outside view and Leave ride restore an orbitable view. Wind pull advects older trail samples backward; turbulence adds smooth transverse flutter. Displacement is exactly zero at a live emitter. Ribbon extrusion fades near the camera plane. All views retain true pause and native/4K rendering.

Let harmony shape the light offers four explicitly silent chord previews and an explicit Connect MIDI button. Fuller note sets and wider voicings open the braid/flowers, close pitch intervals add winding/turbulence, and pitch content shifts colour. The current exposure morphs gradually with frame-rate-independent exponential smoothing; it is not a historical recording of harmonic changes. Live labels list sounding pitch names rather than asserting an ambiguous chord root. Each MIDI channel owns its sustain latch, and input changes/disconnect/all-notes-off release the relevant state. Hardware MIDI requires browser permission and a selected input. No MIDI or audio permission is requested on load.

Save preset opens an inline name form. The browser library stores every sculpture control plus resolution, suspended-arm visibility, camera position/target, camera orbit and animation phase. Choosing a saved preset restores it; Update selected explicitly replaces that version. Saving another name creates a separate version. Presets use localStorage on the current origin, not a server or account; clearing site data removes them, and ports 8793 and 8799 have separate libraries. Failed storage reads/writes surface an error and do not replace the library. Sculpture settings also remain in the URL across refreshes; camera and arm visibility are restored by selecting a named preset.

World, viewpoint, wind and harmonic-response settings are additive fields in the version-1 library. Old records load as the original L, outside camera, no wind and no harmonic response. Reading does not write or migrate storage bytes. New saves include the new controls; transient sounding notes and device permissions are not stored. Rider presets store the outside camera separately so leaving the ride restores a useful view.

Geometry is allocated once for at most 40 emitters: 1,536 segments per ribbon, 1,101 points per bead/spark path. Controls change draw ranges and uniforms. There is no full-screen bloom pass. Native uses CSS size times device pixel ratio; 4K fit scales the scene into a 3840 × 2160 envelope while preserving its aspect. The browser's actual MSAA sample count is included in the benchmark output.

Three additional ray materials are in `gyre-light-rays.mjs`. **Filigree** entwines
three spatial filaments around each historical light path, with independent colour
and glints. Their spread grows from zero at the emitter. **Prism** folds a soft
ribbon profile with coloured edges and fine internal bands. **Fireflies** emits
small lights at fixed timestamps and gives them gently drifting, elongated tails.
The firefly positions use emission time rather than rebuilding a regularly spaced
age lattice every frame, so each light remains coherent as it ages and disappears.
All three use the existing motion, palette, pulse, wind and tail-finish functions.

Ray spread changes the width of these new materials; it is disabled for the original
three. Radiance changes both trail and light-head brightness, defaulting to the
original energy. Deep black backdrop removes the background gradient and floor halo
for a black stage; it does not change display HDR settings. These controls are in
the URL and saved presets. Version-1 records missing them receive spread .55,
radiance 1, and the original backdrop, without rewriting the library.

The added buffers are fixed: three 1,024-segment filaments and 160 firefly quads per
emitter. Prism reuses the original ribbon geometry. Only the selected material is
drawn; repeated switching does not allocate new geometry. The material render review
and performance receipt are in `logs/gyre-rays-20260921/results.md`.

**Fly the rays** adds an optional formation of 5, 9 or 13 original lightcraft.
Choose a ray, then watch from Outside, follow the leader with Squadron chase, or
fly from the rear wing with Squadron pilot. Sideways spread, forward spacing and
vertical separation are independent; Break & regroup opens and reunites the wings.
Ballet unfolds through arrowhead, fan, helix and single file on a 40-second cycle.
Individual formations can also be held. Flight speed and camera banking are separate
from the sculpture's motion.

`gyre-flight-motion.mjs` is the renderer-independent route and formation layer.
The route samples an actual emitter history, including wind, dissolve and the
Sparks/Fireflies drift fields. Filigree strands surround the shared centreline;
Fireflies remain discrete particles. A tangent-matched return curve closes the open
history so successive laps do not teleport. This return is an artistic connector,
not part of the recorded ray. Arc-length lookup spaces the craft along the curve;
transported frames and seam correction keep orientation continuous around the lap.
Completely stationary paths remain finite and suspend flight progression.

`gyre-flight.js` owns the scene adapter: instanced faceted craft, soft engine cores,
twin wakes with a fixed 96-sample history per engine, and damped chase/pilot cameras.
The wake records actual world-space flight positions at up to 45 samples/second.
Its buffers and craft geometry are reused. The camera follows the evolving rail;
this is authored choreography, not inertial physics or collision avoidance. Large
manual changes reshape the route and clear the old wakes. Flight controls and lap
distance/choreography time and transported orientation persist in named presets. Old presets default to flight
off; loading a flight preset restores its outside camera before attaching the flight
camera, so Outside view still returns to the saved composition.

Flight checks and browser/performance evidence: `tests/gyre_flight.test.mjs` and
`logs/gyre-flight-20260922/results.md`.

Pause render cancels animation scheduling. The still sculpture can be inspected or adjusted while paused; no frames are drawn without an explicit control/camera/resize interaction. Hidden tabs suspend animation, and reduced-motion preference starts paused. Playback time resumes without jumping across a pause. The performance meter measures delivered animation-frame intervals, not physical display scanout or GPU execution time. Changes of settings, dimensions, visibility, or camera interaction cancel a pending measurement.

Checks: `node --test tests/gyre_motion.test.mjs tests/gyre_presets.test.mjs tests/gyre_harmony.test.mjs` validates radial invariants, adjustable-arm endpoints, rider rigidity, wind head anchoring, bounded new paths, preset compatibility, storage-failure preservation, harmonic targets and MIDI sustain/disconnect handling. Original browser evidence is in `logs/gyre-20260921/results.md`; tail/preset/main-studio integration evidence is in `logs/piano-workbench-20260921/results.md`; new-world evidence is in `logs/gyre-worlds-20260921/results.md`.
