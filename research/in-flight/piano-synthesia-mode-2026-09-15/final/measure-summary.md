# Synthesia bake-off, final heat: measurement summary (de-anonymised)

Review only. No tracked file, no entry, no git state and none of driver.mjs / server.py / fixture.js was changed. Only the scratch measurement look was changed (listed under Method).

Key: **P = synth-heimdall**, **Q = synth-sol**, **R = synth-vandor**, **S = synth-navi**.

## Run

Command: `node measure_driver.mjs --entries synth-navi,synth-heimdall,synth-sol,synth-vandor` (server 8998, Chrome 9998, headless=new with the anti-throttling flags).

- No jam_timing or jam_verify processes were running at launch.
- The GPU lock was taken and released for each burst:
  - synth-navi: 36.1 s
  - synth-heimdall: 35.5 s
  - synth-sol: 49.6 s (includes the diagnostic and counterfactual passes)
  - synth-vandor: 35.4 s
- Every burst ended in state done, with 0 look errors, 0 skipped sections, 0 page errors and 0 console errors.
- Afterwards: no lock directory, nothing listening on 8998 or 9998, and no Chrome or server process left.

**Data**
- `bakeoff-final/measure/<entry>/measure.json`
- Condensed: `bakeoff-final/analysis/final-metrics.json`
- Driver log: `bakeoff-final/measure-run.log`
- 16:9 frame read: `bakeoff-final/analysis/landscape_band.py`, run on the render frames

## Headline findings

1. **synth-sol's bars, beads and strike rings draw black.**
   - Its five InstancedMesh materials set `vertexColors: true`, but the geometries have no `color` attribute. The per-instance colour is therefore multiplied by an unbound attribute, which reads 0.
   - In-memory diagnostic on a held 7-note chord (v100):
     - as shipped: 0 lit bar px, max luma 0
     - `vertexColors = false`: 50,556 lit bar px, mean saturation 0.97, 0% near-white
     - restored: 0 lit bar px again
   - The renders agree: near-black columns with dark beads.
   - As shipped, almost every note-level check on Q is n/m. Only the breathline and crown lines light.
   - I did not edit the entry. Dropping `vertexColors: true` is the likely one-line fix, since `instanceColor` applies anyway. That is the seat's call.
2. **In the host, a repeat's noteEnd comes before its noteOn (same t).** That clears the "previous strike" that synth-heimdall, synth-navi and synth-sol use to pull a bead gap, so their pedalled repeats still merge. synth-vandor keeps its slot after noteEnd, so its gap still applies. This is from reading the code; the repeat counts below measure the effect.
3. **Regressions since heat 1:**
   - synth-navi's strike washout doubled (29.1/36.2% to 59.8/83.2%).
   - synth-heimdall's single strikes no longer bloom at all: halo 0 px at v112 and v38, where heat 1 had 39,208 and 22,458.

## Metrics, final heat, with heat-1 deltas

"a -> b" is heat 1 -> final heat, on the same measurement look and fixtures. n/m = not measured.

| Check | S synth-navi | P synth-heimdall | R synth-vandor | Q synth-sol (as shipped) |
|---|---|---|---|---|
| Rise speed, u/s | 5.56-5.64 -> 5.56-5.64 | 5.95-6.05 -> 5.95-6.05 | 6.46-6.54 -> 6.46-6.54 | n/m (declared 6.5) |
| Six Eb4, pedal down: separate bars | 1 -> 1 | 1 -> 1 | 6 -> 6 | n/m |
| 16 Eb4 at 8/s: dry / pedal down (new) | 12 / 1 | 14 / 2 | 16 / 16 | n/m |
| Finger+pedal vs finger | 1.000 -> 1.300 | 1.000 -> 1.280 | 1.218 -> 1.215 | n/m |
| Washed-out at strike (v112 / v127) | 29.1/36.2% -> **59.8/83.2%** | 23.5/47.1% -> 0/0% | 0.8/0.3% -> 0/0.2% | 0/0% (bars unlit) |
| Brightness vs velocity, r | 0.97 -> 0.95 | -0.00 -> 0.96 | 0.99 -> 0.97 | n/m |
| Soft halo at 0.1 s, px | 50,046 -> 30,281 | 22,458 -> **0** | 0 -> 1,937 | 0 |
| Hard/soft halo ratio at 0.1 s | 2.00 -> 2.32 | 1.75 -> 0/0 | 136,820/0 -> 73.6 | 0/0 |
| Hard halo at 0.6 s, key up at 1.2 s (heat-1 protocol) | 70,132 -> 30,046 | 0 -> 0 | 0 -> 51,565 | 0 |
| Held v112, key down 2.4 s: halo at 0.6 / 1.5 s (new) | 26,635 / 20,173 | 0 / 0 | 43,401 / 38,123 | 0 / 0 |
| Hard cap px over threshold at 1.0 s | 253 -> 254 | 0 -> 0 | 0 -> 0 (its glow crosses only in the composite) | 0 |
| Non-peak px over threshold, worst Studio / Ultra | 840 / 2,195 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 |
| Ultra p95 ms: full (bars) / ~250 | 8.3 (508) / 8.0 -> 8.7 (542) / 8.3 | 8.0 (513) / 7.7 -> 8.8 (547) / 8.7 | 8.4 (504) / n/m -> 8.5 (536) / 8.2 | 8.5 (511) / 8.1 (274) |
| Ultra p95 with the entry hidden | 8.0 -> 8.3 | 7.9 -> 8.5 | 8.0 -> 7.9 | 8.5 |
| Draw calls (triangles / points) | 5 -> 5 (3,586 / 0) | 3 -> 3 (1,280 / 512) | 10 -> 10 (5,476 / 2,048) | 7 (69,600 / 0) |

The hidden-entry baseline also rose 0.3-0.6 ms since heat 1. Most of the frame-time increase is therefore machine drift, not the entries.

## Heat-1 defect re-check

### synth-navi (S)

| Heat-1 defect | Status | Evidence |
|---|---|---|
| 16:9 fade band not applied; bars stopped near y 660 | **fixed** | Highest saturated bar row in the 16:9 phrase and run frames: 482-514. Heat 1, same frames: 692-726 bright, 528-544 dim. The bars now fade out above the row-470 band start. |
| Ghosts zero height | **fixed** | The ghost layer lights up to 5,893 px in the isolated probes, with 0 px over threshold. |
| Loudness ribbon crossed the protected top band | **fixed** | 9:16: first lit row 678 (heat 1: row 0, whole column lit). 16:9 render: first lit row 496-501 (heat 1: row 0). |
| pedal() empty: repeats merged, finger+pedal = finger | **partly** | Finger+pedal is now 1.300 (was 1.000). Pedalled repeats still merge: six Eb4 give 1 run (seam minimum luma 0.13-0.36) and 16 rapid give 1 run. Cause: host noteEnd before noteOn (headline 2). The bar ends at the new onset, and the new cap overlaps it. |
| Peak-hold needle a ~10 px dotted row; 798 non-peak px over bloom | **partly** | Over-bloom is fixed: 0 px at every Studio probe and at Ultra (was 840 / 2,195). The needle is now a sub-pixel hairline: 5-14 px per needle, height vs velocity r 0.12 (heat 1: -0.23), and v30 needles often not found. Still not readable. |
| Hard caps glowing ~1 s | **not fixed** | Hard cap over threshold: 254 px at 1.0 s (heat 1: 253) and 238 px at 1.5 s while held. Halo 21,004 px at 1.0 s. |
| 50k px soft halo | **partly** | 30,281 px at 0.1 s (was 50,046), 0 by 0.6 s (was 25,329). |
| 29-36% washed strike pixels | **not fixed (worse)** | 59.8% (v112 at 0.1 s) and 83.2% (v127 at 0.05 s) of lit canvas pixels have low saturation; HDR 28.9% / 28.4%; near-white 0%. The strike's luma is now capped at 2.2, but the cap colour is relit at chroma x0.62, so it desaturates instead of whitening. |

### synth-heimdall (P)

| Heat-1 defect | Status | Evidence |
|---|---|---|
| Glow had no velocity term (r -0.00) | **fixed, with a regression** | Brightness vs velocity r is 0.958. But single strikes no longer bloom: halo 0 px at 0.1 s for v112 and v38 (heat 1: 39,208 / 22,458). The cap crosses the threshold only near v120 at 0.05 s (532 px) and on the v127 chord (2,311 px; halo 24,237 at 0.05 s, 0 by 0.3 s). The peaks now glow only at fortissimo. |
| Echo never bloomed, at most 16 px | **partly** | The echo is far larger: up to 1,847 px at v120, 0.05 s (heat-1 data: at most 25 px). Its height and area track velocity (r 0.71 / 0.89). It still never crosses the bloom threshold: 0 px at every probe. |
| pedal() empty | **partly** | pedal() now drives a brightness term and ends tails on lift; finger+pedal is 1.280 (was 1.000). Pedalled repeats still merge: six Eb4 give 1 run and 16 rapid give 2 runs. The 0.06 s bead gap never runs, because host noteEnd arrives first and clears the stored strike. |
| Strike washout 23.5-47% | **fixed** | 0% / 0% low-saturation lit pixels at the strike; max luma 0.84 (v112) and 1.00 (v127). |

### synth-vandor (R)

| Heat-1 defect | Status | Evidence |
|---|---|---|
| Camera writes in update() | **fixed** | 66 page-driven and 30 direct update() calls gave 0 camera, renderer or scene diffs and 0 trapped method calls. The stale-matrix probe gave 0 diffs. The positive control tripped (5 diffs, 1 trapped updateMatrixWorld), so the detector works. |
| Host-reserved layers | **fixed** | 11 of 11 objects under its group are on the default layer only (mask 1). |
| Soft notes never glowed | **partly** | v38 halo is now 1,937 px at 0.1 s (heat 1: 0); 6,975 px in the held run. It is gone by 0.3 s, and the held soft note shows 0 at 0.6 s. Hard/soft ratio 73.6. |
| Held glow gone by 0.6 s | **fixed** | Held v112 halo: 43,401 px at 0.6 s, 38,123 at 1.5 s, 42,784 at 2.0 s. It is 0 at 2.3 s, while the key is still down, as the cap rises into the fade band. Heat-1 protocol (key up at 1.2 s): 51,565 at 0.6 s (was 0). |

Also measured for R, not heat-1 defects:
- 16 rapid Eb4 give 16 separate bars dry and 16 with the pedal down.
- On pedal lift, the ended bars sit 0.51-0.68 px from the lift row and 1,140 px light up between the lanes (its amber lift line).
- In the 16:9 render frames its bars reach rows 81-118 of 1080 (its own fade band is 0.80-0.95 of the height). The judges should check whether that clears the heading block.

## synth-sol (Q): its own acceptance claims

- **As shipped** is the real entry.
- **CF** is a clearly separate in-memory pass in the same burst, with `vertexColors = false` on the five instanced materials, restored afterwards. It shows what the design measures once its colours reach the screen. The tables above use as-shipped numbers only.
- Its `pedal()` handler is a no-op. Every pedal behaviour below comes from the host's noteRelease/noteEnd events.

| Claim (entry_sol.md) | As shipped | CF (vertexColors off) | Verdict |
|---|---|---|---|
| 16 rapid same-note strikes give 16 beads | 0 lit runs | Dry: 16 of 16. Pedal down: 1 run at luma 0.02, 16 at 0.15 (seams only luma 0.069). | Not met. CF: met dry; under the pedal, only as dim seams. The 0.014 s retrigger gap never applies (host order). |
| A still frame tells finger-held, pedal-held and ended apart | Nothing lit | Finger-held: filled, centre 0.188. Pedal-held: hollow, centre 0 and rim 0.234. Ended: filled and dim, 0.057. The whole bar switches state, so the finger-held part of a pedalled note also turns hollow. | Not met. CF: met. |
| No clip to white | 0% near-white (bars unlit) | 0% near-white; at most 0.3% low saturation at the strike | Trivially met. CF: met. |
| Fortissimo bloom decays within 500 ms | No bloom anywhere (0 halo px) | v127 chord halo 72,140 px at 0.05 s, 0 at 0.3 s. But the bead never crosses the threshold (0 px). The bloom comes from the key-edge ring (strike layer, 304-461 px over threshold). | Not met. CF: decays in time, but "cap is the only blooming note surface" fails (the cap never blooms, the ring does). |
| CC64-up gives one shared release line; still-held notes stay filled | Nothing visible | All 4 lane ends sit 1.2-1.8 px from the lift row (spread 0.6 px), from the host's lift sweep. No ring-cap (foot/middle luma 1.00) and 0 px between lanes. The held note stays filled: centre 0.188 vs 0.065. | Not met. CF: ends align and held stays filled, but nothing marks a release line. |
| p95 at most 16.7 ms with about 250 bars | 8.1 ms (274 bars); 8.5 ms (511); update p95 0.3-0.4 ms | same | **Met.** 7 draw calls, 69,600 triangles (sphere beads). |
| Cap radius and bar thickness monotonic with velocity | Not visible | Width 0.476 / 0.530 / 0.610 / 0.690 u at v30 / 60 / 90 / 120. Bead lit px 21 / 30 / 42 / 54 at 0.9 s. Brightness vs velocity r 0.80. | Not met. CF: met. |
| Breathline rises and falls with the crescendo, without note-level flicker | Value read from its vertex buffer: r 0.755 vs velocity. 0.43 at note 0, 1.00 (clamped) for notes 9-15, 0.42 at note 24. Moves 0.10 per note between 0.05 s and 0.25 s after each strike. Pixels: 0 lit at 9:16 (it sits left of the lowest key, off screen). In the 16:9 render it is visible at the far left and runs through the title text in the protected top band. | same | Partly. It follows the arc but saturates at the top and ripples per note. Invisible in portrait; crosses the protected band in landscape. |

Also for Q:
- Finger+pedal equals finger (CF 1.00), because pedal() does nothing.
- The arrival crown lit up to 484 px in the probes.
- No camera, renderer or scene writes (0 diffs, control tripped); 0 of 8 objects off the default layer.
- Q was never measured in heat 1, so it has no deltas.

## Problems found (reported, not edited)

1. **synth-sol.js:** `vertexColors: true` on the bodies, histories, shellRails, peaks and flashes materials, with no colour attribute. Everything but the two lines renders black (headline 1).
2. **synth-sol.js:** the breathline sits at `keyX(KEY.first) - 0.72` with no band fade. It is off screen at 9:16 and crosses the title block at 16:9.
3. **Host event order vs the entries:** noteEnd before noteOn on a repeat defeats the re-strike gap in synth-heimdall (BEAD_GAP), synth-navi and synth-sol (REPEAT_GAP_S). Only synth-vandor beads under the pedal.
4. **synth-navi:** strike saturation regressed (cap chroma x0.62); the needle is now sub-pixel; hard caps still over threshold at 1.0-1.5 s.
5. **synth-heimdall:** the velocity fix removed bloom for every single strike below about v120.

## Method notes

**Harness.** driver.mjs, server.py and fixture.js were not changed. Scratch-only changes to `looks/measure-heat1.js` (backup `analysis/measure-heat1.before-final-measure.js`, patch `analysis/patch_measure_look.py`):

- Sections are registered in a list and then run, which lets the CF pass re-run a subset.
- synth-sol CFG, with its seven group children named `synth-sol:<part>` in memory at mount. Each child's type was checked: 5 InstancedMesh, 2 Line.
- A CFG name check against the current modules. All four CFGs matched, with 0 missing names (synth-vandor's meshes are now under one group; the whole-scene search finds them).
- New checks:
  - lit px per layer
  - the 16-strike repeat test
  - bar width in the velocity sweep
  - a breathline reader
  - K_held (the held-glow protocol from the heat-1 fix review, plus a held v127 chord)
  - R_release (pedal-lift line)
  - X_cam (the heat-1 fix review's camera/state detector, with positive control)
  - a layer audit
  - the synth-sol vertex-colour diagnostic and CF pass
- One shared-code change: the isolated render keeps hidden any part the scheme itself hid (synth-sol's crown). For the other three entries this changes nothing, since all their parts are visible while active.

**Heat-1 comparisons** use `bakeoff-heat1/measure/<entry>/measure.json`, read through the same field paths as the heat-1 table:
- washout = canvas low-saturation fraction on Gbmaj13#11 (v112 at 0.1 s, v127 at 0.05 s)
- r = peak maximum luma vs velocity over the run
- soft halo = E_glow v38 at 0.1 s

Heat 1 had no 16-strike, held 1.5 s, release, camera or layer probes. The 16:9 heat-1 comparison uses `bakeoff-heat1/synth-navi/landscape` frames from the same fixture set.
