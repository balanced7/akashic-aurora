# Grid-tracker research: completeness critic over the five lanes (2026-10-22)

The final report of a research agent (Claude, web), lane `critic`, from the grid-tracker research workflow (run wf_4acc5ff4-38e). Each agent read the brief (grid-tracker-brief-2026-10-22.md) first. Persisted unedited per the full-fidelity rule.

---

**Completeness critique of the grid-tracker research, checked read-only against `E:\AI-Setup\arsenal\keylab\beatbench.py`**

**Bench facts the five reports missed (they change several verdicts)**
- **Shift-suite steps** (lines 227–230): 128→140 (+9%), 140→128 half-time (−9%), 120→150 (+25%), and 150→120 seeded at 150 (−20%).
- **How relock is timed:** `relock_s` runs from the step to the **first** beat of an 8-beat run, every beat within ±70 ms (lines 316, 406–410).
- **What F scores:** `feed()` events after 5 s, de-duplicated within 50 ms, keeping the last word (329–359). A wrong beat, once emitted, cannot be retracted.
- **`halftime_bass` has more than the brief says.** It also has hats (0.4) on every beat (line 167).
  - Its kick/snare skeleton is identical to `drums_70`: kick and snare alternate on 857 ms beats, with hats on the eighths.
  - Only two things differ: hat accent (1.0/0.7 against a flat 0.4) and the sub-bass. Yet one case is annotated at 70 and the other at 140.
- **`offbeat_hats_95`** puts loud hats (1.4) on the "and" (line 180).
- **Swing:** swing 0.33 lands at 0.665 of the beat, the triplet point (line 158).
- **The synthetic suite also has** `ramp_100_to_130` and `dnb_174_seeded_87` (the seed is off by an octave).
- **Patent US 8,889,976 is not a blocker.** It belongs to Honda (Nakadai, Otsuka, Okuno). Claim 1 requires matching against a musical score, and it shows as "Expired – Fee Related" ([Google Patents](https://patents.google.com/patent/US8889976B2/en)).

**(a) Decisions the research leaves open**
1. **What the IMM filter measures.** Options:
   - the grid scorer's (phase, period) peak (IMM lane, after Cemgil);
   - a per-beat timing residual from onsets snapped to grid lines (changepoint lane);
   - the nearest onset.

   The evidence favours the snapped residual. The scorer's leaky multi-bar window makes successive measurements correlated, so the filter becomes overconfident, and it also adds lag. The nearest onset is ruled out: half of the drift suite's beats have no kick or snare on them.
2. **Volatility architecture.** Options: a continuous IMM, a discrete bar-pointer model with a λ regime (multiagent lane), or IMM plus CUSUM/GLR change detection (changepoint lane). Favour IMM plus CUSUM. The bar-pointer model needs downbeats, which the skeleton makes optional, and at λ≈125 it freezes the octave.
3. **Large steps.** The 120→150 step is about 100 ms per beat. That aliases across the sixteenth grid (125 ms at 120 BPM). The changepoint lane's clip at ±2.5σ also caps the GLR's estimate of the new period at roughly 14 ms per beat.
   - These steps need a second path: re-induction from the tempo bank on alarm (IBT's "reset", 3.2 s).
   - No report sets the size threshold between following a step and re-inducing.
4. **Ramps.** Options: a third, mid-volatility model; a constant-acceleration state; or letting CUSUM re-fire. The changepoint lane ignores ramps, and a 100→130 ramp (about 1.8 ms per beat) would make CUSUM alarm repeatedly. Favour the third model.
5. **Parsimony and scoring form.** Options: IBT's signed linear score, Goto's pattern weights, Hainsworth's exp(−log₂d), or the MDL mixture with an ε floor. Favour the MDL mixture: the cost of an off-grid onset is bounded and the score is calibrated.
6. **Tempo-bank resolution.** About 700 tempi (grid lane) against 71 log-spaced states (Krebs). Favour a coarse log-spaced bank plus continuous refinement.
7. **Subdivision families.** Two families (straight, triplet) cover the bench, because the swing case sits on the triplet point.
8. **The seed.** It must be a decaying prior with no fixed octave, never a lock. Both `dnb_174_seeded_87` and the seeded 150→120 shift punish a lock.
9. **Emission lag for observed beats.** Emit at the grid line, or after confirmation? Nothing can be retracted, so this matters.

**(b) Contradictions**
- **When the regime may switch.** The IMM lane switches through Π every beat. The changepoint lane says μ alone is a poor alarm. The multiagent lane switches only at bar ends.
- **Onset timing noise.** The lanes assume 3.4 ms (IMM), 4 ms (changepoint, UNVERIFIED), at most 5 ms needed (onsets), 10 ms (grid), and 8–11 ms on real mixes. Every gate, threshold h and Q ratio scales with this figure, and nobody has measured it on the bench.
- **Grid lane's tie argument.** It omits the on-beat hats. On the bench, shifting the grid by two sixteenths does not tie.
- **The IMM lane's gate** (γ=9 on the steady model) rejects exactly the post-step measurements the shift suite needs.
- **CUSUM on steady-model innovations is contaminated.** IMM mixing feeds the volatile state into the steady model. The detector needs an unmixed reference predictor.
- **Window length.** The grid lane's 8 s window is longer than the 4 s relock limit.
- **Evidence against the switch itself.** The IMM lane cites Cemgil's Table 3, where the switch did not help.

**(c) The three highest risks for passing both suites**
1. **Choosing the beat level in half-time music.**
   - The brief's rule ("beat level from kick and snare accent") picks 70 on `halftime_bass`, because kick and snare sit one beat apart at 70. That gives F ≈ .67 on every drift case, below the .85 bar.
   - `drums_70` has the same skeleton and is annotated at 70.
   - Only three things separate the two cases: flat against alternating hat accent, a sixteenth-note tatum at 140, and a tempo prior. librosa's "pseudo-log-normal" tempo prior ([docs](https://librosa.org/doc/0.11.0/generated/librosa.feature.tempo.html); `start_bpm` = 120 in their example; ISC licence, my reading, UNVERIFIED) favours 140. It may cost `drums_70`, but a mean over 14 synthetic cases can absorb one .67.
2. **Period and phase under syncopation.**
   - beat_a's wrong locks are not octave errors. 112 BPM is a 5-sixteenth period (535.7 ms = 5×107.1) and 171 BPM is a 3-sixteenth period (351.6 ms = 3×117.2). Those match the bass's own gaps of 3, 4, 3, 2 and 4 sixteenths.
   - So the beat must be 2ⁿ or 3·2ⁿ tatums. But 120→150 is a genuine 5:4 step, so rivals at non-family ratios may enter only through the alarm path.
   - **Phase cue:** high-band flux fixes the drift suite (hats on the beat) and breaks `offbeat_hats_95` (hats on the "and"). Low-band flux cannot work either, because kick and sub-bass share 30–200 Hz. The cue has to be specific to kick and snare, for example onsets that rise together across several bands.
3. **Timing of hold against follow.**
   - Within 4 s there are 8.5 beats at 128 BPM, and the 8-beat run has to start by then.
   - "Several bars" of hysteresis (3 bars is 5.1 s at 140) already exceeds that. Tempo steps must bypass the family hysteresis, and the scorer's memory must be cut on alarm.
   - The threshold h should be the smallest that gives zero false alarms on the drift suite, then checked against re-fires on the ramp case.

**(d) What a builder needs that no report covers**
- **Cold start:** the induction policy for the first 5 s, and for short real loops. The tops and melodic loops have no kick or snare, so the accent rule needs a fallback.
- **The accent feature itself,** with per-band lag calibration built into it.
- **Glue between the layers:** how a tempo-bank peak sets the IMM's initial state and R; re-initialising on a family change; how an alarm resets the scorer.
- **Silence and breakdowns:** `predict()` keeps the grid going; the regime probabilities must not drift meanwhile.
- **Downbeat:** decide to return `None`, or specify how bar position is counted.
- **A local replay of the real TYNAN failure,** never committed, since every suite is synthetic.
- **A guard against fitting the bench:** every bench fact above is for analysis only and must not become a constant, per the contract.
