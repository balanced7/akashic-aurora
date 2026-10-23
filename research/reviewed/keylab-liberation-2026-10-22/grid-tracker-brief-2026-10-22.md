# BRIEF: a grid-holding, tempo-following real-time beat tracker (Akashic Aurora, A16 T4)

## Who and why
Daniel produces music in FL Studio. Our code paints his Arturia KeyLab's 12 RGB pads on each beat of whatever
is playing (Spotify through WASAPI loopback), PREDICTED ahead, so the light lands ON the beat. Tonight the
current tracker drifted live on TYNAN's "groovininininin" (half-time bass music, syncopated sub-bass, about 140 BPM).

## Daniel's design, verbatim
- "i want our beat detection to detect the grid not just the spaced out notes and to correct itself based on
  the grid keeping track of beats"
- "on what grid would all of these notes fit? the resolution needs to be accurate enough for that to work, then
  you adjust multiple grid permutations simultaniously with a confidence score, then you can adjust so they all
  connect to the master and they all agree"
- "perhaps we could adjust bpm, and maybe have a higher and lower volitility setting that are smartly joined or
  parsed, the volatile one could get guesses from the lower volitility one ... have shifting bpm and low + high
  volatility heuristics"
- "mechanically not with agents parsing": the detector is pure maths at runtime.

## What failed: the receipts
- **Live log:** locked at 140.8 BPM, then wandered: 124, 130, 167.8, 83.1, 159.7, 118.5, 131.3 (second-half
  median 124.7, range 118-160).
- **Mechanism in the current tracker (beat_a):**
  - each expected beat snaps 50% toward the strongest onset within ±100 ms;
  - the tempo hypothesis may flip after 1 s of disagreement;
  - the period is pulled 10% toward the current tempo guess every 0.25 s.

  It is a note-chaser with a one-second memory.
- **Synthetic "drift" suite** (constant tempo, half-time kick on 1 and snare on 3, loud sub-bass on syncopated
  16ths 3/6/10/13/15, never on a beat):

  | tracker | F | CMLt | Acc1 | spread | flips |
  |---|---|---|---|---|---|
  | aubio | .809 | .513 | .80 | .24 | 3.2 |
  | beat_a | .218 | .012 | .20 | .009 | 0.2 |

  beat_a locks a WRONG grid steadily (112 BPM for 140, 171 for 128). Seeded with the true 140, it locks on the
  off-beat bass (F .000).
- **Synthetic "shift" suite** (a sudden tempo step at 20 s):

  | tracker | F | CMLt | relock | never relocked |
  |---|---|---|---|---|
  | aubio | .747 | .631 | 6.3 s | 1 of 4 |
  | beat_a | .656 | .540 | 3.1 s | 2 of 4 |

## The design skeleton (Daniel's, with Vandor's reading)
1. **Grid hypotheses scored on ALL notes.** A hypothesis is (tempo, anchor phase, subdivision family: straight
   16ths or triplets). Its score is how well EVERY detected onset in the last few bars lands on its grid lines,
   strength-weighted. Off-grid onsets count against it. Onset times need sub-frame precision.
2. **Parsimony.** The coarsest grid that explains the notes wins. A grid fine enough to fit anything (64ths)
   must not.
3. **Many hypotheses at once**, each with a confidence, updated continuously.
4. **One master family.** Hypotheses related by octave or subdivision (70 / 140 / 280) are ONE grid at
   different levels, so they merge and vote together. The beat level comes from accent (kick and snare bands)
   and the database seed when there is one.
5. **Two volatility models, an IMM (Interacting Multiple Model) filter.**
   - A low-volatility model (near-constant tempo) HOLDS the grid through syncopation.
   - A high-volatility model FOLLOWS real tempo changes (DJ transitions, automation, live drummers).
   - Both are mixed every beat by a live regime probability; the mixing step is "the volatile one gets guesses
     from the stable one".
6. **Hysteresis.** The master family changes only when a rival outscores it for several bars. Corrections are
   small and averaged, never per-note snaps.
7. **Predict from the master grid.** Counting beats gives bar position, so is_downbeat is encouraged but
   optional.

## The contract every tracker meets (arsenal/keylab/beatbench.py)
- `tracker = Tracker(rate, hop, seed_bpm=None)`, with `hop` = 512 at 44.1 or 48 kHz.
- `tracker.feed(block)` takes a float32 mono block of `hop` samples. It returns OBSERVED beats:
  `[{"t_beat": s, "bpm", "phase": 0..1, "confidence": 0..1, "is_downbeat": bool|None}]`.
- `tracker.predict(now)` returns EXPECTED beats after `now`: `[{"t_beat", "bpm", "phase", "confidence"}]`.
- Imports: stdlib, numpy and scipy ONLY (enforced by tests/test_keylab_beat_licence_firewall.py). No relative
  imports, so the file is self-contained in one `arsenal/keylab/beat_*.py`.
- CAUSAL: never look at audio beyond what has been fed. No constants copied from the bench (e.g. the bass 16th
  positions).
- Realtime: at least 20× faster than real time on one core.

## Acceptance, pre-registered and committed (b06495ff) before any contestant
Scored by Vandor, independently. A tracker ships only if ALL hold. F is co-primary everywhere.

| suite | criterion |
|---|---|
| drift (5) | F >= .85, CMLt >= .75, bpm_spread <= .02, tempo_flips <= 0.5 |
| shift (4) | F >= .85, CMLt >= .75, mean relock <= 4.0 s, none never-relocked |
| synthetic (14) | F >= .95, CMLt >= .85 (beat_a .970 / .910) |
| loops (90 real, from Daniel's packs; kick / tops / melodic; unseeded and seeded) | F and CMLt within .02 of beat_a; bpm_spread <= beat_a's |
| speed | realtime_x_min >= 20 |

beat_a's loop numbers, seed 7:

| class | F | CMLt |
|---|---|---|
| kick, unseeded | .723 | .660 |
| tops, unseeded | .352 | .213 |
| melodic, unseeded | .465 | .376 |
| kick, seeded | .803 | .805 |
| tops, seeded | .409 | .395 |
| melodic, seeded | .547 | .559 |
