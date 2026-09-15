# Synthesia bake-off, heat 1: results (2026-09-15)

Sheet: `heat1-sheet.jpg`. Three judges: Daniel's eye, rhythm-game craft and a practice read. Scores are out of 10.

## Ranking
1. **Entry M, Vandor "Straight Roll"** (synth-vandor), mean **7.83**. The only entry where the velocity bars show a crescendo at a glance, and its pedal reading works.
2. **Entry K, Navi "Bead & Beam"** (synth-navi), mean **5.50**. A clean roll where brightness follows velocity, but landscape is broken and the extra dynamics cues are too small to read.
3. **Entry L, Heimdall "Glow Echo"** (synth-heimdall), mean **5.00**. The calmest and cheapest, but loud and soft notes look the same.

Caveat: M was rendered on its own phrase and run fixtures, not the shared ones. Re-render it on `?set=heat1` before the final call.

## Measurements
| Check | K | L | M |
|---|---|---|---|
| Rise speed, measured (declared), u/s | 5.56-5.64 (5.6) | 5.95-6.05 (6.0) | 6.46-6.54 (6.5) |
| Six Eb4 with pedal down | 1 merged run | 1 merged run | 6 beads |
| Finger+pedal vs finger only | 1.000 | 1.000 | 1.218 |
| Washed-out lit px at strike | 29-36% | 23.5-47% | 0.3-0.8% |
| Brightness vs velocity, r | 0.97 | -0.00 | 0.99 |
| Soft-note glow halo, px | 50k | 22k | 0 |
| Non-peak px over bloom threshold | up to 798 | 0 | 0 |
| Ultra p95, ~505 bars | 8.3 ms | 8.0 ms | 8.4 ms |

Full data: `measure/<entry>/measure.json`.

## Defects to send each seat
**Navi**
- resize() never applies the 16:9 band (lines 591-595), so landscape bars stop near y 660.
- The needle and the ribbon cross the bloom threshold.
- Hard caps keep glowing for about 1 s.
- The ghost layer has zero height but still draws.
- The needles are too short to read.
- pedal() is empty, so pedalled repeats merge.

**Heimdall**
- The glow has no velocity term (lines 173 and 253).
- The echo never blooms and covers at most 16 px.
- pedal() does nothing, so pedalled repeats merge.
- Strike colours wash out.

**Vandor**
- Re-render on the shared heat1 fixtures.
- Soft notes never glow.
- A held loud note loses its glow after 0.6 s.
- The grid and glass floor use layers reserved for the host.
- update() touches the host camera.

## Grafts the judges want
- Build on M: velocity columns with peak ticks, hollow tails for pedal-held notes, lift lines, and separate beads under the pedal.
- Make M's peak ticks glow with velocity, keeping a faint glow even for soft notes.
- Keep strike colours saturated.
- From L: rounded caps and the correct landscape band.
- From K: a soft glow where the bar meets the rail.
- Thin out M's grid and floor near the notation.

## Heat 2
Sunshine, Asta and Rill join in heat 2.
