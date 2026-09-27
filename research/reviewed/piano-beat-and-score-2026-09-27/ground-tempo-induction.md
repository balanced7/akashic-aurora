# ground:tempo-induction

_Verbatim agent return, workflow wf_fc6a68ac-233, 2026-09-27._

Findings complete. Here is my report.

---

# Lens: tempo and beat induction from symbolic onsets

## 0. The task's premise is wrong, and the correction is the most important thing I found

The computed task states: *"NOTHING INFERS a tempo from what the human plays. There is no onset analysis, no beat tracking, no quantization anywhere in the tree. Verify this yourself rather than trusting it."*

I verified it. It is false. There is a complete, tested, causal multi-agent beat tracker in the tree, plus a 48 KB design doc on precisely this lens, plus an end-to-end pipeline to MusicXML.

| What | Where | Evidence |
|---|---|---|
| Causal beat/BPM/steadiness tracker | `E:\AI-Setup\arsenal\web\piano\score\beat.js` (43,828 bytes, 2026-09-15) | BeatRoot architecture: IOI induction, up to 24 competing agents, lag-2 settled beats, tatum meter. Contract in the 66-line header; `BEAT_PARAMS` at `beat.js:69-87`; `createBeatTracker` at `beat.js:132`; `trackEvents` replay entry at `beat.js:669` |
| Onset grouping + salience | `arsenal\web\piano\score\onsets.js` | 40 ms chord collapse, near-chord across hands, rolled chord, broken-chord run, grace candidate. `salienceOf` at `onsets.js:46-50` |
| Quantizer | `arsenal\web\piano\score\quantize.js` | `createLiveQuantizer` at `quantize.js:180`, Viterbi `cleanDivisions` |
| Research lane on this exact question | `research\in-flight\live-sheet-music-2026-09-14\tempo-meter.md` (47,877 bytes) | 10 sections: survey of PM2S/BeatRoot/met-align/Temperley/PLP, a held-out synthetic benchmark, and a measured table on 11 of Daniel's own earlier sessions (`tempo-meter.md:224-245`) |
| Pre-registered receipts, green | `tests\score_beat.test.mjs` | I ran it: **133 passed, 0 failed.** Receipts LR2a-g, LR3a, LS1-level |
| End-to-end to sheet music | `arsenal\score_cli.mjs` | `events.jsonl` → `take.musicxml`, `performance.mid`, `quantized.mid` |

So the question is not "how do we build this." It is "we built it; here is what it measures on your playing, and here is the one thing still missing."

**What I did not verify:** I did not read all 666 lines of `beat.js` (I read the contract header, params, ladder, sample construction, `trackEvents`). I accepted the task's claims about `groove.js` and `tempomap.js` without reading them. I did not check for `madmom` — it is moot, because none of the shipped path is Python.

---

## 5. THE MEASUREMENT (answering step 5 first, since it is the centrepiece)

Session `20260927-171534-085f6ee9`. Code: `C:\Users\L5\AppData\Local\Temp\claude\E--\a90a987a-4b74-4e3e-9a06-cad82f47b6b7\scratchpad\tempo_probe.py`, `run_beat.mjs`, `phase_probe.py`.

### 5a. Corrections to the stated session facts

| Stated in task | Measured |
|---|---|
| 11.5 min | **16.3 min** (`dur_ms` 979,000) |
| 4,631 notes | 4,633 |
| one continuous take | **No.** 104.7 s of silence from t=0.3 s to t=105.0 s; playing is ~14 min; 120 s (12%) sits in gaps > 2 s |
| median inter-onset 130 ms | 126 ms |
| 1,806 gaps of ~0 ms | Exactly 0 ms: **108**. ≤1 ms: 176. ≤30 ms: **1,827**. The 1,806 figure is the ≤30 ms population — a chord *window*, not near-zero |
| non-zero gaps cluster at 120 and 160 | **One broad mode, not two peaks.** 150-160 ms is the peak (154); 120-130 is a shoulder (74). Bins 130→190 all sit at 111-154 |

### 5b. Does a clear pulse emerge? Globally, **no** — and that is the finding

Salience-weighted onset train, 10 ms frames, whole take, FFT autocorrelation:

```
max r = 0.0344 at lag 660 ms (90.9 bpm)
top 8 peaks: 660, 330, 820, 1990, 790, 2860, 1800, 1850 ms
        r  = .0344 .0340 .0316 .0313 .0309 .0303 .0300 .0295
```

A 9:1 range of candidate lags inside a 14% range of correlation. `argmax` still returns a confident winner. **This is the silent failure, quantified: not a wrong answer, a non-answer delivered as an answer.**

Same statistic in 12 s windows: **median peak r = 0.154**, p10 0.106, p90 0.219 — 4.5× the global value. Winning lag median 600 ms, IQR 360-905 ms.

Log-period induction over the whole take (the in-house method, `tempo-meter.md:128-133`) returns four competing levels at once:

```
P = 713.5 ms   84.1 bpm   2.80x mean
P = 782.6 ms   76.7 bpm   2.77x mean
P = 540.8 ms  111.0 bpm   2.33x mean
P = 414.6 ms  144.7 bpm   1.29x mean
periodicity strength (best/mean) = 2.80   -> "free" by the 6.7 cut points
```

### 5c. Locally, yes — the shipped tracker on the same session

`node run_beat.mjs 20260927-171534-085f6ee9 4/4`, feeding the real `events.jsonl` through `onsets.js` + `beat.js`:

```
14,647 events, 3,919 ticks, causal run = 180 ms total = 0.046 ms per 250 ms tick
bpm (tactus):        p10 81.8  p25 87.1  med 96.9  p75 99.8  p90 113.4
periodicity 'per':   p10 2.51  med 2.99  p90 4.21
mode:                steady 4%   loose 32%   free 44%   hold 20%
drawing:             bars 4%     tape 96%
hit share:           p10 0.50  med 0.75  p90 1.00
subdivision (tatums/beat): {1: 36, 2: 2649, 3: 740}
period jumps:        x1.5-ish 0.37/min   x2-ish 0.00/min
bpmShown:            med 98, range 74-149, 180 changes = 11.03/min
SETTLED BEATS:       n=1080, IBI med 634 ms (p10 476, p90 740)
beat-to-beat wobble: med 4.4%, p90 18.2%
```

Three things to read off this:

1. **Real time is not the hard part.** 0.046 ms of compute per 250 ms of music — about 5,400× faster than real time, single-threaded, in JavaScript. Whatever stops us, it is not the clock.
2. **His wobble is 4.4% / 18.2%**, which lands squarely in the doc's `rub2` "strong rubato" synthetic class (4.1% / 20.5%, `tempo-meter.md:210`). That is measured, not asserted.
3. **`drawing: bars 4%, tape 96%`.** From inference alone, today's system would draw proportional unmetered "tape" for 96% of this take. It will not hand you bar-lined sheet music of this performance without a beat source you supply.

My Python reimplementation of periodicity strength read median **4.48** where the shipped tracker reads **2.99** — a 1.5× disagreement. The shipped number is authoritative; my band shares (49% steady) are wrong and are superseded. Flagging it because it is a real trap: *"periodicity strength" is not portable across implementations, so never compare a reimplementation against the published 4.5/3.0 cut points.*

### 5d. The triplet answer — onset phase inside the real settled beats

This is the measurement that matters for a drummer. For each of 2,764 onset groups, its phase inside the settled beat interval that brackets it (beats 200-2000 ms, median span 642 ms):

```
phase   count            phase   count
0.000   858 (31.1%)      0.475-0.525  345   <- 1/2, clean peak
0.225-0.275  200 <- 1/4  0.325-0.350   42   <- 1/3, in a VALLEY
0.725-0.775  184 <- 3/4  0.650-0.675   56   <- 2/3, in a VALLEY
```

Deviation from the nearest slot of each candidate grid:

| Grid | median \|dev\| | p75 | p90 |
|---|---|---|---|
| duple (0, ¼, ½, ¾) | **10.1 ms** | 35.0 | 59.0 |
| triple (0, ⅓, ⅔) | 40.0 ms | 74.7 | 99.3 |
| duple 16ths + triplets together | **7.5 ms** | 19.2 | 33.7 |

Swing test — peak of the off-beat population (phase 0.33-0.78) is at **0.495**, implied swing ratio **0.98 : 1**. He plays straight, not swung. (Mean 0.563 and median 0.531 are pulled up by the ¾ population; the mode is the honest statistic here.)

But per minute, the feel switches:

```
 2-3 min  1/2= 50  1/3+2/3= 10   duple
 3-4 min      57            27   duple
 4-5 min      50            28   duple
 5-6 min      27            59   TRIPLE
 6-7 min      62            18   duple
 7-8 min      69            16   duple
 8-9 min      33            34   mixed
 9-10 min     45            18   duple
10-11 min     39            18   duple
11-12 min     23            75   TRIPLE
12-13 min     41            30   duple
```

**So: predominantly straight duple 16ths at ~94 bpm, with two decisively triple passages (minutes 5-6 and 11-12) and one mixed, ~17-22% of the take.** The shipped tracker's own grid detector independently agrees: 740 of 3,425 ticks measured 3 tatums per beat = 22%.

This resolves the "strange rhythmic stuff that didn't come out how I wanted" differently from the task's hypothesis. It is **not** two subdivisions coexisting at every instant. It is a player switching subdivision across a take, against a tracker that holds one grid at a time with 4-decision hysteresis (`meterHold: 4`, `beat.js:83`). The hysteresis that stops the display flickering is exactly what lags a genuine feel change.

Two caveats I will not paper over. The 31% mass at phase 0 is **partly an artifact** — a settled beat that hit takes its onset's own time (`tempo-meter.md:149`), so phase 0 is guaranteed populated; only the off-beat structure is independent evidence. And there is **no ground truth**: nobody has labelled this take, so "duple here, triple there" is my inference from grid deviation, not a verified reading of what he intended.

### 5e. What a global-tempo DP tracker does with the same onsets

`librosa.beat.beat_track` fed the identical symbolic onset envelope (sr=44100, hop=441 → exactly 100 fps):

```
tightness=100: tempo=162.16 bpm  2160 beats  IBI med 370 ms  IQR 350-380  p10 320  p90 410
tightness=400: tempo=162.16 bpm  2139 beats  IBI med 370 ms  IQR 360-380  p10 350  p90 390
librosa.feature.tempo windowed: p10 84.5  med 120.0  p90 166.7  (only 69 distinct values)
```

Two failures at once, both instructive:

- **Octave error.** 162.16 bpm is 1.88× the tracker's 96.9. librosa's default `start_bpm=120` lognormal prior dragged it to double time — exactly the failure `tempo-meter.md:106` predicted from Moelants' 120 bpm population resonance, with the recommendation to centre the prior on *his* feel (80 bpm) instead. **That prediction is now confirmed on his real data.**
- **Rigidity.** One global tempo for 16 minutes, with beat intervals spanning only 320-410 ms (±12%), while the actual tempo curve runs p10 81.8 → p90 113.4 bpm (a 39% range). DP absorbs rubato by inserting and dropping beats rather than by bending tempo.

### 5f. End to end, already on disk

`state\arsenal\score\20260927-171534-085f6ee9\lens6full\export.json` (produced by another lens in this same run, so I read it rather than re-running):

```
280 measures MusicXML, 5,838 pieces, 4,394 chords, 1,205 tie starts
285 tupletBeats (triplet brackets), 1,193 beam groups, 96 accidentals
7 metronome marks, 4 rubato, 1 freely, 8 time changes, 4 short measures
counts: logOns 4633 == scoreSounding 4633   (every note preserved)
rhythm: "unverified"
```

Sheet music with triplet brackets already comes out of this session. And `rhythm = "unverified"` — set at `arsenal\web\piano\score\index.js:611`, which certifies `"inferred"` only when every measure came from the inferred rung and nothing fell to tape. **The system declines to vouch for the rhythm of this take.** That is the correct answer and it is already wired.

---

## 1. The candidate families

| Family | Assumes | Breaks when | Causal? | Cost in numpy/scipy | Status here |
|---|---|---|---|---|---|
| **IOI histogram / autocorrelation / tempogram** | a stationary period over the window | tempo drifts within the window; measured above — global r collapses to 0.034 while windowed is 0.154 | Yes, on a trailing window | Low. ~40 lines. Whole-take ACF of 97,897 frames is one `scipy.signal.correlate(method='fft')` | Induction stage shipped (`beat.js`, per `tempo-meter.md:128-133`) |
| **Comb-filter / resonator bank** | one stable period; harmonic comb resolves level | the comb's own harmonics create the ×2/×3 ambiguity it is meant to solve; needs a prior to break ties | Yes, natural streaming form | Low-medium | Present in spirit as the harmonic sum `H(P) + ½H(2P) + ⅓H(3P) + ¼H(4P)` |
| **Multi-agent hypothesis tracking (BeatRoot)** | several (period, phase) hypotheses can coexist and be scored by explained salience | the top agent can be wrong in a way no scoring fixes; needs a switching law (here 1.5×) or it chatters | **Yes, natively** | Medium. ~400 lines. Measured: 0.046 ms/tick, 24 agents max | **Shipped.** `beat.js:132-663` |
| **Dynamic programming (Ellis)** | one global tempo; a transition cost penalizes deviation from it | rubato — demonstrated in 5e: 162 bpm, ±12% IBI spread against a 39% real tempo range | **No.** Needs the whole signal | Free — `librosa` is installed | Available as a comparison only |
| **Bayesian bar-pointer / HMM / particle filter** | a generative model of position-in-bar × tempo; tempo changes are a proportional random walk | state space explodes; a particle filter degenerates under long holds; met-align scores 56.5 F on live performance (`tempo-meter.md:98`) | Yes (filtering) | High. 1,000+ lines, or an install | Named as v2 (`tempo-meter.md:300`). Not built. Correctly deferred |

The in-house choice — induction to propose, agents to arbitrate — is the right one for our constraints, and the receipts support it: agents *do not* improve the BPM number (induction alone Acc1 0.65 vs 0.61 with agents, `tempo-meter.md:207`). They exist to supply **phase, a grid, and runner-ups**. That is the correct reason to pay for them.

## 2. The hard part: tempo is not constant

**What handles it well:** short trailing windows (12 s here) plus per-hypothesis period adaptation clamped to a band. `beat.js:74` — `periodGain: 0.35`, `periodMin: 0.7`, `periodMax: 1.4`: a hit moves an agent's period by 35% of the error, and no agent may drift beyond 0.7-1.4× its birth period. The clamp is what stops an agent walking to a wrong metrical level one small correction at a time. Measured recovery from a 70→95 bpm step: 4.9-10.3 s (`tempo-meter.md:205`).

**What silently fails, and the failure mode, named:**

1. **Global autocorrelation / whole-take tempogram — "confident noise."** It does not report low confidence; it reports a peak. Measured: max r 0.0344, with seven rivals inside 14% of it. Any pipeline that takes `argmax` without checking peak-to-mean ratio will get a number and never learn it is meaningless. The guard is `periodicity strength = best/mean`, and it read **2.80** for the whole take (i.e. "free") against a median of 2.99 per window.
2. **Global-tempo DP — "rubato absorbed as beat insertion."** Demonstrated in 5e. The grid stays rigid and the *beats* become wrong, so downstream the errors appear as impossible rhythms rather than as a tempo problem.
3. **Grid-fit as confidence — the trap the doc caught.** On synthetic *random* onsets, the share of notes landing on the tracker's grid is median 0.62 — statistically identical to strong rubato's 0.60 (`tempo-meter.md:217`). A tracker that adapts to every onset always looks confident on its own grid. Worse, the naive "lock" rule calls **random playing locked 62% of the time** (`tempo-meter.md:218`). This session's hit share is median 0.75, which would read as "locked" — and the periodicity bands correctly say steady only 4%. The receipt `LR3a` pins it: on random playing, steady 0%, free 90%.
4. **Long holds.** 20% of this session's ticks are `hold`. The doc's readout deliberately excludes the interval that ends at a beat re-anchored after a hold, because counting it *read half tempo after pauses* on session S5 (`beat.js:25-26`). A fermata measured as tempo is a halving.

## 3. Onset weighting recipe

Shipped and calibrated; I would change one thing.

```
1. Chord collapse FIRST.        onsets.js:31  chordMs 40
   Measured here: 4,633 notes -> 2,777 groups. 1,120 groups (40%) are multi-note, max 6.
   Without this, 1,827 sub-30ms gaps enter the IOI histogram as evidence for a
   ~30 ms period. This is not optional, it is the difference between signal and garbage.
2. Near-chord across hands.     nearMs 60 when >= 7 semitones outside the group range
   Catches a left-hand bass struck 50 ms before the right-hand chord as ONE event.
3. Salience.                    onsets.js:46-50
   s = sqrt( sum over notes of (0.4 + vel/127) ) + 0.5 if lowest note <= MIDI 55 (G3)
   - sqrt, not sum: a 6-note chord is louder than a single note but not 6x more
     metrically important. Linear weighting lets one big chord define the tempo.
   - the 0.4 floor: a ghost note still counts as an onset. For a drummer this matters —
     grace notes and ghosted strokes are structurally real even at velocity 20.
   - bass bonus: the lowest voice carries the beat.
4. Pair weighting in induction. gamma 0.8^(groups between), window 12 s
   Adjacent onsets weigh more than distant ones.
5. Prior.                       priorBpm 80, priorOct 0.7
   HIS feel, not the population's 120. Section 5e shows what the 120 prior costs: 1.88x.
6. Pedal and harmony as METER accents only, never as beat evidence.
   beat.js:84  accentBass 0.7, accentHarm 1.2, accentPedal 0.8
```

Measured ablation on the accents: onsets only 0.537 → all accents 0.574 (`tempo-meter.md:209`), and the doc honestly marks that as within noise because the synthetic downbeats already carried a velocity accent. **That ablation has never been run on a real labelled take.**

**My one change, for a drummer specifically:** register weighting is currently one bass bonus at a single threshold (G3). A drummer's metrical hierarchy is register-stratified — kick, snare, hats occupy separate bands and carry different metrical weight. On a keyboard this maps to bass / mid / melody. I would test a three-band weight against the current single bonus. I have not run this; I am naming it as a hypothesis with a cheap test, not a recommendation.

## 4. The octave / metrical-level ambiguity

This is the crux, and it is the same question as "is that a triplet or a tempo change."

**Why it is unavoidable:** a period-only estimator is scale-free. If onsets fall every 320 ms, then 320, 640 and 960 ms all explain the data; the harmonic sum `H(P) + ½H(2P) + ⅓H(3P) + ¼H(4P)` deliberately *rewards* a period whose multiples are populated, which means it rewards every member of the family.

**How each family resolves it:**

| Family | Resolution | Cost |
|---|---|---|
| Histogram / ACF | A prior only. Nothing in the data breaks the tie | Wrong prior = wrong octave. Measured: 1.88× |
| Comb bank | The comb's harmonics *are* the ambiguity | No resolution |
| Multi-agent | Keeps rivals alive and lets a human pick. `FAMILY_RATIOS = [2, 0.5, 1.5, 2/3]` (`beat.js:101`); a tap within 8% selects a live agent rather than replacing it (`tapSelect: 0.08`) | The only family that can offer a one-press fix |
| DP | Commits globally. No runner-up exists | Silent |
| Bar-pointer HMM | Resolves it *structurally* — the state is position-in-bar, so meter and level are inferred jointly. This is the principled answer | High cost; met-align still scores 56.5 F live |

**The direct link to triplets.** In `beat.js:30-34`, the displayed tempo is the tracked beat converted by the *measured subdivision* — grid of 1, 2 or 3 tatums. So a beat at 640 ms with grid 3 and a beat at 427 ms with grid 2 are nearly the same onset evidence. **At the induction level, "he started playing triplets" and "he sped up by 1.5×" are the same observation.** They are distinguished only by whether the *grid* flips or the *period* flips.

On this session the system got that right, and I can show it:

```
period jumps x1.5-ish:  0.37 / min   (the tempo explanation was rarely taken)
subdivision = 3 tatums: 740 of 3,425 ticks = 22%   (the triplet explanation was taken)
period jumps x2:        0.00 / min
```

The ×1.5 relation is the dangerous one and it is the one the doc measured as dominant across S1-S12 (0.2-3.4 flips/min, `tempo-meter.md:33`), with ×2 rare. Here ×1.5 is down to 0.37/min because the meter was pinned to 4/4 — which is precisely the prediction at `tempo-meter.md:251`: *with a user-set meter the conversion is fixed and those flips disappear.* **Confirmed on real data.**

The fragility receipt worth respecting: adding ±25 ms of random jitter to his onsets changes which family member is shown on **19-69% of readouts** depending on session (`tempo-meter.md:224-236`). And `arsenal/web/piano.js` currently stamps `clock()` inside the MIDI handler rather than logging `ev.timeStamp`, so render-frame delay is added to every onset (`tempo-meter.md:417`). **That is the highest-leverage unfixed item in the whole lens, and it is a small change.** I did not measure the actual handler delay; the doc also calls for measuring it before changing anything.

---

## What is actually missing

One thing, and it needs Daniel, not an algorithm.

Every parameter in `BEAT_PARAMS` was tuned on **synthetic** performances. The doc says so plainly at `tempo-meter.md:301`: *"They are tuned on synthetic playing only; retune them on labelled takes (TM5)."* TM5 has never happened. There is no labelled take in this repo — 69 sessions, ~132,000 note events, zero ground truth.

That is why I can measure that minutes 5-6 are triple and minutes 2-3 are duple, but I cannot tell you whether the tracker was *right*, or whether the 10.1 ms median deviation from a 16th grid is his feel or my grid error. And it is why "captures the performance" cannot currently be evaluated at all: there is no reference to compare a score against.

The cheapest fix exploits the fact that he is a drummer. He can tap. `trackEvents` already accepts `taps` and `one` (`beat.js:669`); `score_cli.mjs` already accepts `--taps` and `--one`. One take where he taps the beat and marks bar 1 converts the entire lane from synthetic-tuned to measured, and it upgrades that take from rung 4 (inferred, `rhythm: "unverified"`, 96% tape) to rung 3 (taps, metric bars). **The ladder was built for this and the rung has never been used on real data.**

The number that should make this attractive: notation quantized to 16ths discards a median of **10.1 ms** and a p90 of **59.0 ms** of his actual placement. At a 642 ms beat, 59 ms is 9% of a beat — plainly audible, plainly his. It is also small enough to store as a per-note offset beside the quantized position, which is how a score can be notationally correct *and* keep the performance. `performance.mid` already preserves every onset at 0 ms error (receipt LR9b); `quantized.mid` holds the grid. **Both files already exist on disk for this session.** The performance is not being lost — it is being kept in a second file that nothing currently reads back as expressive data.

**Retirement rule, since a capability without one is debt:** if a labelled take shows the inferred rung cannot beat tape on his material — Acc1 below ~0.5 or beat F below ~0.5 at the measured wobble — retire the inferred rung from *notation* and keep it only for the `♩ ≈ 96` readout and the family buttons. The ladder already degrades to tape by design (`beat.js:122-129`), so retirement is a config change, not a deletion.

**Files:** `E:\AI-Setup\arsenal\web\piano\score\beat.js`, `onsets.js`, `quantize.js`, `index.js`; `E:\AI-Setup\arsenal\score_cli.mjs`; `E:\AI-Setup\tests\score_beat.test.mjs`; `E:\AI-Setup\research\in-flight\live-sheet-music-2026-09-14\tempo-meter.md`; `E:\AI-Setup\state\arsenal\score\20260927-171534-085f6ee9\lens6full\export.json`. My probes: `C:\Users\L5\AppData\Local\Temp\claude\E--\a90a987a-4b74-4e3e-9a06-cad82f47b6b7\scratchpad\{tempo_probe.py,run_beat.mjs,phase_probe.py,out.txt}`.