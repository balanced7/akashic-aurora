# Entry: Vandor, "Straight Roll"

**The idea in one sentence.** This is your original straight light columns, made bigger: glass tubes that rise from the exact key, with a velocity cap whose peak glows and then fades, and a small meter needle on each key that holds the loudest recent strike for a second.

Module: `arsenal/web/piano/schemes/synth-vandor.js` (id `synth-vandor`). Build target: lookdev2 `straight-lines-proposal.md` section 3 (W's tubes, X's attack and lift line). There are no words: chord names stay with the host.

## What makes it Synthesia
- **Bars from keys.** There is one lane per key at `keyX(m)`, straight up at a steady 6.5 u/s, and a bar's length is how long the note sounded. Every bar starts on one onset row at y -0.10, which sits inside the key, so the key hides the foot and a chord's heads form one line.
- **Contact in the same frame.** On noteOn the key edge gets a flash with a sideways streak (R 0.45+1.15v), a ring across the key tops, and sparks (3+36v²).
- **Beads.** A re-struck note ends its previous bar at least max(0.16 u, 5 px) before the new onset. Only the bar's end moves; its onset stays exact.
- **Finger vs pedal.** While the finger holds, the bar is a solid glossy core. While only the pedal holds, it is a hollow rim over tinted glass. Finger plus pedal is brightest (x1.22). When the pedal lifts, an amber line crosses the lane board and rises with the roll, cutting every pedal tail at the same height.
- **Colour is the note.** Each bar is `noteColor` re-lit in OKLab. Velocity raises lightness and chroma; hue never changes and nothing is pushed to white. Old bars dim and lose some colour over 3.5 s.
- **Bloom decays, and only the peak blooms.** The peak (the flash inside the cap plus its halo) is one mesh. It is the only additive draw, and it draws last. Every other light layer (lane board and contact line, glass floor, strike flash, ring, sparks) is *luma-bounded light*: premultiplied, with alpha = luma / 0.85. Over a pixel at or below 0.85 luma the result stays at or below 0.85. Over a brighter pixel, such as a lit host key, its luma never rises. That holds however many layers stack, so a chord's flashes, rings and sparks cannot add up past the 0.9 threshold. Bars and needles were already ordinary "over" layers capped at 0.8.

## Dynamics
- **Velocity bar with a glowing peak.** The cap length is W x (0.45 + 2.1v). Its glow strength is pk = 0.34 + 0.66 v^1.35, so a soft strike still glows faintly, and the glow is pk x (2.2e^(-age/0.16) + 0.6e^(-age/0.8)), reaching W x (0.22 + 0.8v), a little brighter with the pedal down. While the finger holds, it decays only down to an ember of 0.20 x v (the larger of the two, never their sum), which fades in 0.25 s once the finger lifts. So a held forte keeps a small glow at its peak, and nothing stacks or stays at full bloom.
- **Second cue: a VU-style peak-hold needle per lane (chosen over the contact ripple).** A strike throws the needle to 0.6 + 4.2v above the keys, but only if that is higher than where the needle already is. It holds for 1 s and then falls. A faint glass sleeve under it reads as the velocity bar you already like.
- **Why the needle and not a ripple.** A ripple lasts about as long as the flash, so it tells you nothing the flash hasn't already said. The needle lingers after the attack is gone, so a chord leaves a row of needles you can compare after the strike: is the melody above the chord, and did the thumb land hard? Anyone who has watched a stereo meter reads it without being taught. The X ring stays in, but only as part of the strike.

## Receipts (headless, RX 9070 XT, the house fixtures, synthetic MIDI)

| Check | Result |
|---|---|
| Contract | all 8 methods present, 0 host scheme errors |
| Six repeated Eb4, no pedal | 6 bars; gaps 48.5 to 54.4 px portrait, at least 25.6 px landscape |
| Six repeated Eb4 under pedal | 6 bars; gaps 8.8 to 9.9 px (the rule itself) |
| Finger vs pedal-only (one Eb3 bar, v112) | centre luma 0.77 solid vs 0.24 hollow; rim/centre 2.6 on the hollow part |
| Peak glow halo, hard v112 / soft v38, same Eb4, at 0.1 s (fix window, bloom on minus off, 8-bit luma >= 4) | 121,259 / 7,020 px (17.3x); a second matched pair gives 140,836 / 1,341 px (105x). Heat 1 had the soft glow at 0 px |
| Held v112 Eb4 (key down 2.4 s, no pedal), halo px | 140,836 at 0.1 s; 47,549 at 0.6 s; 42,854 at 1.5 s (30% of the strike's area, 27% of its summed light); 0 by 0.3 s after the key lifts. Heat 1: 0 at 0.6 s and 1.0 s. Held v38: peak luma 0.044 vs 0.129 for v112 (about the velocity ratio), below the bloom threshold |
| Draw calls | 10 draws, 5,476 triangles, 2,048 points (the page with vs without the scheme) |
| Frame time, Ultra 1440x2560, 251 to 323 live bars (mean 264) | fix window: p95 7.9 ms over 600 frames (p50 7.0); scheme hidden p95 7.7 ms; update() p95 0.1 ms. Heat 1: p95 8.4 ms |
| Errors | 0 page errors across 5 bursts |
| Bloom isolation (HDR float render, threshold 0.9, 13 probes) | 0 pixels pushed or brightened over the threshold by any non-peak layer. Before the fix, the strike flash alone pushed 839-6,267. The whole scheme's peaks add 553 px (single) to 12,027 px (chord, frame 1) over the threshold, and all of it decays. |
| Bloom isolation (JPEG glow-on/off diff) | The residual strike-flash diff is 1,992 px on hard Eb4 frame 1; 1,746 of those pixels are *darker* in that channel. That is the luma-bounded flash dimming the host's own lit-key bloom, not added light (why diagnostic: dim-only vs light-only layers). The brief's rule 6 allows bloom on the strike itself, so this is within the brief. The verifier's stricter "only the peak blooms" reading is noted. |
| piano-next.html (today's tree) | boots; `registerScheme` then `selectScheme('synth-vandor')` returns true; 11 noteOn/Release/End events, 0 errors |

## Heat 1 fix window (2026-09-15, 13:05-13:45 EDT)
Only the four measured defects were fixed; nothing else changed. Module sha256 `abe98502fa667889951add40fbba29b29cd2085d990af6ecb8cf63d413140a85` (heat 1 was `5f6fb488...`).
1. **update() no longer touches the host camera.** The `camera.updateMatrixWorld()` call is gone; `project()` only reads the matrices as the host last rendered them. Checked in the page: 66 page-driven and 30 direct update() calls, plus a stale-camera probe (camera moved and fov changed without matrix updates), gave 0 changes to camera, renderer, fog or scene state and 0 trapped setter calls. A positive control that calls `updateMatrixWorld()` is caught (5 matrix diffs, 1 trapped call). The only scene writes in the module are `scene.add(root)` and `scene.remove(root)`.
2. **The lane board and glass floor are the scheme's own objects in its own group.** All 10 meshes live in one `THREE.Group` named `synth-vandor` (render order 1, so their internal orders 5-17 sort only among themselves), on the default layer, with no renderer, fog or scene settings changed. Harness note: a probe that lists `scene.children` for `synth-vandor:*` names now has to traverse the group.
3. **Soft notes glow.** There is a velocity floor on the peak (numbers above).
4. **Held notes keep a small glow.** There is a sustained ember while the finger holds (numbers above).

Unchanged and re-measured: 0 non-peak HDR pixels over 0.9 in 7 states (Gbmaj13#11 v112 at 0.1 and 1.6 s, v127 at 0.05 and 1.5 s; Db6/9 v38 at 0.1 and 1.6 s; six Eb4 at v90), 0 pushed over by non-peak layers, 0 at Ultra; near-white fraction 0.
Frames on the shared heat1 fixtures (`?set=heat1`), portrait and landscape, 26 each, 0 errors: `bakeoff-heat1/synth-vandor-fix/{portrait,landscape}/sheet-heat1.jpg`. Measurements: `bakeoff-heat1/measure-fix/final/measure.json`.

## With more time
- Mist over the lanes, lit by the notes.
- A top-voice brightness cue for the melody.
- The three skins from the proposal (Luminous, Poster, Spectacle) on this same grammar.
- Let 16:9 set its own glass-floor reflection. It sits slightly off-axis at the wide lens.

## Host-side words (Z's onset stamps)
The scheme draws no text. The host's overlay would place the stamps:
- Group onsets within 60 ms, read chords with `chordread.createReader` (at least 3 pitch classes, 1.2 s aggregate under the pedal), and draw each stamp on a dark pill.
- Pin each pill every frame to the projected onset row: y = -0.10 + (now - t0) x 6.5, z = TRAIL_Z + 0.42.
- To keep that geometry in one place, I propose an optional scheme export `onsetRow(t0, t)` that returns world {y, z}, so the host never copies the roll's constants.

## Watch for
- The flash at the key must fade within about a quarter second on a hard six-Eb4 run.
- The needles should still hold, and then fall, after the chord's attack has gone.
- Under the pedal, the amber lift line should cut every pedal tail at the same height.
