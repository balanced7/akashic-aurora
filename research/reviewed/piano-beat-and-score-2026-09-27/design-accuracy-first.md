# design:accuracy-first

_Verbatim agent return, workflow wf_fc6a68ac-233, 2026-09-27._

I verified the tree myself and ran new experiments. Here is the design.

---

# Tempo tracking and score transcription: architecture

## 0. Four corrections to the grounding, one of which changes the build order

All four lenses agree the pipeline exists. It does — `E:\AI-Setup\arsenal\web\piano\score\` (18 modules), tests green as of this run: `score_beat` **133/0**, `score_quantize` **68/0**, `score_export` **84/0**, `score_settle` **40/0**. I am not re-litigating that. But three of the four lenses drew the wrong conclusion from it, and one lens's central diagnosis is falsified by measurement.

### 0.1 The notation lens's root-cause claim is wrong. The gate is the binding constraint, not the grid.

The notation lens concluded: *"0.1% metric bars is the root cause of the 7-ties-per-bar clutter… Fixing the grid fixes readability for free. Do not retune the engraver."* The premise is that the grid is bad. I tested it on synthetic takes where truth is known (`E:\AI-Setup\tests\fixtures\score\gen.mjs`, `genTake`, 4/4 ballad, 80 bpm, 32 bars, seeds 37/41/53), running the shipped `clean()` unmodified:

| rubato | beat F70 vs truth | median \|error\| | p90 | bar kinds |
|---|---|---|---|---|
| rub0 (metronomic) | **0.984 / 0.988 / 0.984** | **8.0 ms** | 15.6–18.0 ms | `{tape: 32}` — **zero metric** |
| rub1 | 0.438 / 0.786 / 0.930 | 14.2 / 17.9 / 15.1 ms | 34–39 ms | 30–34 tape, 0–2 metric |
| rub2 | 0.487 / 0.567 / 0.522 | 23.9 / 18.0 / 17.2 ms | 41–49 ms | 0 metric |

On a **perfectly metronomic** take the tracker recovers the beat to 8 ms median with F70 0.984 — and still produces **zero metric bars**. So the grid is not the blocker. I found which gate is, by sweeping it:

| `rung4Floor` | random/free (9 pieces, must stay 0) | rub0 | rub1 | rub2 |
|---|---|---|---|---|
| **8.0 (shipped, `index.js:74`)** | 0 / 258 | **0 / 96** | 2 / 100 | 0 / 105 |
| 6.0 | 0 / 258 | 45 / 96 | 4 / 100 | 0 / 105 |
| **5.0** | **0 / 258** | **74 / 96 (0.77)** | 8 / 100 | 0 / 105 |
| 4.5 | **1 / 258 (leaks)** | 85 / 96 | 11 / 100 | 0 / 105 |

The steadiness band is *not* the problem: on rub0 it reads `modes {free: 2, steady: 31}` — 31 of 32 bars pass `beat.js:127`. The periodicity floor at `index.js:500` (`if (drawing === "bars" && source === "inferred" && !(s.per >= o.rung4Floor)) drawing = "tape"`) rejects all of them. **`rung4Floor: 8.0` is set above what metronomic playing achieves.** `tempo-meter.md:§3` itself records metronomic periodicity p10 = 6.9 and random p90 = 3.2; the shipped floor sits above the *upper* bound of that window. That is a one-constant calibration defect and it explains `ls3-bench-2026-09-15.json` `metricPooled: {bars: 2}` across 18 sessions and all 274 tape bars on his take.

**Consequence for the build order:** the cheapest high-value change is not a new tracker. It is `8.0 → 5.0` with the table above as its receipt.

### 0.2 But the same experiment kills the optimistic reading too

At floor 5.0, rub1 still gets **8/100** metric bars and rub2 **0/105**. His real take's beat sequence sits in the rub1 band (§0.3). So: **inference alone will never notate his expressive solo playing, at any gate setting.** That is now proven against ground truth rather than asserted. Every lens hinted at it; none proved it. He must supply the beat, or accept proportional tape. No algorithm choice changes this.

### 0.3 His take is rub1-shaped, not "the tracker changing its mind"

The notation lens read BPM p90/p10 = 1.56 and concluded *"that is not rubato at a stable pulse — that is the tracker changing its mind about the tactus."* p90/p10 of BPM conflates rubato with level flips. I used a scale-resolved statistic instead: local robust-quadratic leave-one-out residual of the beat sequence over ±W beats.

| beat sequence | W=4 | W=8 | W=16 | R=W16/W4 |
|---|---|---|---|---|
| his take, seg 2 (289 beats, IBI 634 ms) | 15.3 | 23.1 | 42.4 | 2.76 |
| his take, seg 3 (469 beats) | 17.7 | 23.2 | 38.0 | 2.14 |
| his take, seg 5 (305 beats) | 15.0 | 19.7 | 44.5 | 2.97 |
| synthetic rub0 EST | 8.9–11.3 | 7.4–10.3 | 6.8–9.3 | 0.76–0.82 |
| **synthetic rub1 EST** | **18.1–22.1** | **22.1–29.5** | **57.7–64.0** | **2.61–3.44** |
| synthetic rub2 EST | 21.4–28.2 | 24.8–50.0 | 51.9–98.3 | 2.41–3.91 |

His estimated grid is statistically indistinguishable from the tracker's output on **moderate rubato**, and clearly distinguishable from both metronomic and random. So the grid looks like a rub1 performance seen through this tracker — which lets me quote the accuracy the tracker achieves in that regime (§0.1: ~15–18 ms median, ~35–39 ms p90). That number is the floor under every feel claim in this design.

### 0.4 The tracker flattens rubato — the opposite error from the one everyone feared

On rub2 the **truth** beat sequence has a W16 residual of 161–209 ms (genuine phrase-scale tempo curvature). The tracker's output has **52–98 ms**. `periodGain: 0.35` with `periodMin: 0.7 / periodMax: 1.4` (`beat.js:74`) makes the tracker a low-pass filter on tempo. On his most expressive playing we draw a *calmer* tempo curve than he played, and his rubato is then misattributed to note deviations. For a drummer that is the worst possible failure direction, and no lens named it. It gets its own acceptance test (Stage 4, test 2).

---

## 1. The law the design is built on

**A grid derived from the notes cannot measure the notes.**

`beat.js:504`: `let t = b.g ? b.g.t : b.t;` — a settled beat that hit a group **takes that group's own onset time**; a miss is linearly interpolated between neighbouring hits (`beat.js:506-507`). `index.js:207 tactusTime` interpolates between those records, and `index.js:429 beats_ms` is built from it. So the exported grid is piecewise-linear interpolation *through his own onsets*.

I measured the consequence on `E:\AI-Setup\state\arsenal\score\20260927-171534-085f6ee9\lens6full\score.clean.json` (4,601 placed notes):

| deviation of note from grid | n | median \|dev\| | share within 2 ms |
|---|---|---|---|
| **on-beat, vs shipped `beats_ms`** | 1,661 | **0.00 ms** | **53.7%** |
| on-beat, vs leave-one-out local fit | 1,660 | 24.25 ms | 5.1% |
| off-beat, vs shipped `beats_ms` | 2,940 | 18.00 ms | 5.2% |
| off-beat, vs leave-one-out local fit | 2,939 | 27.09 ms | 4.9% |

The grid passes **exactly through** more than half of his on-beat onsets. Remove the self-anchoring and on-beat and off-beat notes become statistically indistinguishable (ratio 0.88–0.99, stable across W ∈ {4,6,8,12,16} and degree ∈ {1,2}).

Therefore the realtime lens's §4 feel table (`1/3` slot "+18.7 ms late") and the tempo-induction lens's phase histogram (31% mass at phase 0, correctly flagged as "partly an artifact") are largely measurements of the anchoring, not of him. The quantization-feel lens hit the dual problem: its librosa stand-in grid was *not* onset-anchored, so it found a real but unknown +3 to +6 ms slot-0 bias — and correctly refused to report feel without removing it.

**This becomes a typed field, not a convention.** Three grid provenance classes travel with every artifact:

- **Class A — exogenous.** Beat times from a source independent of the onsets: the jam click (`arsenal/web/piano/tempomap.js`), a metronome, or a continuous tap track. Feel claims permitted.
- **Class B — endogenous, smoothed.** Fit to his onsets through a smoother with bounded per-beat influence, carrying its own leave-one-out residual as an explicit error bar. Feel claims permitted only when the effect exceeds that bar — and only after the Stage-5 cross-check (§9) validates class B at all.
- **Class C — endogenous, anchored.** Today's `beats_ms`. Notation and BPM readout fine. **Feel output structurally forbidden.**

## 2. What scale his feel can actually be measured at — and the honest deliverable

This is the number that decides the whole feature, and nobody computed it. The repo's own model of human tap error is 30 ms (`gen.mjs` `TAKE_DEFAULTS.tapErrMs: 30`). I measured what survives smoothing (40 reps, error of the smoothed tapped grid vs truth beats):

| tap error | raw sd | ±2 beats | ±4 | ±8 | ±16 |
|---|---|---|---|---|---|
| 30 ms | 30.0 | 21.0 | **15.5** | **11.6** | 8.8 |
| 20 ms | 20.0 | 13.9 | 10.3 | 7.6 | 5.7 |
| 10 ms | 10.0 | 7.0 | 5.2 | 3.8 | 2.8 |

±16 smoothing buys 8.8 ms but destroys real tempo motion (rub1 truth curvature over ±16 beats is 52–67 ms). So the usable window is ±4 to ±8, giving a **tapped-grid error of 12–16 ms sd**. Compare the effects the lenses reported: off-16ths early by **5–6 ms**, swing offset **+6.35 ms**.

**Per-note microtiming at the 5 ms scale is not measurable on a free solo take by any grid we can build.** Not with this tracker (15–18 ms), not with his taps (12–16 ms). A click would resolve it, but playing to a click is a different performance.

**Per-slot systematic feel is measurable, and it is the real deliverable.** A mean over n notes has standard error sd/√n: at sd 15 ms and n = 500–1,000, that is 0.5–0.7 ms. A 5 ms effect is then 7–10σ — *provided the grid error is independent of the slot being measured*. Class A guarantees that (his taps are not his notes). Class C violates it catastrophically. Class B is the open question, and §9 names it as the riskiest assumption with a one-take experiment that settles it.

So the honest product split:
- **Per-note ribbon**: drawn with a confidence band equal to the grid's LOO sd; notes inside the band drawn grey. Resolves phrasing at the **20–50 ms** scale — which is real (his measured off-beat p90 is 50–56 ms) and is exactly the scale a drummer means by "behind" versus "on top of" the beat.
- **Per-slot feel card**: the statement he can act on ("your off-16ths sit 6 ms early, at every tempo in this take"), resolvable to ~1 ms, gated on grid class.
- **Never** a per-note millisecond number on a class-C grid.

---

## 3. Components

Everything extends what exists. Two extended files, three new pure modules, one new Python verifier, one renderer extension. All new JS modules follow the house contract on line 1: *pure ES module, no DOM, no clock*.

### 3.1 `E:\AI-Setup\arsenal\web\piano\score\tempomapfit.js` — new (stage T2.9, "tidy")

```
fitTempoMap(beats, { class, lambda|auto, segments, meter }) -> TempoMap
```
- **In:** `[{ t_ms, hit: bool, conf, source }]` — `beat.js` settled beats (`beat.js:642 settled`), or tap times, or the jam tempo map.
- **Out:** `TempoMap` (§5.1) — knots, a period function, per-beat LOO residuals, and the class label.
- **Algorithm: penalized least squares on log-period with a second-difference penalty**, solved as a banded linear system in the tempo domain; λ selected by generalized cross-validation on the LOO residuals, clamped to a band calibrated against `gen.mjs` rub0/rub1/rub2 truth curves. Monotonicity in time enforced as a constraint.
- **Chosen over** *Kalman filter / Cemgil–Kappen smoother* (`tempo-meter.md:102`): algebraically equivalent in the linear-Gaussian case, but its state-noise parameter is exactly the unknown; the penalized form exposes one interpretable λ we can calibrate against truth curves, and forward–backward is more code for the same estimate.
- **Chosen over** *`librosa.beat.beat_track` DP*: measured by the induction lens to return one global tempo of 162.16 bpm on his take (1.88× octave error from the `start_bpm=120` prior) with beat intervals spanning only ±12% against a 39% real tempo range. Stays as a comparison baseline; never a component.
- **Chosen over** *bar-pointer HMM / particle filter*: genuinely better — it resolves level and phase jointly, which is the principled answer to §7's ambiguity — but 1,000+ lines, and met-align scores 56.5 F on live performance (`tempo-meter.md:98`). Deferred as v2, exactly as `tempo-meter.md:300` already ruled. I am not overturning that ruling.
- **Chosen over** *raw `beat.js` output*: measured in §0.3 — not locally smooth at any scale (residual grows 15 → 44 ms from ±4 to ±16 beats), and class C.
- **Critical implementation detail:** the LOO residuals are the *product*, not diagnostics. They are the error bar attached to every downstream feel number. A `TempoMap` without them is invalid.

### 3.2 `E:\AI-Setup\arsenal\web\piano\score\level.js` — new, small

```
chooseLevel(beats, groups, { meter, candidates }) -> { factor, score, runnerUp, margin, why }
```
- Adopts the quantization-feel lens's selector — `looseRate + 0.5·[σ saturated] + d1Share` — which is a genuinely good contribution and I take it as specified. I add one term: **the LOO residual normalized by the candidate period**, because a wrong level shows up as a residual that is a large *fraction* of the beat. His segments measure 0.024–0.028 of the beat at ±4 (from §0.3); a doubled level would put them near 0.05.
- **Chosen over feeding this back into `beat.js`'s causal family machinery.** `beat.js:14` guarantees determinism from a monotonic clock so replay and live agree, and `tests/score_quantize.test.mjs:214` asserts clean and live agree on the same events. A quantizer→tracker feedback loop would break both. Level choice is a hindsight decision: it belongs in the tidy pass and in the human-pressed family buttons (`FAMILY_RATIOS`, `beat.js:101`; `tapSelect: 0.08`), not in the causal loop. This is where I part company with the quantization-feel lens, which wanted the signal to "flow back to `beat.js`'s tactus/family machinery."

### 3.3 `E:\AI-Setup\arsenal\web\piano\score\feel.js` — new

```
deviations(score, tempoMap)                  -> DeviationSet
feelProfile(devSet, { by: "segment"|"phrase" }) -> FeelProfile[]
swingOf(devSet, span)                        -> SwingReading
syncopation(score, phase, tempoMap)          -> SyncopationReading
```
Every function **returns `null` with a stated reason when `tempoMap.class === "C"`**, and stamps `grid: { class, looMedian, looP90, rev, knotHash }` onto every number it emits. This is the anti-lying mechanism and it is a type check, not a code review convention.

### 3.4 `E:\AI-Setup\arsenal\web\piano\score\quantize.js` — extend (three surgical changes)

1. **Retain the residual.** `quantize.js:106` already computes `const e = (it.f - k/d) * P` and throws it into `fit`; `:195` recomputes it for the σ EMA and discards it again. `fitOf` returns `devs: e[]`; `decide()` (`:199`) and `cleanDivisions()` (`:253`) carry it. Cost: one array push.
2. **Surface the margin.** `divideBeat` already returns `runnerUp` at `:143`. I confirmed by grep across `arsenal/`, `tests/`, `scripts/` that **nothing reads it** (the two `tests/piano_spell.test.mjs:146,149` hits are an unrelated local). `decide()` carries it through `...r`; `cleanDivisions` at `:253` drops it. Add it there, and draw any beat below a margin threshold as ambiguous with its runner-up available. The quantization lens found seg2 beat 38 decided by **0.170** on a scale where the change penalties alone are 1.6.
3. **Make `sigma` mandatory.** `cleanDivisions`' signature defaults it to `QUANT_PARAMS.sigma0Ms` = 40 ms (`:223`). `index.js:346` passes `sigma: q.sigma()` correctly, but the quantization lens measured that at the 40 ms default, triplet recall on his take drops **14/14 → 6/14**. A latent trap that halves triplet recall should be a type error. `bench.js` and the lab pages are the exposure.
4. **Tuplet sanity gate.** A beat may not be *exported* as d=3 or d=6 (a bracket on the page) when its own max \|residual\| exceeds a fraction of the grid step. This is the direct fix for the three spurious triplets the quantization lens found at 480–560 s with residuals of +41/−70, +74/−41, +22/−66 ms. Those would engrave as triplets with 70 ms errors inside them — the single failure most likely to make him say the notation is lying. Gated beats become loose, which is the honest answer and is already a supported state.

### 3.5 `E:\AI-Setup\arsenal\web\piano\score\musicxml.js:369` — one-line fix

```js
beam: beamOf.get(it), tuplet: k === 0 ? bracketOf.get(it) : null,
```
`tuplet` is gated to the chord's principal note; `beam` is not. Per MusicXML 4.0 `<beam>` belongs on the chord's first note only. I reproduced this independently with stdlib XML: **1,028 `<beam>` elements on `<chord/>` member notes in 166 of 280 measures**, and with Verovio 6.3.0 on the shipped export: **1,022 errors** — 651 `Adding 'beam' to a 'chord'`, 337 `MusicXML import: Chord starting point has not been found`, 18 tuplet, 10 rest, 6 space. Our own verifier LR9a passes because it checks beams against the transcriber's own model. Fix: `beam: k === 0 ? beamOf.get(it) : null`.

### 3.6 `E:\AI-Setup\arsenal\web\piano\score\index.js` — three changes

1. `rung4Floor: 8.0 → 5.0` (`index.js:74`), with the §0.1 table as the receipt.
2. **`rhythm` must not lie about provenance.** `index.js:611` returns `"jam"` whenever `fixed` beats were injected, whatever their origin. I confirmed this end to end: injecting `gen.mjs` truth beats gives `{metric: 32}` and `rhythm: "jam"` on a take that never saw the jam clock. Add `"clicked"` and `"tidied"`; reserve `"jam"` for the jam clock alone. The grid class (§1) rides alongside.
3. **Per-segment `feel` in `clean()`.** Live, a feel change already closes a segment (`index.js:165`); offline, `clean()` takes one global `feel` (`index.js:666`). The tempo-induction lens measured two decisively triple passages in his take (minutes 5–6 and 11–12, ~17–22%) against a tracker holding one grid at a time with `meterHold: 4` hysteresis. The tidy pass must be able to choose feel per phrase. Small change; the machinery exists.

### 3.7 `E:\AI-Setup\arsenal\piano_feel.py` — new, read-only verifier

Follows the `tests/test_score_export.py` pattern exactly: an independent Python-stdlib/numpy reader that recomputes the deviation statistics, LHL syncopation and swing CIs **from the JSON artifacts**. Python never re-implements the tracker or the quantizer. The realtime lens correctly named the existing drift landmine — `E:\AI-Setup\arsenal\performance.py:1391` already duplicates onset grouping at `ONSET_MERGE_MS = 40` with no shared fixture, while `onsets.js` has since grown near-chord, roll merging and grace detection. The rule to write down: **the analysis core stays single-source in pure JS; Python reads artifacts and argues with them, never re-infers.** That is also why I reject a Python tempo tracker outright.

### 3.8 The drummer view — extend `E:\AI-Setup\scripts\piano_roll_render.py` and `arsenal\web\piano\score\ribbon.js`

Not a new organ. Three panels over the roll he already has: tempo curve with the LOO confidence band; IOI histogram with subdivision lines drawn on it; deviation ribbon under the staff (`ribbon.js:372` already interpolates a position against real `t`, so it is the natural host). The notation lens's ranking here is right and I adopt it: a tempo curve is a native object to a drummer in a way a treble clef is not.

### 3.9 Tap capture in the page — the one genuinely missing input

`--taps` exists (`score_cli.mjs:92-95`, accepting `taps_ms` / `taps_s`) and `trackEvents` accepts `taps` and `one` (`beat.js:669`). What is missing is a way for him to *produce* taps: a footswitch or key that logs a tap event.

**And the taps rung as built is not what stage 3 needs.** I tested it: `beat.js:85` sets `taps: 4, tapValidBars: 4` — it is a **4-tap count-in with a 4-bar validity window**, not a continuous tap track. Injecting the generator's 4 taps plus "This is 1" yields **2 metric bars of 32** at every rubato level, then falls back to inferred. A drummer tapping continuously through a take must go through the **fixed-beats injection** (`index.js:102`, `clean({ beats })`), which I verified gives **32/32 metric bars**. So: taps for phase and level → the tap rung; a continuous tap track → `beats` injection as a class-A grid. Two different paths, and the second is the one TM5 needs.

---

## 4. The seam that makes all of this cheap

`index.js:102`:
```js
const fixed = Array.isArray(o.beats) && o.beats.length >= 3 ? o.beats.slice() : null;
```
and `index.js:104`: `const bt = fixed ? null : createBeatTracker(...)`.

**The transcriber already accepts an externally supplied beat grid and bypasses its own tracker entirely.** Verified end to end. So the tidy pass, the click grid and the tap track all attach through one existing, tested seam: `clean(events, { beats: tempoMap.times(), one })`. No surgery on `beat.js`, no fork of the transcriber, nothing new in the causal loop. The three defects this seam currently has — `rhythm` mislabels the source as `"jam"`, `segKey` collapses everything to one `"fixed"` segment (`index.js:224`), and no class travels with the grid — are all in §3.6.

---

## 5. The data contract

Versioned API strings in the house style (`QUANTIZE_API`, `BEAT_API`, `SETTLE_API`).

### 5.1 `TempoMap` — `arsenal.piano.score.tempomap/v0`

```
{ api, class: "A"|"B"|"C", source: "jam"|"click"|"taps"|"tidied"|"inferred",
  segments: [{ id, from_ms, to_ms, reason }],
  knots:  [{ beat: int, t_ms: float }],          // monotone in t_ms
  loo:    [{ beat: int, resid_ms: float }],      // leave-one-out; the error bar
  looMedianMs, looP90Ms, lambda, window,
  level:  { factor, runnerUp, margin, why },
  rev, knotHash }                                // identity; see the retirement rule
```
`class` is computed, never asserted: `"A"` requires `source ∈ {jam, click, taps}`; `"B"` requires a fit whose per-beat influence is bounded and `loo` populated; anything else is `"C"`.

### 5.2 `DeviationSet` — `arsenal.piano.score.feel/v0`

One record per placed onset, keyed by the stable `note.id` that `index.js:606` already emits:

```
{ api, grid: { class, source, rev, knotHash, looMedianMs, looP90Ms },
  bias_ms,                                       // removed grid bias, stored so raw is recoverable
  notes: [{ id, bar, beat, d, k, pos,
            ms,        // signed: onset − notated grid time, AFTER bias removal
            beat_frac, // ms / P            — comparable across tempi
            grid_frac, // ms / (P/d)        — |grid_frac| > 0.5 means it was nearer another slot
            P, sigma,  // the per-beat sigma the decision was made at (exists today, discarded)
            margin,    // cost(runnerUp) − cost(chosen) (exists at quantize.js:143, unread)
            inBand }]  // |ms| <= grid.looP90Ms  → drawn grey, never quoted
}
```

Four rules the measurements force, three of them the quantization-feel lens's and correct:

1. **`bias_ms` is mandatory.** Slot-0 mean deviation was +3.1 to +6.3 ms with p < 10⁻¹¹ in every segment of that lens's run. A player cannot be systematically late on the onsets that define the grid. Ship without bias removal and the system tells a drummer he plays 5 ms late when the grid is 5 ms early.
2. **`grid_frac`, not `ms`, is the honest primary.** 10 ms at 87 bpm and 10 ms at 230 bpm are different musical facts.
3. **`margin` must be surfaced.** It is computed and discarded today.
4. **`inBand` is mine and it is the one that stops the lying.** Any deviation inside the grid's own LOO p90 is not evidence about him. On his take that band is 35–39 ms, which greys out most of the ribbon — and that is the correct, honest picture.

### 5.3 `FeelProfile` / `SwingReading` / `SyncopationReading`

```
FeelProfile:  { span, d, slot, n, mean_ms, sd_ms, se_ms, systematicOverRandom: |mean|/sd,
                reportable: bool, grid }
SwingReading: { span, n, medianX, ratio, ci95: [lo, hi], sigmaX_ms, offsetMs,
                verdict: "straight"|"swung"|"triplet"|"sloppy"|"below-noise", grid }
SyncopationReading: { perBar: [{ bar, lhl, wnbd, perStream: [{ stream, lhl }] }],
                      attribution: [{ noteId, units }],
                      phase: { source: "jam"|"song"|"one"|"inferred", conf }, grid }
```
`reportable` is false when `systematicOverRandom < 1` or `|mean_ms| < se_ms · 3` or `grid.class === "C"`. The UI greys unreportable values; it does not hide them, because "we cannot tell yet" is information.

---

## 6. Triplets, swing, syncopation, specifically

### Triplets
The decision rule already exists and is formal — `quantize.js:13-14`, `C(d)` over the alphabet {1,2,3,4,6} with λ tables at `:48-53`, adaptive σ (EMA 0.05, clamped 15–60 ms), continuity 0.8, bar-back 0.8, collision 6, and the `d6MinGroups: 5` gate. Five anti-flap mechanisms; measured flap rate 0.054–0.094 division changes per beat. I am not redesigning it. Four changes:

- Per-note residuals retained → the tuplet sanity gate (§3.4.4) catches the three spurious brackets.
- `margin` surfaced → a beat decided by 0.17 is drawn ambiguous, not rendered as fact.
- `sigma` mandatory → the 14/14 → 6/14 trap becomes impossible.
- Per-segment `feel` → his mid-take subdivision switches become representable instead of fighting `meterHold: 4`.

The closed-form entry barrier is worth keeping visible for calibration: for a perfect triplet, d=3 loses to d=4 once σ > (P/12)/√2.1 = 0.0575·P to *enter* and 0.1179·P to *hold*. At P = 528 ms that is 30.4 ms to enter, 62.2 ms to hold, against a σ clamp of 60. High entry barrier, near-unbounded retention — good anti-flap design whose cost is that *the first triplet of a run is the one at risk*, empirically confirmed (the live pass missed exactly the run's entry beat; the Viterbi pass recovered it).

### Triplet vs swung pair vs sloppy straight
A genuine triplet with all three notes sounding is **not** ambiguous: the 3-grid rms error measured 6.3–13 ms against 34–58 ms on the 4-grid, a 3–7× advantage. The real ambiguity is a triplet with the middle note absent (onsets at 0 and 2/3) versus a swung pair — timestamp-identical, so the discriminator must be phrase-level. I adopt the quantization-feel lens's rule as specified, with its conditioning, which is the part that makes it work:

Over a phrase, for beats the quantizer read as **d=2 with onsets on slots 0 and 1**, let `x` be the offbeat's beat fraction, `E₃` the count of beats in the window with an onset within 0.05 beat of 1/3:

```
σ_x > 0.06 beat                     -> SLOPPY / free. Report no subdivision; mark loose.
|median(x) − 0.5| < 0.03            -> STRAIGHT.
median(x) > 0.53 and E₃ >= 3        -> TRIPLET (notate the 3-grid, rest the empty 1/3 slot).
median(x) > 0.53 and E₃ <  3        -> SWUNG (notate straight, report the ratio).
```

The conditioning on the quantizer's own d=2 reading is load-bearing: unconditioned, σ_x measured 0.024–0.140 beat and the rule said "sloppy" everywhere; conditioned, σ_x is 0.018–0.038 beat and it discriminates. One addition of mine: **the thresholds must be expressed in units of the grid's LOO sd, not in fixed beat fractions.** 0.03 beat at 634 ms is 19 ms — below the class-C grid's own 35 ms p90. On a class-C grid this rule is unrunnable, and it should refuse rather than answer.

### Swing
Continuous ratio `r = x/(1−x)`, reported as a **distribution**: median r, bootstrap 95% CI, `σ_x` in ms, n, and `|mean|/sd`. Never as a bare number. On his take the measured pooled r is 1.0376 with CI [1.0068, 1.0806] and a +6.35 ms offbeat offset — **which is 3× below the tracker's own median beat error in his regime (15–18 ms).** The honest output on a class-B grid is therefore *"straight; no swing measurable above ±15 ms grid error"*, and the number appears only when the grid is class A. The tempo-induction lens's independent mode-based estimate (0.98:1) agrees on the verdict.

### Syncopation
Nothing in the tree represents it: `beat.js:84`'s accents (`accentBass 0.7, accentHarm 1.2, accentPedal 0.8`) run the opposite direction (accents → meter template), `marks.js accentMarks` is velocity-based dynamics, and `measures.js:220`'s "syncopated quarter" is a rhythm-spelling rule.

- **Primary: Longuet-Higgins & Lee 1984 (LHL).** Chosen for one decisive reason — its score is **attributable to a specific note**, so you can point at the staff and say "this is the syncopation, 3 units". It is also the measure used in the groove/embodiment literature (Witek et al. 2014).
- **Reject Keith 1991** on the measured grounds: unnormalised, so on real polyphonic bars it is a note-density proxy (corr −0.118 with LHL). It ranked a dense 16th run above a sparse displaced figure — inverted.
- **Second, continuous: WNBD** (Gómez et al. 2005), corr +0.596 with LHL, bounded, degrades smoothly where LHL is integer-stepped. It only knows the beat, not the bar, so it cannot distinguish a displaced note on beat 4 from one on beat 1 — hence second, not primary.
- **Pressing 1997 / Toussaint 2002**: same hierarchy family, no per-note attribution advantage over LHL. Not adopted.
- **Per-stream extension (Sioros & Guedes 2011) is the part that matters for a drummer, and it is not optional.** LHL/Keith/WNBD are all defined on a monophonic binary onset grid; collapsing polyphony to "positions occupied" makes a left-hand bass on beat 1 plus a displaced right hand score the same as nothing on 1. For a drummer that is exactly backwards: syncopation is per-limb. `arsenal/web/piano/score/hands.js` already assigns voices and streams and `onsets.js:47-51 salienceOf` already carries velocity, so per-stream LHL is computable from what exists.
- **LHL requires committed bar phase**, so every syncopation number carries `phase.source` and `phase.conf`. A phase error of one beat rewrites every score in the bar. `meter.js inferPhase` plus `index.js`'s priority (jam → song → "This is 1" → inferred) already supply it; measured synthetic downbeat F is 0.578 overall and **0.173 on strong rubato**, which is precisely why the provenance must travel.

---

## 7. How expressive microtiming is preserved rather than quantized away

1. **It is already preserved losslessly, in a file nothing reads back.** `midi.js:5-11` writes `performance.mid` as SMF type 0 at PPQ 500 with 1 tick = 1 ms — every logged on/off at its true time, receipt LR9b measuring 0 ms error — alongside `quantized.mid` on the grid. Both exist on disk for his session right now. The performance is not being lost; it is being kept in a second file with **no link between note *i* in one and slot *k* in the other.**
2. **The missing artifact is the join, and it is nearly free.** `index.js` already emits stable `note.id`, `pos` in ticks, `t_ms`, and per-bar `beats_ms` (`index.js:429`, `:606-607`). So `DeviationSet` is computable *today* from data already in the export. Cost: one array push in `fitOf`, two fields in two return objects.
3. **Notation stays notation.** Deviations never enter MusicXML as notated content. They live in a sidecar join table beside `performance.mid` and `quantized.mid`. What *does* go into MusicXML is the tempo map as `<sound tempo>` per bar plus metronome marks — `musicxml.js` already writes these (7 on his take) — so a rendered score plays back with his tempo curve even though the noteheads sit on a grid. That is the correct division: the grid carries the reading, the tempo map carries the breathing, the sidecar carries the placement.
4. **Where the notation genuinely cannot tell the truth, it already refuses.** `quantize.js:29-34`: when the best division exceeds `looseCost` 12, or a collision cannot be explained as a roll, the beat is marked loose and drawn as proportional tape — claiming no rhythm at all. This is the right design and it is why his take comes out `rhythm: "unverified"` (`index.js:611`) with 274 tape bars. **I am keeping that refusal and extending it**, not weakening it: the tuplet sanity gate adds a new reason to refuse, and `inBand` adds a third.

---

## 8. Build order, with falsifiable acceptance tests

### Stage 0 — the two defects that cost hours
- `musicxml.js:369` beam gate. **Passes** when Verovio load of every fixture export yields **0 errors**, asserted in `tests/score_export.test.mjs` so a foreign consumer guards the export from here on. **Fails** if any error remains. Baseline: 1,022 errors on his take today.
- `cleanDivisions` `sigma` becomes required; `bench.js` and the lab callers updated. **Passes** when triplet recall on his take stays 14/14 and a caller omitting `sigma` throws. **Fails** if any caller silently keeps the 40 ms default.

### Stage 1 — the gate calibration (highest value per unit of work in the whole design)
`rung4Floor: 8.0 → 5.0`.
- **Passes** when, on `gen.mjs`, metric-bar share is **≥ 0.70 on rub0** and **exactly 0 on the 9 random/free pieces**. Measured at 5.0: 74/96 = 0.77 and 0/258.
- **Fails** at 4.5 (random leaks 1/258) and at 8.0 (rub0 = 0/96).
- **Second falsifier:** if on his real sessions 5.0 admits any bar whose tempo-map LOO residual exceeds 5% of the beat, revert. Keep receipt LR3a green throughout (random playing: steady 0%, free 0.9025).

### Stage 2 — TM-D, the timestamp drill
`piano.js:3513 onMidiMessage(ev)` reads `ev.data` and never `ev.timeStamp`; `piano.js:2653 noteOn` stamps `clock()` itself, adding render-frame delay to every onset; `piano.js:4602` already fakes a `timeStamp` nobody reads. Log both side by side for 2 minutes with the 3D scene rendering.
- **Passes** with a dated drill note carrying the offset and jitter distribution.
- **Fails / do nothing** if measured added jitter p90 is below 5 ms — `tempo-meter.md:6.10` says measure before changing, and a change without a measurement is the debt this repo forbids.
- Why here: ±25 ms of added jitter moves the beat level on up to 69% of readouts on some of his sessions, and my measured grid error in his regime is 15–18 ms. 25 ms of handler jitter would dominate everything downstream.

### Stage 3 — TM5, labelled takes. The gate for everything expressive.
~10 short takes from Daniel: some to the jam click (class A by construction), some with a **continuous** tap track (§3.9 — not the 4-tap count-in), some free; 4/4, 3/4, 6/8; at least two where he deliberately plays triplets and two where he deliberately swings, labelled by him.
- **Passes** when beat F70 and Acc1 of the inferred rung against his click grid are reported for the first time on real data, and the accent ablation (`tempo-meter.md:209`: onsets 0.537 → all accents 0.574, honestly marked "within noise" on synthetic) is finally run on labelled material.
- **Fails, with a consequence:** if inferred beat F70 against his click is below ~0.5 at his measured steadiness, **retire the inferred rung from notation** and keep it only for the BPM readout and the family buttons. Retirement is a config change — the ladder already degrades to tape (`beat.js:122-129`).
- This stage is not optional and no algorithm substitutes for it. There is no ground truth in 69 sessions and ~132,000 note events. Every `BEAT_PARAMS` value was tuned on synthetic playing; `tempo-meter.md:301` says so plainly and TM5 has never happened.

### Stage 4 — `tempomapfit.js` + `level.js` (TM4)
Three tests, and the second one is mine:
1. **Tidy ≥ causal.** On `gen.mjs` truth, tidy beat F70 ≥ causal beat F70 at every rubato level. Baselines measured this session: rub0 0.984/0.988/0.984; rub1 **0.438**/0.786/0.930; rub2 **0.487**/0.567/0.522. The rub1-s37 and rub2-s37 cases are where the tidy pass must earn its keep.
2. **Tidy must not over-smooth.** On rub2, the tidy map's own ±16-beat residual must be within 2× of the truth curve's. Truth: 161–209 ms. The causal tracker: 52–98 ms — it flattens genuine rubato by 2–4×. **Fails, and must be rejected, if the tidy map is smoother than truth by more than 2×**, because a smoother tempo map invents steadiness and misattributes his rubato to note deviations. The original TM4 spec (`tempo-meter.md:445`) can be passed by a flatter map; this test closes that hole.
3. **Level chooser.** Chosen factor equals truth's on ≥ 0.9 of synthetic segments, and on the ×2/×0.5 family suites it does not release a correct level (LS1-level already measures `heldShare` 0.974 at rub0, 0.59 at rub2). **Fails** if it releases a correct level more often than the shipped `levelHold: 4` machinery does.

### Stage 5 — `feel.js`, deviations and the feel card
1. **The anchor test.** On a class-A take, on-beat median \|dev\| must be strictly below off-beat median \|dev\| — a drummer places the beat more precisely than the subdivisions. Measured on the class-C grid today: ratio **0.88–0.99** across every window and degree, with an on-beat median of exactly **0.00 ms** and **53.7% inside 2 ms** — the self-anchoring signature. **Fails, and the feel card does not ship, if on a class-A grid the ratio stays ≥ 0.9** — that means either the grid is still wrong or he does not anchor beats, and either way the premise of the feature is false.
2. **Every reported effect exceeds its error bar**: `|mean| > 3·se` with `se = grid.looSd/√n`, and `systematicOverRandom ≥ 1`. On his take at n=77 and sd 25 ms, se is 2.8 ms, so the 6 ms swing offset is reportable *only* if the grid error is slot-independent.
3. **Recovery on known swing.** Add a swing parameter to `genTake` and require the recovered ratio within 0.05 of truth with ≥ 90% CI coverage. **Fails** on bias > 0.05 or under-coverage.

### Stage 6 — syncopation, per-stream LHL
- **Passes** when LHL rank correlation with his own bar labels from the TM5 takes is ≥ 0.6 and the per-note attribution points at the note he names.
- **Fails** if LHL ranks a dense 16th run above a sparse displaced figure — that is the Keith failure mode and would mean the collapse-to-positions bug survived into the per-stream version.

### Stage 7 — realtime
Compute is a non-issue and I am not going to pretend otherwise: measured causal tick mean 0.033 ms / p95 0.156 ms; transcriber p95 0.275 ms per onset group; whole 23-session export 3,805× realtime; Verovio load of a 280-bar score 339 ms with page 1 at 58 ms (my measurement). The realtime question is **what may be claimed live**, not whether it fits. Live shows only class-C-safe things: `bpmShown`, the band word, the beat pip, the ÷2/×2/2↔3 family buttons, tap, "This is 1", and the subdivision chip — all of which `beat.js:639-642` and `meter.js:26-33` already compute and throw away for want of a HUD. The feel card appears after the tidy pass runs at segment close. Bars settle at `settleBeats: 4` (`settle.js:22`) with measured relabel churn of 0.035% at lag 2 and 0.000% at lag 4, and 0 of 1,998 settled bars ever changed. That machinery is done; nothing here disturbs it.

---

## 9. The riskiest assumption

**That the grid's error is independent of the slot being measured.**

Every per-slot feel claim — "your off-16ths are 6 ms early" — is a mean over hundreds of notes, and a mean beats a noisy grid: at sd 15 ms and n = 1,000 the standard error is 0.5 ms, so a 5 ms effect is 10σ. That arithmetic is the entire reason this feature is possible at all. It holds **only if the grid's error does not correlate with which slot a note sits on.**

- On the shipped class-C grid the assumption is **false by construction**, and I measured how badly: on-beat notes sit at median 0.00 ms with 53.7% inside 2 ms, off-beat notes at 18.00 ms with 5.2%. Any per-slot comparison on that grid is measuring the anchoring.
- On a class-A grid it is **true by construction** — his taps or the click are not his notes.
- On a class-B grid (a smoother fit to his onsets) it is **unverified and plausibly false**: a smoother fit to onsets that are predominantly on-beat will be pulled toward the on-beat onsets, reintroducing exactly the correlation the smoothing was meant to remove. And class B is precisely what this design wants to use on free takes — which is most of what he plays.

**The experiment that settles it needs one take.** Record one take to the click. Build two grids from the same notes: the class-A click grid, and a class-B grid from `tempomapfit.js` ignoring the click. Compute the per-slot `FeelProfile` from each. If they agree within the stated error bars, class B is validated for free takes and the feature generalizes. If they disagree, **class B is retired from feel permanently** and only class-A takes ever produce a feel card — which means the honest deliverable on a free solo take shrinks to phrasing at the 20–50 ms scale plus a tempo curve, and the millisecond feel statement becomes a click-take-only capability.

I would run that experiment before writing a line of `feel.js`.

---

## 10. Dependencies

**Argue for: `verovio`.** Verified installable with zero dependencies, and verified working: it loaded the 1.4 MB / 280-bar export in 339 ms, produced 13 pages, rendered page 1 in 58 ms — and **it caught a real defect that our own verifier LR9a passes**, because LR9a checks beams against the transcriber's own model. Its value is precisely that it is not our code. Adopt it as an **adversarial consumer in the test suite**, not in the render path (`musicxml.js` already emits MusicXML 4.0 partwise; Verovio consumes `take.musicxml` unchanged).

One correction to the notation lens: it reported verovio 6.3.0 as installed. It is **not** installed in the repo's pinned interpreter — `py -c "import verovio"` fails under `C:\Users\L5\AppData\Local\Programs\Python\Python311\python.exe`. It exists only in a disposable venv at `C:\Users\L5\AppData\Local\Temp\claude\E--\a90a987a-4b74-4e3e-9a06-cad82f47b6b7\scratchpad\nven`. Install it into a **pinned repo venv**, not the global 3.11 — the machine's Python strategy pins 3.11 via `py.ini` deliberately and the score path must not pollute it.

**Retirement rule for verovio:** if a future major version rejects a construction MusicXML 4.0 permits, pin the old version and file the divergence rather than bending our export. If it stops being maintained, the assertion generalizes to "any independent consumer" and the test is skipped with a dated note, never deleted.

**Optional: `music21` 10.5.0** — three pure-Python deps, no numpy constraint, verified present in that same venv. A second independent reader for ties and durations. Lower value than verovio; take it only if a second opinion is wanted.

**Reject `madmom`, and I do not need to test the install to say so.** Nothing in this design would use it. The tidy pass is a symbolic smoother over onset times — a banded linear system in numpy. madmom is an audio beat tracker, its numpy-2.4 situation is known-painful, and `tempo-meter.md:§7` already argues that all strong offline symbolic models are trained on classical piano and score downbeat F 14–28% on ASAP, worse than what runs here. Also reject `partitura` (capable, nothing needs it — a capability with no retirement rule is debt) and `abjad` (reported unbuildable; I did not re-verify).

**Present and sufficient:** numpy 2.4.4, scipy 1.17.1, librosa 0.10.2, node v24.14.1. librosa stays a comparison baseline only — its measured 1.88× octave error on his take (162.16 bpm against the tracker's 96.9, from the `start_bpm=120` prior) is the reason it is not a component.

---

## 11. Retirement rules

- **The deviation layer is derived, never an atom.** Every `dev` record carries `grid: { class, source, rev, knotHash }`. When the grid changes — a rebuild, a ×2 family press, a tactus or phase change, a new tidy pass — every deviation stamped with the old grid is **invalidated with it, not migrated**. A `dev` number without that stamp is retired on sight.
- **The inferred rung** retires from *notation* if Stage 3 shows beat F70 below ~0.5 at his measured steadiness. It keeps the BPM readout and the family buttons. Config change; the ladder already degrades to tape.
- **Class B** retires from *feel* if the Stage-5 §9 cross-check fails. It keeps notation and the tempo curve.
- **`rung4Floor: 5.0`** retires back to 8.0 if it admits any random bar on the `gen.mjs` free suite, or any real bar whose LOO residual exceeds 5% of the beat.
- **The Verovio assertion** degrades to "any independent consumer" if Verovio is abandoned.

---

## 12. Honest limits: what this gets wrong, and how he notices

1. **No ground truth on any of the 69 sessions.** Every number about his playing — mine, and all four lenses' — measures a grid, not him. *He notices:* the system reports "no measurable swing" on a take he knows he swung.
2. **Inference will not notate expressive solo playing at any gate setting.** Proven: at floor 5.0, rub1 → 8/100 metric bars, rub2 → 0/105. *He notices:* beautiful engraved pages that arrive marked "unverified" and mostly proportional. The fix is his taps or a click, not our algorithm.
3. **The tracker flattens rubato 2–4×.** *He notices:* the tempo curve looks calmer than it felt, and his rubato appears as note deviations instead of tempo motion. Stage-4 test 2 exists specifically to catch this, and it is the misattribution a drummer would most resent.
4. **Per-note feel below ~15–20 ms is not recoverable on a free take.** Tracker error 15–18 ms median; tap error 12–16 ms after smoothing; repo's own tap-error model 30 ms. *He notices:* most of the deviation ribbon is greyed out as "inside the grid's own error".
5. **Level ambiguity is unresolvable in principle.** At the induction level "he played triplets" and "he sped up 1.5×" are the same observation (`beat.js:30-34`); with a pinned meter the conversion is fixed *by construction*, so the tempo-induction lens's "the system got it right on this take" is circular — stability is not correctness, which is exactly the LR3a lesson (random playing reads "locked" 62% of the time on grid fit). *He notices:* a passage notated in 16ths at 94 bpm that he played as triplets at 63, or vice versa. Mitigation is a human press, not an algorithm.
6. **Polyphonic syncopation collapse** until per-stream LHL lands. *He notices:* syncopation numbers that ignore his left hand entirely.
7. **Voice F1 0.859 against a 0.90 gate, ceiling 0.938 even given truth staves.** Tuning is exhausted and the repo recorded it. *He notices:* a left-hand arpeggio figure jumping staves mid-run — legible wrongness, not garbage, which is why it does not block the MVP.
8. **Grace notes detected and never written.** `onsets.js:20-22` detects them; the export contains 0 `<grace>` elements. *He notices:* his ghosted strokes and grace notes silently become ordinary notes or disappear into a chord.
9. **The tie clutter stays until the grid improves.** Median 7 ties and 19 note-pieces per bar on his take; the same engraver produces 0 ties on oracle beats. Do not retune the engraver.
10. **One session of 69 analysed deeply.** 46 have never been through the pipeline at all. `node arsenal/score_cli.mjs bench` would cost roughly 6 s of CPU and is the cheapest new evidence available.

---

## 13. What I did not verify

- I read the contract headers, params and the specific functions I cite in `beat.js` (43 KB), `meter.js`, `hands.js`, `measures.js`, `ribbon.js` — not all of them end to end. `layout.js`, `engrave.js`, `paint.js`, `marks.js` I did not open.
- I did not open the plan corpus beyond `tempo-meter.md` §§6.9–8 and targeted greps. `plan-amendments.md` (97 KB), `transcription.md` (60 KB), `critic.md` (39 KB), `ls1-rulings.md`, `rendering-formats.md` are unread by me. **Some of what I propose may already be specified or already ruled on there**, in particular the deviation layer and the bracket sanity gate. That corpus should be read before any of this is treated as new.
- My synthetic calibration is 4/4 ballad at 80 bpm, seeds 37/41/53, 32 bars — 9 takes plus the 9-piece free suite. I did not run 3/4, 6/8, or the other textures, and the `rung4Floor` recommendation of 5.0 is calibrated on that slice only. **It must be re-run across the full `gen.mjs` suite before it is committed.**
- I did not run `tests/score_hands.test.mjs`, `score_layout.test.mjs`, `score_fixtures.test.mjs`, `score_lab.test.mjs`, or `tests/test_score_export.py`.
- I did not open the lab page in a browser and did not test live Web MIDI. I did not measure the actual `onMidiMessage` handler delay (that is Stage 2's job, and it must not be pre-empted by assumption).
- I did not root-cause the single Verovio octave-shift warning.
- I did not test any install beyond confirming what is and is not importable. I did not test a madmom install; nothing I propose needs it.
- The tapped-grid noise floor in §2 uses the repo's own 30 ms tap-error model applied to synthetic truth beats. **His actual tap accuracy has never been measured.** If he taps to 10 ms the numbers improve substantially (5.2 ms sd at ±4); if he taps to 50 ms the tapped path fails. Measuring it is a two-minute drill and belongs at the front of Stage 3.

---

## 14. Files

Verified in this pass: `E:\AI-Setup\arsenal\web\piano\score\quantize.js` (`:13-14` cost model, `:38-45` params, `:48-53` λ tables, `:106-107` residual computed and discarded, `:143` `runnerUp` returned with zero readers, `:195` σ EMA discards it again, `:223` `sigma` default 40, `:253` clean output shape) · `beat.js` (`:69-87` params, `:85` `taps: 4 / tapValidBars: 4`, `:101` family ratios, `:122-129` ladder, `:127` steady gate, `:504-507` settled beat takes its own onset time, `:642` sample shape, `:669` `trackEvents`) · `index.js` (`:74` `rung4Floor: 8.0`, `:102/:104` fixed-beats injection bypasses the tracker, `:165` feel closes a segment, `:207` `tactusTime`, `:346` correct `sigma` pass, `:429` `beats_ms`, `:447` bar kind, `:500-501` the binding gate, `:606-607` note output, `:611` `rhythm`, `:665` `clean`) · `musicxml.js:369` (the beam defect) · `settle.js` (`:22`, `:31-36`) · `onsets.js` (`:31-37`, `:47-51`) · `midi.js:5-11` · `E:\AI-Setup\arsenal\web\piano.js` (`:2653` `noteOn` stamps `clock()`, `:3513` `onMidiMessage` discards `ev.timeStamp`, `:4602` fakes one) · `E:\AI-Setup\arsenal\score_cli.mjs` (`:91-97` `--taps`) · `E:\AI-Setup\tests\fixtures\score\gen.mjs` (`:209-247` `genTake`, truth shape at `:431-440`) · `E:\AI-Setup\arsenal\performance.py:1391` (the duplicate onset grouper with no shared fixture) · receipts `E:\AI-Setup\state\arsenal\score\ls1fix-r1-bench-2026-09-15.json` (`steadyShareRange [0, 0.068]`, LR3a) and `ls3-bench-2026-09-15.json` (`metricPooled bars: 2`) · export `E:\AI-Setup\state\arsenal\score\20260927-171534-085f6ee9\lens6full\`.

My probes, all in the scratchpad and disposable: `C:\Users\L5\AppData\Local\Temp\claude\E--\a90a987a-4b74-4e3e-9a06-cad82f47b6b7\scratchpad\` — `vandor_beamcheck.py` (chord-member beam count), `vandor_vrv.py` (Verovio error census and timing), `v_anchor.py` / `v_anchor2.py` (the anchoring artifact and the LOO ratio), `v_gen.mjs` + `v_gen.json` (synthetic truth vs `clean()`), `v_gate.mjs` / `v_gate2.mjs` (the `rung4Floor` sweep), `v_taps.mjs` (the tap rung is a count-in), `v_shape.py`. Nothing was written to the repo.