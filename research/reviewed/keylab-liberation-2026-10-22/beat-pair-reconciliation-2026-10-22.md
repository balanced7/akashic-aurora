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

## Addendum: the kick-gate lane (Heimdall, 2026-10-22, same evening)

Heimdall took the unseeded weak spot and returned a NEGATIVE, with data (bus 1792706081643-0). He tried three
formulations of a kick-likeness function on the onset bands (0-400 Hz body vs hats). Gate-value medians: kick
.689, tops .604, melodic .661. Kick and melodic overlap hard (kick min .498 vs melodic max .832), and no threshold
reaches aubio's melodic .386 without dropping kick from .653 to .621. beat_a.py was reverted byte-clean to
8928fea1 (verified by Vandor). Lesson: beat_a_kick_gate_transient_sharpness_does_not_separate. A real kick detector
needs the sub-150 Hz TIME-DOMAIN envelope per onset (attack slope, decay rate), not spectral-flux band means.

Vandor's note on his sweep. At threshold 0.70 the gated tracker beat shipped on every class of that sample
(kick .660, tops .213, melodic .376). The threshold was chosen in-sample, though, and the gate values overlap,
so it is most likely selected noise. It is NOT adopted. An optional held-out check was pre-registered with
Heimdall: threshold fixed at 0.70, a fresh stratified sample (seed 101), passing only if melodic CMLt rises
>= +.05 and kick and tops each drop <= .01.

### Second attempt: the time-domain envelope (Heimdall, bus 1792706667791-0)

Heimdall rebuilt the gate on the retained low-band MAGNITUDE envelope, with two features:
- body = log1p(median 0-400 Hz level);
- duty = mean/max.

The classes DO separate on these features (kick body ~.19 / duty ~.14, melodic ~1.24 / ~.23, tops ~.02 / ~.05),
but the gate is a cliff with no tunable middle:

| gate | kick CMLt | tops CMLt | melodic CMLt | synthetic F |
|---|---|---|---|---|
| off (shipped) | .653 | .213 | .263 | .970 |
| on | .621 | .236 | .441 | .880 |

It fails three of the four pre-registered criteria (kick, tops and synthetic F). The synthetic kick decays to
near-silence between hits, so the gate reads it as "not kick-like". The file-name taxonomy is also noisy at the
boundary: some "Drum" loops are top loops, and some have no sub-400 Hz body at all. Reverted byte-clean
(verified), and the lock was released.

Lesson: beat_a_kick_gate_time_domain_envelope_synthetic_regression.

The lane is closed. The next real step, if ever wanted, is a PER-ONSET kick classifier on the raw sub-150 Hz
signal (attack slope, decay fit), with synthetic F pre-registered as its own criterion.

### Third: the held-out check PASSED, and the gate shipped as a labelled partial improvement

Heimdall ran the check pre-registered in Vandor's note: the relative-sharpness gate, threshold FIXED at 0.70, on
a fresh stratified sample (seed 101), gated against shipped. It passed, and he shipped it into beat_a.py:
- `kick_likeness()`, a pure module-level function;
- a per-band ring;
- `KICK_GATE = 0.70`, unseeded path only;
- the pin tests/test_keylab_beat_a_kickgate.py.

So his first "negative" was the in-sample artifact. **Vandor reproduced every number independently**, against the
shipped version loaded from HEAD.

Held out, seed 101, unseeded, shipped -> gated:

| class | F | CMLt | AMLt | Acc1 | octave err |
|---|---|---|---|---|---|
| kick | .692 -> .685 | .497 -> .518 (+.021) | .621 -> .621 | .567 -> .633 | .226 -> .157 |
| tops | .484 -> .468 | .304 -> .305 (+.001) | .661 -> .662 | .500 -> .567 | .163 -> .094 |
| melodic | .345 -> .349 | .155 -> .226 (+.071) | .465 -> .501 | .464 -> .679 | .205 -> .052 |

Seed 7, the reconciliation run:
- synthetic F .970 -> .967 (criterion >= .95: holds);
- kick CMLt .653 -> .660;
- melodic CMLt .263 -> .376;
- every SEEDED class is byte-identical.

**What the pre-registration did not measure.** F falls slightly on kick and tops:
- held out: -.007 and -.016;
- seed 7: -.025 and -.041.

What the gate buys is tempo-octave correctness across the board: Acc1 up on every class, octave errors cut by
30-75%. That is the most visible failure for the lights (half or double speed). It is shipped with the F cost
stated here.

Vandor's mutation check of the pin (a CODE mutation, not an input swap):
- sign flipped in kick_likeness: RED (2 failing);
- gate forced always open: RED (1 failing).
