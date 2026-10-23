# Pre-registration: the grid tracker (2026-10-22, written before any contestant exists)

## The ask (Daniel, verbatim, live with FL Studio and the KeyLab open)
- "its drifting, i want our beat detection to detect the grid not just the spaced out notes and to correct
  itself based on the grid keeping track of beats, what do you think?"
- "on what grid would all of these notes fit? the resolution needs to be accurate enough for that to work, then
  you adjust multiple grid permutations simultaniously with a confidence score, then you can adjust so they all
  connect to the master and they all agree, what do you think?"

## What failed (receipts)
- **Live (21:45, TYNAN "groovininininin", no database seed, guest mode alongside FL):** beat_a locked at 140.8
  BPM, then wandered: 124, 130, 167.8, 83.1, 159.7, 118.5, 131.3. Second-half median 124.7, range
  118.3-159.6. Daniel: "its drifting".
- **Mechanism, read from beat_a.py:**
  - each beat snaps 50% toward the strongest onset within ±100 ms (PLL_PHASE 0.5);
  - the tempo may flip after 4 × 0.25 s of disagreement (SWITCH_AFTER, TEMPO_EVERY_S);
  - the period is pulled 10% toward the current guess every 0.25 s (line ~306).

  It is a note-chaser with a one-second memory.
- **Drift suite baseline** (`beatbench --suite drift`, 5 constant-tempo half-time cases with loud sub-bass on
  syncopated 16ths):

  | tracker | F | CMLt | Acc1 | bpm_spread | flips |
  |---|---|---|---|---|---|
  | aubio | .809 | .513 | .80 | .240 | 3.2 |
  | beat_a | .218 | .012 | .20 | .009 | 0.2 |

  beat_a holds steady on the WRONG grid (est 112 for 140, 171 for 128). Seeded at 140, it locks on the
  off-beat bass (F .000).

## The design every contestant implements (Daniel's, with Vandor's specifics)
1. **Grid hypotheses scored on ALL notes.** A hypothesis is a tempo, an anchor phase, and a subdivision family
   (straight 16ths, or triplets). Its score is how well every detected onset in the last few bars lands on its
   grid lines, weighted by onset strength. Off-grid onsets count against it. Onset times are refined below the
   frame size (peak interpolation).
2. **Parsimony.** The coarsest grid that explains the notes wins. A grid fine enough to fit anything must not.
3. **Many hypotheses at once, each with a confidence**, updated continuously.
4. **One master.** Hypotheses related by octave or subdivision (70 / 140 / 280; the 16th grid at 140 = the 8th
   grid at 70) are one grid at different levels, so they merge and vote together. The beat level is chosen by
   accent (kick and snare) and by the seed when there is one.
5. **Hysteresis.** The master changes only when a rival outscores it for several bars. Small, averaged
   corrections, never per-note snaps.
6. **Predict from the master grid.** Counting beats gives bar position, so emitting is_downbeat is encouraged
   but optional.

## Acceptance, fixed now (F is co-primary everywhere, per Heimdall's rule)
Run by Vandor, independently, with:
- `beatbench --suite drift --trackers aubio,a,<g>`
- `--suite all --per-cat 30 --seeded --seed 7`

A contestant ships only if ALL of these hold.

| suite | criterion |
|---|---|
| drift (5 cases) | mean F >= .85, mean CMLt >= .75, mean bpm_spread <= .02, mean tempo_flips <= 0.5 |
| synthetic (14 cases) | mean F >= .95 (beat_a .970), mean CMLt >= .85 (beat_a .910) |
| loops, seed 7, each of kick / tops / melodic, unseeded and seeded | F and CMLt each >= shipped beat_a minus .02; bpm_spread <= shipped beat_a's |
| speed | realtime_x_min >= 20 (live headroom) |
| contract | BB.check_tracker() == []; the licence firewall is green (stdlib + numpy + scipy, no relative imports) |
| honesty | causal only: no look-ahead past the audio fed so far; no constant copied from the bench (e.g. SYNC_BASS_16THS) |

If more than one passes, the best mean CMLt on loops wins, then F. If none passes, the record says so, and
beat_a stays shipped.

## Addendum, written before any contestant: shifting BPM and two volatility settings

Daniel, verbatim, mid-build:
- "mechanically not with agents parsing"
- "perhaps we could adjust bpm, and maybe have a higher and lower volitility setting that are smartly joined or
  parsed, the volatile one could get guesses from the lower volitility one, what do you think? have shifting bpm
  and low + high volatility heuristics"
- "feel free to fan out for research, go crazy / if you want to fan out for build to, feel free to do so, you can
  make yourself a team, try to use the ask verb to leverage deepseek subagents and tag team with Heimdall hisself"

**Readings:**
- The DETECTOR is mechanical at runtime: numpy maths, with no model in the loop.
- Building it may be a team.
- The two volatility settings map onto an Interacting Multiple Model (IMM) filter: a low-volatility (near
  constant tempo) model and a high-volatility (tempo moving) model, run together and mixed by a live regime
  probability. IMM's mixing step is literally "the volatile one gets guesses from the low-volatility one".

**New suite:** `beatbench --suite shift`, four 40 s cases with a sudden tempo STEP at 20 s:
- 128 -> 140;
- 140 -> 128 half-time with bass;
- 120 -> 150;
- 150 -> 120 seeded at 150.

The new metric, `relock_s`, is the seconds from the step until 8 consecutive beats hit again.

**Baselines, measured before registering:**

| tracker | F | CMLt | mean relock_s | never relocked |
|---|---|---|---|---|
| aubio | .747 | .631 | 6.29 | 1 of 4 |
| beat_a | .656 | .540 | 3.10 | 2 of 4 |

**Shift acceptance, added to the table above:**

| suite | criterion |
|---|---|
| shift (4 cases) | mean F >= .85, mean CMLt >= .75, mean relock_s <= 4.0, never_relocked = 0 |

The drift criteria (constant tempo, so it must HOLD) and the shift criteria (a real change, so it must FOLLOW)
pull in opposite directions. Passing both at once is the point of the two volatility settings.
