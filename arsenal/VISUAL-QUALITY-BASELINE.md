# Visual quality baseline

Established 2026-09-21 from the crystal piano studies, studio integration and Gyre.
Daniel's direction: "It would be incredible if this fidelity, quality, beauty and elegance could become our baseline!"

Use this before designing or changing Arsenal visuals. It records reusable practice and reference work; each new implementation still needs fresh visual and performance evidence. Extend the existing [spectacle design](SPECTACLE-DESIGN.md), including its quiet/loud musical grammar. These principles transfer across palettes, subjects and styles.

## The standard we are keeping

| Quality | Design requirement | Review in the actual render |
| --- | --- | --- |
| Fidelity | Resolve fine edges, material detail and silhouettes at the intended display size. Allocate detail where the camera can approach. | Inspect thin arcs, close-up rods/LEDs, diagonal edges and moving highlights at actual native resolution. Check shimmer as well as still-image aliasing. |
| Beauty | Compose a clear focal form, a deliberate palette and enough negative space for the shape to read. Light should reveal form and depth. | Examine several phases, distant and close views, quiet and energetic states. Dense passages should retain colour and structure. |
| Fluidity | Layer distinct timescales: immediate source motion, slower overall movement and lingering history. Response should remain continuous. | Watch sustained motion, state transitions, release and resume. Look for phase jumps, accidental synchronized blinking and periodic stalls. |
| Elegance | Give a small set of understandable controls expressive range. Group controls around motion, form and afterimage. | A single adjustment should have a legible effect. Presets should offer distinct compositions and make discoveries recoverable. |
| Performance | Target native display pixels and sustained 60 fps minimum; pursue the display refresh rate where measured hardware permits. | Report actual drawing-buffer dimensions and frame-time distribution. Never silently lower resolution to earn an FPS claim. |
| Trust | Preserve authored settings, camera state and working input/capture paths. Make saving and replacement explicit. | Check preset round trips, legacy records, failures, pause, switching and existing integrations relevant to the change. |

Beauty remains an authored judgment. Numeric image metrics can diagnose clipping, contrast or colour changes; they cannot certify an evocative composition. Show the render alongside the numbers.

## Approaches worth repeating

1. **Start with a concrete motion idea.** Daniel's suspended spinning LED arm gave Gyre a coherent source, axis and history. Sketch the hierarchy first: axial spin, tilted axis, whole-axis precession and wobble. The corrected axial model leaves the long stem on its own axis while the bent leg circles it. Verify a simple geometric invariant before elaborating the effect.

2. **Separate fast motion from slow structural change.** The latest violet preset combines 0.18 rev/s spin with 0.008 rev/s precession and 10.2 seconds of history. That leaves roughly 1.84 spin turns but only 0.082 precession turns in the exposure. The broad form remains legible while internal loops weave. This is a useful relationship to explore, not a universal formula for beauty. Tune speed, history, dimensions and camera together.

3. **Make the light's history spatially coherent.** Gyre evaluates world-space paths at emission time; pulse and colour belong to each historical sample. Camera orbit must reveal the same sculpture from another angle. Flicker and breakup concentrate toward older samples, preserving readable live tips. In continuous live note effects, a new strike should add energy without erasing its predecessors; explicit design-control changes may deliberately preview a fresh exposure.

4. **Keep every representation in agreement.** Visible mechanism, CPU light heads and GPU trail paths share dimensions and rotation order. They currently implement matching equations in separate languages; invariant tests and browser renders guard drift. The rider camera transforms position, target and up together. Wind displacement is zero at the emitter and grows with trail age.

5. **Spend rendering effort where it is visible.** Reuse allocated buffers and update uniforms/draw ranges; instance repeated lights. Use suitable edge antialiasing and soft local light profiles. Gyre achieves its look without a full-screen bloom pass. Other scenes may justify bloom or richer materials: measure their cost and preserve silhouette and colour. More blur, brightness or particles is not evidence of more detail.

6. **Give variants different forms.** Aether, Solstice and Nocturne explore instrument shape, material and illumination; Gyre, braid and pendulum explore different path families. A palette swap alone does not fulfill a request for a new silhouette or motion identity. Build a small number of strong variants and inspect each.

7. **Treat controls as part of the instrument.** Name effects in terms people can see; expose independent dimensions and meaningful ranges. Provide attractive starting points, immediate feedback, discoverable reset and true pause. Make irrelevant controls visibly unavailable. Save camera, phase and appearance when those contribute to the composition; explain what a URL does not preserve.

8. **Protect exploration.** Inspect the user's current settings before testing, use a separate preview, and restore temporary viewport changes. Load and update are different actions. Validate the complete preset before applying it; failed reads/writes must retain the library and report failure. Version fields additively and verify older records without silently rewriting them.

9. **Integrate with existing ownership.** The studio work moves existing controls and retains their handlers, instrument lifecycle, note/sustain state and capture pipeline. Avoid duplicate render loops and competing camera owners. Keep settings and decorative UI out of the recorded canvas unless they are intended content.

10. **Let inspection change the design.** Initial pale ribbons and undersized sparks were refined after rendering; the axial interpretation was corrected after Daniel's feedback; close-up geometry was refined for the rider view. A compiled shader or passing unit test is one piece of evidence. Iterate on actual shape, colour, motion and usability.

## Reference recipes and authorship

[Five reference recipes](visual-references/2026-09-21/gyre-recipes.json) preserve known control values and launch URLs outside browser storage.

- **Golden wings / Long flowing lines medium:** warm layered arcs; 0.54 spin, -0.066 precession, 6.2-second history, beads, Ember, 3.25 stem / 2.5 reach, flicker 0.75 at 6 Hz.
- **Long lines slower movement, would look really cool with a slow p:** the observed saved label; slower warm loops, 0.18 spin, -0.021 precession, 10.2-second history, full flicker.
- **idk what to call it but its purple and beautiful!:** Violet & rose, sparks, 3.75 / 4.5 dimensions, -0.021 precession, 2 Hz tail flicker; broad tumbling loops.
- **this one also looks so cool!!!!:** the same wide violet family with +0.008 precession; the latest user-favoured reference, with a bright woven centre and fine fading outer arcs.

These are parameter recipes, not a full export of browser saves. Camera vectors, animation phase and exact historical frames were not recovered into this file. Matching the controls recreates the motion family, not an identical screenshot. The live library also stores camera and phase and remains on its browser origin; ports 8799 and 8793 have separate libraries.

Daniel supplied the physical inspiration, requested form/material/camera variations and discovered the saved combinations through exploration. House work already established adjustable VFX, musical visual grammar and saved looks. Navi's Aurora Ribbons and Feedback Tunnel are concrete earlier preset examples. Gyre adds purpose-built kinematic paths, trail shaders and preset storage; it directly imports the crystal performance helper. Similar design vocabulary is evidence of continuity, not proof that a particular older shader was copied.

## Repeatable workflow

1. Read this standard and the relevant existing design/component docs. Inspect the user's current state and a nearby reference.
2. Write the intended visual experience in one sentence. Choose the focal form, motion hierarchy, palette roles and three observable acceptance criteria.
3. Establish one convincing scene and its geometry invariants. Add expressive controls once each has a clear visual meaning.
4. Inspect motion at the intended pixel size. Compare several phases and one deliberately difficult case. Tune proportion, colour and timing before adding unrelated decoration.
5. Exercise switching, extremes and persistence; measure frame delivery and resource stability. Make performance tradeoffs explicit.
6. Record the result, exact settings, environment, failures and remaining limits. Preserve promising discoveries as named variants. Credit user choices and earlier work precisely.

Do not apply an idle animation floor indiscriminately: a standalone sculpture may drift continuously, while musical performance may call for genuine rest. Likewise, deterministic kinematic paths suit this work; a task requiring force/torque realism needs a different model.

## Acceptance for the next visual change

Scale verification to the changed behavior. Keep both an artistic review and a technical receipt.

- **Composition:** judge full view and a close view; light and dark backgrounds where supported; several animation phases; quiet and dense musical input where relevant. Record what became clearer or more expressive and any aesthetic regression.
- **Resolution:** record CSS viewport, device pixel ratio and actual drawing buffer. "Native" is the current viewport in physical pixels. "4K fit" preserves aspect inside 3840 x 2160 and may be narrower. An exact 4K claim requires an observed 3840 x 2160 buffer.
- **Timing:** on this workstation target at least 60 delivered fps with p95 at or below roughly 16.7 ms in the agreed representative scene. Report mean FPS, p95, worst interval and missed-budget percentage. Inspect periodic stutter and input response; report tradeoffs if the target is missed. Monitor-rate performance remains an aspiration until measured in that configuration.
- **Measurement method:** warm up, then use the existing ten-second measurement for comparable screening. For a sustained-performance claim, extend the observation through the slowest meaningful motion cycle and check stability. At 0.008 rev/s, one precession turn takes 125 seconds. Record GPU/backend, MSAA, dimensions, settings, visibility and competing GPU load. RAF delivery is not GPU timing or physical scanout.
- **Resources and lifecycle:** compare resources after both trail modes have first rendered, then after repeated switching. Check true pause with an unchanged frame counter between reads; check resume, resize and hidden-tab handling when touched. Rebuilds must dispose owned resources.
- **State and input:** load/save/update round trips, camera/view restoration, old records, malformed/quota failures, channel sustain and input switching as relevant. Silent chord previews and unit tests do not establish physical MIDI hardware success.
- **Compatibility:** use existing host services for integrated pianos and retain capture/settings behavior. Test the affected surface at a compact layout and its target display.
- **Decision:** report observed success, proposed improvement and unverified behavior separately. Tests can guard geometry and storage; human visual judgment remains necessary.

Relevant focused suites, from the repository root:

```powershell
node --test tests/gyre_motion.test.mjs tests/gyre_presets.test.mjs tests/gyre_harmony.test.mjs
node --test tests/piano_crystal_performance.test.mjs tests/piano_solstice_signals.test.mjs tests/piano_instrument_state.test.mjs tests/piano_looks_registry.test.mjs tests/piano_looks_store.test.mjs tests/piano_string_envelope.test.mjs
```

Run the suites appropriate to the changed code, plus actual browser review. This capture is documentation and recipe work; it does not assert a new runtime test run.

## Evidence recorded tonight

These are dated observations from receipts, not guarantees for future code or other hardware.

| Configuration | Observed delivery | Source |
| --- | --- | --- |
| Original Gyre, Sparks/Beads/Silk including 40-light maximum-control Silk, 3630 x 2160 fit, 4x MSAA | 240 fps; p95 4.3 ms; 10-second samples | [Original Gyre receipt](../logs/gyre-20260921/results.md) |
| Tidal braid, 24 silk emitters, 1485 x 915 native preview | 240 fps; p95 4.3 ms | [New-world receipt](../logs/gyre-worlds-20260921/results.md) |
| Solar wind, 32 silk emitters and attached camera, 3506 x 2160 fit, 4x MSAA | 120 fps; p95 8.5 ms | [New-world receipt](../logs/gyre-worlds-20260921/results.md) |
| Main piano, observed 3840 x 2160 canvas | UI generally 143-160 fps with another rendering tab; final display 230, not a sustained benchmark | [Studio receipt](../logs/piano-workbench-20260921/results.md) |

GPU for the measured Gyre runs: AMD Radeon RX 9070 XT through ANGLE/D3D11. New-world checks recorded 26 passing tests and no browser warnings/errors. The main studio receipt records a successful silent canvas capture; encoded timing, recorded audio and physical MIDI were not independently established. Receipts identify other checks that were code-inspected rather than exercised.

## Source map

- [Gyre behavior and limits](web/piano/GYRE.md)
- [Renderer and trail shaders](web/piano-gyre.js), [motion equations](web/piano/gyre-motion.mjs), [preset validation/storage](web/piano/gyre-presets.mjs)
- [Crystal performance helper](web/piano/crystal-performance.mjs), [crystal study builder](web/piano/crystal-studies.js)
- [Studio integration](web/piano/workbench.js), [existing saved-look registry](web/piano/looks/registry.js)
- [Existing musical design language](SPECTACLE-DESIGN.md), [house preset bank](web/play.js)
- [Navi's Aurora Ribbons](web/presets/aurora-ribbons.frag), [Navi's Feedback Tunnel](web/presets/feedback-tunnel.frag)
