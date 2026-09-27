# ground:quantization-feel

_Verbatim agent return, workflow wf_fc6a68ac-233, 2026-09-27._

I have everything. Writing findings.

## Corrections to the brief, first — two of its premises are wrong

**1. "There is no onset analysis, no beat tracking, no quantization anywhere in the tree" is false.** There is a complete, heavily-documented live-transcription pipeline at `E:\AI-Setup\arsenal\web\piano\score\` (19 modules, ~400 KB) plus a plan/amendment corpus at `E:\AI-Setup\research\in-flight\live-sheet-music-2026-09-14\` (~360 KB across 7 docs). The relevant modules:

| file | stage | what it does |
|---|---|---|
| `score/onsets.js` | T1 | chord (40 ms) / near-chord (60 ms, 7 semitones) / roll / run / grace grouping, `salienceOf` at `:47-51` |
| `score/beat.js` | T2 | causal beat tracker, IOI induction, ≤24 competing agents, steadiness bands, `bpmShown`, tactus conversion, ×2/÷2/2↔3 family |
| `score/meter.js` | T2.4 | tatum-template meter scoring, bar phase, pickups, **the triplet/straight "feel" chip** at `:26-33` |
| `score/quantize.js` | T3 | the per-beat division decision — this is my lens |
| `score/measures.js` | T4 | rhythm spelling, tuplet brackets, ties, beams |
| `score/musicxml.js` `midi.js` `engrave.js` `export.js` `ribbon.js` | T5+ | notation output |

There is also **audio** onset detection at `arsenal/web/piano/listen/dsp.js:141-281` (spectral flux, 3 bands, 172 Hz frame rate). `tempomap.js`/`groove.js` are the *jam playback* organ — a separate thing from `score/`, and the brief conflated them.

**Consequence: the ask is largely already built.** The work is extension and instrumentation, not a new organ.

**2. The "120 ms and 160 ms coexisting" finding does not survive measurement.** Re-measured on `state/arsenal/performance/20260927-171534-085f6ee9/roll.txt`:

- 4633 notes (brief said 4631); note-onset span **13.18 min**, not 11.5 (`meta dur_ms=978963` = 16.3 min counts notes held to session end).
- raw note IOI median **126 ms** ✓ (brief: 130).
- "1806 gaps of ~0 ms" → only **108 are exactly 0**. 1637 are ≤20 ms, **1827 are ≤30 ms**, 1930 ≤40 ms. So 1806 was a ≤~28 ms count. Relevant number: the 40 ms chord window absorbs **41.7%** of the raw note stream; the quantizer sees 2716 groups, not 4633 notes.
- The 120/160 "two peaks" are **bin-edge artifacts plus tempo sections**. Globally the group-IOI distribution is one broad hump peaking at 148–171 ms (8 ms bins: 52, 59, 92, 98, **127, 128**, 108, 110, 110, 80, 54…). A 2-component GMM on log-IOI over 260–300 s prefers **one** mode (BIC −98.5 vs −83.2). Where 2 modes are found (680–760 s) the ratio is ≈1.9 — an 8th/16th octave pair, not 3-vs-4. Windowed medians walk 340 → 160 → 200 → 170 → 260 → 350 → 150 ms: **the take is four tempo sections**, and the global histogram is their superposition.
- Segmented at rests >1.5 s: **4 segments, 86.9 / 101.3 / 90.7 / 113.6 bpm.**

So "two subdivisions of one pulse" is not what his strange rhythmic stuff is. What it actually is, below.

Method note: I ported `quantize.js` to Python (`qlib.py`) and **validated the port against the shipped JS** — `node` ran `divideBeat` from `arsenal/web/piano/score/quantize.js` on 8 real beats and agreed with my port **8/8**, costs matching to 4 decimals (e.g. seg2 beat 38: JS 3.7066, port 3.707). Beat times are a documented **stand-in** (`librosa.beat.beat_track` on a salience-weighted symbolic onset envelope, 172 Hz frames); I did not design a tracker, per the lens.

---

## Q1 — The subdivision decision rule

**It exists and is already formal.** `quantize.js:13-14`:

```
C(d) = Σ ((f − k/d)·P)² / 2σ²  +  λ[d]  +  0.8·[d ≠ previous non-empty beat]
                               +  0.8·[d ≠ same beat one bar back]  +  6·collisions
k = round(f·d) clamped to 0..d−1
```

λ tables at `:48-53`, alphabet {1,2,3,4,6} (+8 optional): straight `1:0, 2:0.5, 4:1.5, 6:1.75, 3:2.0`; triplet `1:0, 3:0.5, 6:1.5, 2:1.75, 4:2.0`; compound `1:0, 3:0.5, 6:1.5, 2:1.75`. Params at `:38-45`.

**What stops it flapping — five mechanisms, all present:**
1. **Adaptive σ** — EMA (w=0.05) of squared residuals, clamped 15–60 ms (`:38`, `:196-197`). Measured per-beat σ on the real take: min 15.0, median 21–28, max 40–48.
2. **Continuity 0.8** against the previous non-empty beat.
3. **Bar-back 0.8** against the same beat one bar earlier — a metrical, not merely temporal, prior.
4. **Viterbi clean pass** (`cleanDivisions`, `:223`), run twice, bar-back prior refreshed from the previous pass.
5. **The d=6 gate** (`d6MinGroups: 5`, `:45`): d=6 only competes on beats with ≥5 groups, because the d=6 grid contains every d=3 slot at a lower λ, so ungated it priced triplets at λ6 and hoovered up jittered 16ths.

Measured flap rate on real data (680–760 s, 150 beats): live **0.094 division changes/beat**, clean **0.054**. Not flapping.

**The one thing that is not formalised: which metrical level is "the beat."** This dominates everything else. Same 80 s of notes, three tactus choices:

| tactus | bpm | clean divisions | loose | σ end | \|dev\| median |
|---|---|---|---|---|---|
| ×1 | 230 | `{1:46, 2:446, 3:4, 4:50}` | 0.0% | 15.0 | 4.7 ms |
| ×2 | 114 | `{2:30, 3:1, 4:288}` | 0.0% | 23.4 | 8.9 ms |
| ×4 | 56 | `{4:26, 6:49}` | **33%** | **60.0** (saturated) | **39.4 ms** |

All three are notationally correct. Only the first two are readable. **Loose-rate + σ-saturation is a reliable *invalidity* detector for a too-slow tactus but is NOT a level chooser** — it monotonically favours the finest level, because a beat with one onset can never go loose. Adding a d=1-share penalty fixes it: `score = loose_rate + 0.5·[σ≥59] + d1_share` picks ×2 (87/101/91/114 bpm, musically right) on all 4 segments, and every alternative scores worse by 3–100×. That is a concrete, cheap addition, and it is currently **absent**: `quantize.js` produces no signal that flows back to `beat.js`'s tactus/family machinery.

---

## Q2 — Genuine triplet vs swung pair vs sloppy straight

**First, the confusion is narrower than stated.** A genuine triplet with all three notes sounding is *not* ambiguous with a swung pair — it has three onsets, and the 3-grid fits measurably better. On the real take I found beats where the 3-grid rms error is **6.3–13 ms** against **34–58 ms** on the 4-grid: a 3–7× advantage. That is not an ambiguity, it is a signal.

The real ambiguity is **a triplet with the middle note absent** (onsets at 0 and 2/3) versus a swung pair. Those are timestamp-identical. The discriminator must be phrase-level, and the evidence that separates them is **whether the 1/3 position is occupied anywhere in the phrase.**

**Formal rule.** Over a phrase window, for beats the quantizer read as d=2 with onsets on slots 0 and 1, let `x` = the offbeat's measured beat fraction. Let `E₃` = the count of beats in the window with an onset within tol (0.05 beat) of 1/3, and `N₃` = beats whose onsets fit the 3-grid better than the 4-grid.

```
σ_x > 0.06 beat                    -> SLOPPY / free. Report no subdivision; mark loose.
|median(x) − 0.5| < 0.03 beat       -> STRAIGHT.
median(x) > 0.5 + 0.03 and E₃ ≥ 3   -> TRIPLET (notate 3-grid, rest the empty 1/3 slot).
median(x) > 0.5 + 0.03 and E₃ < 3   -> SWUNG (notate straight, report the ratio).
```

The `σ_x` gate is what makes this robust, and it must be computed on beats **conditioned on the quantizer's own d=2 reading**, not on raw 2-onset beats. That conditioning matters enormously: unconditioned, σ_x measured 0.024–0.140 beat and the rule said "sloppy" everywhere; conditioned, σ_x is **0.018–0.038 beat (9–26 ms)** and the rule discriminates. Unconditioned samples mix 16th-position offbeats (x≈0.25/0.75) into what is supposed to be a pair statistic.

On this take: `E₃` (onsets near 1/3) is outnumbered by onsets near 1/4 in every passage — 13 vs 66, 8 vs 42, 18 vs 60, 3 vs 11 — so the correct reading is straight-with-16ths, and the rule says so.

**How the shipped pipeline actually performs.** I defined a clean triplet as ≥3 onsets with 3-grid rms < 0.03·P and 4-grid rms > 2× that, then scanned the whole take (1009 beats at the chosen tactus). **14 clean triplets.** Results:

- **live causal pass: 13/14**
- **clean Viterbi pass as `index.js:346` actually calls it: 14/14** (it recovers the one the live pass lost)
- clean pass at `cleanDivisions`' own **σ default: 6/14**

Two genuine triplet *runs* exist and are correctly read: seg2 beats 38–48 and seg3 beats 85–87 and 305–307. **This is his "strange rhythmic stuff": isolated triplet beats inside predominantly-16th playing at ~90–114 bpm.** The pipeline gets them.

**I must retract an intermediate finding of my own.** My harness initially omitted `sigma` when calling `cleanDivisions`, reproducing its signature default (`sigma = QUANT_PARAMS.sigma0Ms` = 40 ms, `quantize.js:223`), and I concluded the Viterbi pass destroyed 7 of 13 detected triplets. It does not — `index.js:346` passes `sigma: q.sigma()`. The real finding is a **latent trap, not a live bug**: the default is 40 ms, and at 40 ms triplet recall drops 14/14 → 6/14 (seg3: 17 d=3 beats → 1). Any other caller that omits the argument silently loses 60% of triplets. `bench.js` and the lab pages are the exposure.

**Two genuine residual fragilities:**

- **σ in the clean pass is one end-of-segment snapshot.** Per-beat σ within a segment spans 2.7–3.2× (seg2: 15.0 → 47.9, snapshot 31.7), so the fit term is mis-weighted by up to **10×** on some beats. The live pass stores its own per-beat σ (`decide()` returns it) and it is thrown away at the segment boundary; only `sigma_ms` per segment survives to output (`index.js:614`).
- **The margin is thin and nobody looks at it.** `divideBeat` computes `runnerUp` at `quantize.js:143` — and **nothing in the tree ever reads it** (grep across `arsenal/web/piano/` and `tests/`: the only other hits are an unrelated local in `piano_spell.test.mjs`). seg2 beat 38's margin was **−0.170** on a cost scale where the change penalties alone are 1.6. A reading decided by 0.17 should be labelled ambiguous, not rendered as fact.

Closed-form for the d=3 entry barrier, for calibration. For a *perfect* triplet, d=3 loses to d=4 once
```
σ > (P/12) / sqrt(λ₃ − λ₄ + penalties) = (P/12)/sqrt(2.1) = 0.0575·P    (entering: both 0.8s paid)
σ > (P/12) / sqrt(0.5)                 = 0.1179·P                        (incumbent: no penalty)
```
At P=528 ms that is 30.4 ms to enter, 62.2 ms to hold — and σ clamps at 60. **The d=3 basin has a high entry barrier and an essentially unbounded retention basin.** Good anti-flap design; the cost is that the *first* triplet of a run is the one at risk. Verified empirically: seg2 beat 38 (the run's entry beat) is the single beat the live pass missed. At the σ=15 floor a triplet can drift ±35 ms (6.6% of the beat) and still read d=3.

---

## Q3 — Swing ratio, continuous

**Definition.** For a beat read d=2 with onsets on slots 0 and 1, `x` = the offbeat's beat fraction; swing ratio `r = x/(1−x)` (long:short). r=1.00 straight, 1.50 light swing, 2.00 triplet swing. Report as a **distribution, not a number**: median r, bootstrap 95% CI on the median, `σ_x` in ms, and n.

Measured, per segment at the chosen tactus:

| seg | bpm | n pairs | median x | r | 95% CI | offset | σ_x |
|---|---|---|---|---|---|---|---|
| 0 | 86.9 | 21 | 0.5076 | 1.033 | [0.982, 1.081] | +5.6 ms | 20.2 ms |
| 2 | 90.7 | 36 | 0.5031 | 1.031 | [0.989, 1.088] | +5.0 ms | 26.3 ms |
| 3 | 113.6 | 18 | 0.5055 | 1.055 | [0.994, 1.093] | +7.1 ms | 11.7 ms |

Pooled, n=77: median x = 0.5092, **r = 1.0376**, CI **[1.0068, 1.0806]**, offbeat median **+6.35 ms late**, Wilcoxon signed-rank against x=0.5 **p = 6.2×10⁻³**.

**But that headline number is contaminated, and the contamination is the most important methodological finding in this whole analysis.** The mean deviation on **slot 0 — the beat itself** — is significantly positive in every segment: +6.28, +4.07, +3.59, +3.15 ms (Wilcoxon p = 2×10⁻²⁵, 4×10⁻¹¹, 3×10⁻⁴¹, 3×10⁻²⁵). A player cannot be systematically late on the very onsets that define the grid. **The grid is early, by 3–6 ms.** Any deviation layer that does not remove this reports tracker bias as the drummer's feel.

**After re-centring slot 0 to zero per segment**, the feel signature is coherent and replicates across all four independent segments at four different tempi:

| position | seg 0 | seg 1 | seg 2 | seg 3 |
|---|---|---|---|---|
| d=2 slot 1 (8th offbeat) | +1.11 | — | +0.96 | +4.18 |
| d=4 slot 1 (1st 16th) | **−6.03** | **−6.15** | **−5.99** | **−4.67** |
| d=4 slot 2 (the 8th) | −2.66 | −4.59 | −0.96 | +0.44 |
| d=4 slot 3 (3rd 16th) | −8.13 | −4.12 | +3.22 | −2.60 |

**His 8th-note offbeats sit slightly late (+1 to +4 ms); his off-16ths are consistently rushed by 5–6 ms.** Four-for-four replication on slot 1 of d=4. That is a real, specific, reportable thing about his playing — the kind of statement a drummer can act on — and it is invisible without the re-centring step.

**How to report it to a drummer.** Not "swing = 1.0376". Report: *"Straight eighths (ratio 1.04, 95% CI 1.01–1.08). Your off-16ths are early by 5–6 ms, consistently, at every tempo in this take."* Ratio plus CI plus the per-slot table. And the systematic/random breakdown: `|mean| / sd` per slot was 0.003–0.55 — i.e. **the systematic part is at most half the random part.** Saying "you swing" when systematic/random < 1 is overclaiming, and the ratio should be shown greyed or withheld below a threshold.

---

## Q4 — Syncopation

**Nothing in the tree represents it.** No metrical-hierarchy weight exists anywhere: grep across `score/*.js` for metrical weight returns only `beat.js`'s accent terms (`accentBass 0.7`, `accentHarm 1.2`, `accentPedal 0.8`, `beat.js:84`) — which run the *opposite* direction (accents → meter template), and `marks.js` `accentMarks`, which is velocity-based dynamic accent, not metrical. `measures.js:220` mentions "the syncopated quarter" but that is a *rhythm-spelling* rule (which written value is legal across a beat line), not a measure.

**Published measures, compared.** I implemented three and ran them on 38 real bars (680–760 s, bar phase chosen by accent):

| measure | mean | sd | range | corr. with LHL |
|---|---|---|---|---|
| **Longuet-Higgins & Lee 1984** (LHL) | 2.29 | 1.79 | 0–6 (26% of bars zero) | — |
| **Keith 1991** | 15.61 | 3.82 | 7–22 | **−0.118** |
| **WNBD** (Gómez/Melvin/Rappaport/Toussaint 2005) | 0.302 | 0.080 | 0.225–0.562 | **+0.596** |

- **LHL** assigns metrical weights by level (4/4 at 16ths: bar 0, half −1, beats −2, 8ths −3, 16ths −4) and scores each note→following-rest pair where the rest outranks the note, summing `W(rest) − W(note)`. It is the measure used in the groove/embodiment literature (Witek et al. 2014, inverted-U of syncopation vs pleasurable urge to move). **It is the right primary choice**, for one decisive reason: its score is *attributable to a specific note*. You can point at the note on the staff and say "this is the syncopation, 3 units." No other measure here can do that.
- **Keith 1991** (0–3 per note: none / hesitation / anticipation / syncopation) is **unnormalised, so on real polyphonic bars it is a note-density proxy** — corr −0.118 with LHL, essentially uncorrelated. Concretely: bar 5 with 12 of 16 positions filled scores Keith 19, LHL 4; bar 37 with 4 positions `[1,4,7,10]` scores Keith 8, LHL 5. LHL correctly ranks the sparse displaced figure as more syncopated than the dense run; Keith inverts it. **Do not use it.**
- **WNBD** (mean normalised note-to-nearest-beat distance, doubled for notes crossing a beat) is the best agreement with LHL (+0.596), is bounded and continuous, and is useful as a **second, gradual number** — it degrades smoothly where LHL is integer-stepped. But it only knows the beat, not the bar, so it cannot distinguish a displaced note on beat 4 from one on beat 1.
- **Pressing 1997** (cognitive complexity) and **Toussaint 2002** (metrical complexity) are alternatives in the same family as LHL, both hierarchy-based; Pressing's weights are psychologically motivated rather than derived from the metrical tree. Neither adds per-note attribution over LHL.
- **Sioros & Guedes 2011** is the one that matters for the gap below.

**The gap, and it is serious for a drummer.** LHL, Keith, WNBD are all defined on a **monophonic binary onset grid**. My implementation collapsed polyphony to "positions occupied" — so a left-hand bass on beat 1 plus a right-hand offbeat scores the same as a bar with nothing on 1. For a drummer that is exactly wrong: **syncopation is per-limb.** Kick on 1 with a snare displaced is not the same event as nothing on 1. **Sioros & Guedes (2011)** is the published extension to polyphonic and velocity-weighted streams, and it is the right target. The good news: `score/hands.js` already assigns voices/streams and `onsets.js` already carries velocity and `salienceOf`, so per-stream LHL is computable from what exists.

**Requirement LHL imposes: syncopation needs committed bar phase, not just beats.** `meter.js inferPhase` and `index.js`'s phase priority (jam → song → "This is 1" → inferred) already supply it. Syncopation output must carry the phase's provenance, because a phase error of one beat rewrites every syncopation score in the bar.

---

## Q5 — The central question: the representation that keeps both layers

**The deviation is already computed and thrown away.** `quantize.js:106`:

```js
const k = clamp(Math.round(it.f * d), 0, d - 1), e = (it.f - k / d) * P;
fit += e * e / (2 * sigma * sigma);
```

`e` is the signed per-note deviation in ms. It is summed into `fit`, recomputed at `:195` for the σ EMA, and **never retained**. `decide()`'s return (`:199-201`) and `cleanDivisions`' output (`:253`) carry `d`, `ks`, `pos`, `div`, `cost`, `loose`, `P` — no deviation. Downstream there is nothing: grep for residual/deviation/microtiming across `score/*.js` returns only comments.

**The cost of the fix is near zero, because the inputs already survive to output.** `index.js:429` computes `beats_ms` — the tactus beat times of each bar on the build's grid — and exports it (`:615`); notes carry `t_ms`; pieces carry `pos` in ticks. So `dev_ms = note.t_ms − (beats_ms[beat] + pos_within_beat/beatTicks · P)` is computable **today** from data already in the score output. One `push` in `fitOf`, one field in two return objects.

**The two-file split that exists but does not join.** `midi.js:5-11` already writes `performance.mid` (SMF type 0, PPQ 500, 1 tick = 1 ms, every logged on/off at its true time) *and* `quantized.mid` (SMF type 1, PPQ 480, notes on the grid). That is already a two-layer representation — but as two **files**, with **no link between note *i* in one and slot *k* in the other.** The missing artifact is the join. `index.js` already has stable `note.id`, so the join table is `note.id → {bar, pos, dev_ms}`.

**Proposed schema.** Per placed onset, alongside the existing `{bar, pos, d}`:

```
dev: {
  ms:    signed ms, onset minus notated grid time, AFTER grid-bias removal
  beat:  ms / P                  signed fraction of the local beat
  grid:  ms / (P/d)              fraction of the grid STEP it sits on; |grid| > 0.5
                                 means it was nearer another slot than its own
  P:     the local beat period used for this beat
  sigma: the per-beat sigma the decision was made at   (exists, discarded)
  bias:  the grid bias removed, so the raw number is recoverable
  margin: cost(runner-up) - cost(chosen)                (exists at :143, read by nobody)
}
```

Four design rules the measurements force:

1. **`bias` is mandatory, not optional.** Slot-0 mean deviation is +3.1 to +6.3 ms with p < 10⁻¹¹ in every segment. Ship without bias removal and the system tells a drummer he plays 5 ms late when the tracker is 5 ms early. Bias is estimated per segment as the mean slot-0 deviation and stored so the raw value is recoverable.
2. **`grid` (not `ms`) is the honest primary.** `dev.ms` is not comparable across tempi; 10 ms at 87 bpm and 10 ms at 230 bpm are different musical facts. Measured take-wide at the chosen tactus: |dev| median 8.7 ms, p90 50.8, p99 79.5, signed mean +2.56, n=2629; 27.3% exceed 10 ms, 17.0% exceed 20 ms, 10.9% exceed 30 ms, 3.9% exceed 50 ms.
3. **`margin` must be surfaced.** It is already computed and discarded. A reading decided by 0.17 on a scale where penalties are 1.6 is a coin-flip presented as a fact. Beats below a margin threshold get drawn as ambiguous, with the runner-up reading available — not silently resolved.
4. **Aggregate to a per-(segment, d, slot) feel profile**, and per *stream* once `hands.js` voices are joined in — mean, sd, n, and `|mean|/sd`. That profile is the table in Q3 above, and it is the thing that actually told me something about his playing.

**Surfacing, three layers.** (a) The score, notated positions, unchanged — a drummer must be able to read it. (b) A **deviation ribbon** under the staff: one signed tick per note against a zero line, ms scale, early left / late right. `ribbon.js` already draws proportional time (`:372` interpolates a position against real `t`), so it is the natural host rather than a new surface. (c) A **feel card** per section: tempo, swing ratio with CI, the per-slot mean/sd table, LHL per bar, and `|mean|/sd` so the drummer can see when a claim is weaker than the noise.

**Retirement rule** (house rule: a capability without one is debt). The deviation layer is **derived, never an atom.** It is recomputed from `events.jsonl` plus the committed beat grid, and every `dev` record carries the grid's identity — segment id, the build `rev` that `index.js` already maintains (`:430` `res.rev`), and a hash of `beats_ms`. When the grid changes — a rebuild, a ×2 family press, a tactus or phase change — every deviation stamped with the old grid is **invalidated with it**, not migrated. A `dev` number without that stamp is retired on sight. And deviations never enter MusicXML as notated content; they live in the sidecar join table beside `performance.mid` and `quantized.mid`.

---

## Q6 — The real finding, worked through

Loaded and run, not reasoned about. **The premise does not hold**: 120 ms and 160 ms are not two subdivisions of one pulse. Evidence, in order: (i) the global group-IOI distribution is one broad hump peaking at 148–171 ms, and the "two peaks" appear only under 20 ms bins whose edges cut the hump — medians of 126 and 158 from bins 110–135 and 150–175 are what a unimodal distribution centred at ~145 produces, giving the spurious ratio 1.24–1.30 seen in all 9 windows (neither 4:3 = 1.333 nor 3:2 = 1.5); (ii) a 2-component GMM on log-IOI prefers **one** mode over 260–300 s (BIC −98.5 vs −83.2); (iii) where two modes do appear (680–760 s) the ratio is ≈1.9, an 8th/16th octave pair; (iv) 30 s windowed medians walk 340 → 160 → 200 → 170 → 260 → 350 → 150 ms. It is **four tempo sections**, and the global histogram is their superposition.

**What the design outputs for the take** (4 segments, tactus chosen by `loose + 0.5·[σ saturated] + d1_share`, straight λ table, `cleanDivisions` called as `index.js:346` does):

| seg | window | tempo | beats | divisions (clean) | loose | \|dev\| med / p90 | swing |
|---|---|---|---|---|---|---|---|
| 0 | 132–248 s | 86.9 bpm | 166 | `{1:1, 2:32, 3:3, 4:130}` | 0.6% | 7.2 / 39.5 ms | r=1.033 [0.982,1.081] |
| 1 | 250–309 s | 101.3 bpm | 95 | `{1:2, 2:6, 3:2, 4:83, 6:2}` | 1.1% | 9.3 / 35.6 ms | n too small |
| 2 | 318–607 s | 90.7 bpm | 429 | `{1:1, 2:51, 3:14, 4:352, 6:11}` | 0.5% | 9.1 / 56.4 ms | r=1.031 [0.989,1.088] |
| 3 | 614–791 s | 113.6 bpm | 319 | `{2:30, 3:17, 4:272}` | 0.0% | 8.9 / 50.6 ms | r=1.055 [0.994,1.093] |

**Is it right? Substantially yes, with one caveat.** Four tempo sections at 87–114 bpm, predominantly 16ths with 8ths, **36 beats read as triplets**, ~0.5% loose, deviations median 8.7 ms. The two genuine triplet runs are found: seg2 beats 38–48 and seg3 beats 85–87 / 305–307, with 3-grid rms 6.3–13 ms against 4-grid 34–58 ms. **All 14 clean triplets in the take are caught** as the pipeline is wired. His "strange rhythmic stuff" is isolated triplet beats and short triplet runs inside 16th-note playing at ~90–114 bpm — and the shipped quantizer reads them correctly.

The caveat: the tactus choice is not made by anything in the codebase, and it is the single largest lever. It changes 230 bpm/8ths into 114 bpm/16ths into an unreadable 56 bpm/33%-loose mess, from the same notes.

**One thing worth flagging as spurious.** At 480–560 s, three beats read d=3 whose own deviations are +41/−70, +74/−41, +22/−66 ms. Those are not triplets — they are two notes ~73 ms apart near the half-beat that got spread across the 3-grid rather than colliding on one slot. `collision: 6` (`:39`) is large enough that on some beats the cheapest escape is a finer or different division. A `margin` and a max-|dev| sanity gate on any tuplet bracket would catch these; as it stands they would be **engraved as triplets** in the score with 70 ms errors inside them. That is the failure mode most likely to make him say the notation is lying.

---

## What I did not verify

- I did not run the JS test suite (`tests/score_quantize.test.mjs`, `score_beat.test.mjs`, `score_fixtures.test.mjs` exist; `node` is v24.14.1). I validated my port against the shipped `divideBeat` on 8 real cases (8/8 agreement) but did not validate `cleanDivisions` or `createLiveQuantizer` against the JS.
- `beat.js` (43 KB) and `meter.js` I read only the headers of — per the lens, beat times were given to me. **My beat grid is a librosa stand-in, not `beat.js`.** Every tempo, tactus, and deviation number above inherits its bias; the slot-0 +3-to-6 ms bias is very likely an artifact of the stand-in, and the numbers must be re-derived against `beat.js` before any of them is quoted to Daniel as a fact about his playing. The *structure* of the findings (bias exists, must be removed, deviation is discarded, margin is unread, tactus is unchosen) does not depend on which tracker supplied the grid.
- Bar phase for syncopation came from a max-accent heuristic of my own, not `meter.js inferPhase`.
- I did not open the plan corpus (`plan-amendments.md` 97 KB, `transcription.md` 60 KB, `tempo-meter.md` 48 KB, `critic.md` 39 KB, `ls1-rulings.md`). **Some of what I recommend may already be specified or already ruled on there** — in particular whether the deviation layer was designed and deferred. That corpus should be read before any of this is treated as new.
- I analysed one session of 69. Segment-level replication (4 segments, 4 tempi) is within that one take.
- No claim checked about madmom; not needed — nothing I propose requires an install beyond numpy/scipy/librosa, all present.

## Files

- `E:\AI-Setup\arsenal\web\piano\score\quantize.js` — the cost function `:13-14`, params `:38-45`, λ tables `:48-53`, `fitOf` and the discarded residual `:104-115` (`:106`), `divideBeat` and the unread `runnerUp` `:126-143`, the loose rule `:142`, `createLiveQuantizer` `:178-210` (σ EMA `:195-197`), `cleanDivisions` and its σ-40 default `:223`
- `E:\AI-Setup\arsenal\web\piano\score\index.js` — the correct call `:346`, `beats_ms` `:427-430`, export `:614-615`
- `E:\AI-Setup\arsenal\web\piano\score\onsets.js` — grouping params `:31-37`, `salienceOf` `:47-51`
- `E:\AI-Setup\arsenal\web\piano\score\beat.js`, `meter.js`, `measures.js`, `midi.js` (`:5-11` the two-file split), `ribbon.js` (`:372`), `hands.js`
- `E:\AI-Setup\research\in-flight\live-sheet-music-2026-09-14\` — the 7-doc plan corpus, unread
- My harness (scratch, disposable): `C:\Users\L5\AppData\Local\Temp\claude\E--\a90a987a-4b74-4e3e-9a06-cad82f47b6b7\scratchpad\qlib.py` (validated port + stand-in grid), `t1.py`–`t11.py` (the experiments above), `check.mjs` (the JS cross-validation)