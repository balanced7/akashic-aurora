# Reconciliation: the blind beat-tracker pair, beat_a vs beat_b vs aubio (2026-10-22)

Daniel (Discord, 2026-10-22): "Go ahead and continue working, lets see what we can figure out for our own internal
beat detector." This records how the replacement for aubio (GPLv3+) was chosen.

## Protocol

- **The bench came first.** arsenal/keylab/beatbench.py was committed (2b0d31f1) before either tracker existed.
  Its contract was agreed with Heimdall (bus 1792703252595-0):
  - feed() returns OBSERVED beats;
  - predict() returns EXPECTED beats;
  - downbeats are optional;
  - the metrics pick the better tracker and the licence picks the shippable one, as two separate questions.
- **Written blind.** beat_a.py (Vandor) and beat_b.py (Heimdall) were written without reading each other.
  Heimdall confirmed in his submission that he never opened beat_a. Vandor opened beat_b only after both had
  been submitted.
- **Licence firewall.** tests/test_keylab_beat_licence_firewall.py allows stdlib, numpy and scipy only. Both
  files pass, so both are shippable and the decision is on the numbers alone.
- **One run, identical cases.** `beatbench --suite all --per-cat 30 --seeded --trackers aubio,a,b`, 190 cases:
  - 14 synthetic;
  - 30 kick, 30 tops and 30 melodic loops from Daniel's own packs, each run unseeded and seeded (seed = the
    BPM in the file name).

  Receipt: state/arsenal/keylab/receipts/beatbench-20261022-174354.json (local; it lists loop paths).

## Results

| Tracker | Class | F | CMLt | AMLt | Acc1 | Octave err | Never locked | Pred err ms / hit |
|---|---|---|---|---|---|---|---|---|
| aubio | synthetic | .712 | .498 | .736 | .714 | .216 | 1/14 | — |
| **a** | synthetic | **.970** | **.910** | **.981** | **.929** | .083 | 1/14 | **6.2 / .921** |
| b | synthetic | .631 | .539 | .651 | .571 | .127 | 4/14 | 104.7 / .536 |
| aubio | kick | .707 | .593 | .826 | .750 | .110 | 11/28 | — |
| **a** | kick | **.748** | **.653** | .792 | **.786** | .135 | 7/28 | 88.8 / .667 |
| b | kick | .299 | .199 | .259 | .429 | .000 | 22/28 | 145.6 / .190 |
| **a** | kick, seeded | **.803** | **.805** | **.852** | **.964** | **.000** | 5/28 | **29.0 / .784** |
| b | kick, seeded | .312 | .177 | .200 | .429 | .000 | 26/28 | 118.5 / .183 |
| aubio | tops | .408 | .247 | .746 | .667 | .167 | 18/30 | — |
| a | tops | .393 | .213 | .764 | .633 | .225 | 19/30 | 164.9 / .354 |
| **a** | tops, seeded | .409 | **.395** | **.850** | **.967** | .000 | 16/30 | 128.6 / .419 |
| aubio | melodic | **.518** | **.386** | .613 | .567 | .113 | 15/30 | — |
| a | melodic | .464 | .263 | .527 | .500 | .256 | 19/30 | 113.7 / .353 |
| **a** | melodic, seeded | **.547** | **.559** | **.830** | **1.000** | .000 | 10/30 | 91.8 / .477 |

Speed is the worst case across all runs, as a multiple of real time:
- aubio: 979×;
- a: 86×;
- b: 4.9×.

## Verdict

**beat_a ships**: it becomes the default engine of `py -m arsenal.keylab beat` (`--engine a`), painting the pads
ahead of the beat from predict(). It wins:
- every seeded class;
- synthetic, by a wide margin;
- kick loops unseeded, the class most like a full mix.

**aubio stays** as `--engine aubio`, optional, lazily imported and never vendored, so the comparison remains
runnable.

**beat_b stays in the repo** as a recorded contestant, registered as tracker "b" for future rounds. On real
audio its adaptive peak picker rarely fires a beat that its grid gate accepts, so it seldom locks (22-30
"never locked" per class), and every downstream metric inherits that.

## What each side contributed

- **From Heimdall (process):**
  - the `beat_a` / `beat_b` names, avoiding a `tempo_b` that his `tempo*` boundary glob would have swallowed;
  - predict() as a separate call, so detection failures and phase-lock failures are scored apart;
  - optional downbeats;
  - the rule that score and licence are separate questions.

  All four are in the contract.
- **From Heimdall (algorithm):** the octave fold with seed snap, and BPM taken as the median of observed
  inter-beat intervals. Neither is adopted yet. beat_a's seeded octave error is already .000, and its reported
  BPM is already accurate (Acc1 .96-1.0 seeded), so the bench gives no evidence they would add anything. They
  remain candidates if unseeded octave work resumes.
- **From Vandor:**
  - the bench;
  - band-averaged accent onsets. Summing bins let broadband hats outvote the kick; averaging per band fixed the
    off-beat trap, the 174 BPM 2/3 ghost and the sparse kick on synthetic;
  - comb phase lock plus a phase-locked loop that predicts ahead;
  - the unseeded accent rule for the metrical level.

## Honest limits, and what is next

1. **Unseeded hats-only and melodic loops:** beat_a is slightly below aubio (CMLt .213 vs .247; .263 vs .386).
   The accent rule that helps kick loops hurts these.
   - A kick gate was tried and removed: sub-bass share and periodicity do not separate kick loops from melodic
     ones (medians .276 vs .275).
   - A real kick detector, based on transient sharpness, is the next design step.
   - Hats-only loops are genuinely ambiguous between beat and off-beat in isolation, and AMLt is their fair
     metric. On AMLt, seeded beat_a scores .850 against aubio's .746.
2. **Lead calibration:** the default paints 15 ms early, covering the device's ~10 ms plus loopback capture.
   Probe P21 (a 240 fps phone video) measures it; `--lead-ms` tunes it by eye.
3. **Real songs:** loops are cut to the grid, but songs have intros, breakdowns and tempo changes. Two
   real-song sources follow:
   - Daniel's own FL renders, once the FLP tempo event is derived clean-room (save at two tempos, diff the events);
   - a listening session with the seed from the databases.
4. **Downbeats are not scored yet.** beat_b emits a coarse 4/4 layer; beat_a claims none.
