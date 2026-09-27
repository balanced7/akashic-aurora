# design:realtime-first

_Verbatim agent return, workflow wf_fc6a68ac-233, 2026-09-27._

All three suites green (133/0, 68/0, 84/0), and `noteOn(m, vel)` at `piano.js:2651` stamps `clock()` at `:2653` — the MIDI event's own timestamp never reaches it. I have what I need.

---

# Tempo tracking and score transcription: architecture

## 0. Where I disagree with the grounding

All four lenses are right that the capability exists (`arsenal/web/piano/score/`, 5,459 lines, 18 modules). I re-ran the suites: `score_beat` **133/0**, `score_quantize` **68/0**, `score_export` **84/0**. The base is green. Three corrections, each measured:

**(a) "The grid is early by 3–6 ms, so bias removal is mandatory" is wrong, and shipping it would corrupt the feature.** The quantization-feel lens made bias removal design-rule #1. The cause is structural, not bias. `beat.js:504`: `let t = b.g ? b.g.t : b.t` — a settled beat that hits an onset *takes that onset's time*. `onsets.js:68`: a group's time is its **first note's** time. So:

```
on-beat notes that ARE their group's leading edge   n=935   93.2% have deviation EXACTLY 0,  median +0.00
on-beat notes that are NOT the leading edge         n=726   median +10.0, mean +14.6   <- the "bias"
within-chord offset from leading edge (multi-note)  n=3072  median +4.0, p90 +28.0, max +100
```

The "+3 to +6 ms late" is **chord spread measured against the chord's own leading edge**. Subtracting it as tracker bias subtracts his voicing and hand-spread from his timing. Do not remove it. Measure it separately and call it what it is: spread, a left-hand/right-hand fact, not a pulse fact.

**(b) "Fit a smooth tempo curve, measure residuals against it" (TM4, endorsed by the realtime lens) is falsified on this data.** I fitted a second-difference-penalised smooth (Whittaker–Henderson) to the 1,084 notation beats:

```
lam=0   (the notation grid itself)  beat residual sd   0.0 ms
lam=10  (mild smooth)              beat residual sd  43.7 ms   |dev| median 12.0 -> 21.3
lam=100                            beat residual sd  71.0 ms   |dev| median 31.0
```

If the beat sequence were "tempo plus jitter," a mild smooth would sit a few ms off it. It sits **43.7 ms** off. The sequence contains large fast excursions — tactus indecision, not rubato (IBI p10 472 / p90 735 ms, ratio 1.56, against a rubato threshold of 1.08). Residuals against a smooth curve would be dominated by the tracker changing its mind. **Do not build the tidy pass as the feel substrate.**

**(c) The margin is worse than "computed and unread."** `divideBeat` returns `runnerUp` (`quantize.js:143`) and nothing reads it — confirmed by grep. But notation comes from `cleanDivisions` (`index.js:346`), and **`cleanDivisions` never computes a runner-up at all** (`quantize.js:223-262`). The notation path has no margin to surface. That is a new seam, not a wiring job.

## 1. The measurable atom, and the coverage number

Given (a) and (b), there is exactly one well-posed quantity: **phase within a beat span whose both endpoints are onset-anchored.**

For a span bracketed by settled beats at `t_a`, `t_b` where both carry `b.g`, a note at `t` has `φ = (t − t_a)/(t_b − t_a)`. φ is a pure ratio — it needs no stable tempo, no smooth curve, no global model. It is exactly what "did he rush that 16th" means at that instant.

Measured on his session, restricted honestly:

```
beats 1084   onset-anchored 855 (78.9%)   interpolated 229 (21.1%)
spans 1083   BOTH ends anchored  720 (66.5%)   <- the reportable coverage
```

**Two-thirds coverage is the honest headline.** One third of his take cannot carry a feel number at all, and the UI must say so rather than interpolate through it.

On those 720 spans (n=3367 notes), independently of the grounding's method and grid:

```
grid fit (|dphase|, median)    duple 16ths 0.0180 (11.4 ms)   triplets 0.0498 (31.5 ms)   both 0.0151 (9.5 ms)
swing, offbeat mode 0.5073 -> ratio 1.030    bootstrap 95% CI on median [1.049, 1.073]
subdivision by minute: min 5-6 TRIPLE (31 vs 70), min 11-12 TRIPLE (98 vs 137), min 8-9 and 10-11 mixed
```

This **replicates the tempo-induction lens exactly** (it found minutes 5–6 and 11–12 triple, swing 0.98) from a different grid and a different method. Two independent measurements agreeing is the strongest evidence in this whole exercise: **he plays straight 16ths at ~87–114 bpm with two decisive triplet passages.** That is the answer to "the strange rhythmic stuff." The task brief's "120/160 ms two coexisting subdivisions" hypothesis is not supported — the quantization lens showed it is bin-edge artifact over four tempo sections, and I confirm the subdivision switches *across* the take rather than coexisting within it.

## 2. The finding that sets the build order

I injected known microtiming into synthetic performances (off-16ths −6 ms, off-8ths +4 ms), ran them through the **real** `beat.js` + `onsets.js` via `trackEvents`, and measured how much came back. Tempo noise fixed at a 4% per-beat random walk (near his wobble); 5 seeds, median:

```
 jitter  wobble med/p90 |  recovery s1 / s2 / s3   | sign stable across seeds?
   0 ms   2.7% / 10.5%  |    90%   94%   81%       | y NO y
   4 ms   2.8% / 11.2%  |    74%   93%   72%       | y y y
   6 ms   3.0% / 11.2%  |    81%   86%   85%       | y y y
   8 ms   3.4% / 14.4%  |    55%   40%   61%       | y y y
  10 ms   3.8% / 15.7%  |    33%   39%   36%       | NO y y
  12 ms   4.2% / 16.1%  |    41%   -8%   43%       | y NO NO
  15 ms   4.9% / 18.1%  |    34%  -37%   74%       | y NO NO
  20 ms   5.4% / 18.1%  |    49%   74%   35%       | NO NO NO
  25 ms   6.0% / 19.2%  |    63%   21%   23%       | NO NO NO
```

Read the last column. **At 12 ms of timestamp jitter and above, the recovered sign is not consistent across random seeds.** The system would tell a drummer he plays his off-16ths late when he plays them early, and which way it told him would depend on luck.

Below ~6 ms, recovery is 72–94% and the sign is stable everywhere. **The mechanism works. The measurement chain is what breaks it.**

And the chain is broken today. `piano.js:3513` `onMidiMessage(ev)` reads `ev.data` and never `ev.timeStamp`; it calls `noteOn(m, vel)` (`piano.js:2651`), which stamps `const t = clock()` (`:2653`, `clock` at `:673`). The MIDI event's own hardware timestamp is discarded and replaced with whenever the handler happened to run. The only place `timeStamp` appears is the synthetic injection path (`piano.js:4602`), where nothing reads it.

So: the timestamp is not "the highest-leverage unfixed item" (tempo lens) or "a root-cause item" (realtime lens). **It is a hard blocker that inverts the sign of the deliverable.** Everything else is downstream of it.

One nuance I'll correct: `tempo-meter.md:417` calls this "render-frame delay." `onmidimessage` runs as its own task, not on the render frame, so the true delay is task-queue latency — smaller than a frame but jittery under WebGL main-thread contention. Its actual magnitude is **unmeasured**, by them and by me. Stage 1 measures it.

## 3. Components and seams

Nothing new is needed upstream of notation. Four seams, three of them small.

### S1 — `midiIn` (fix, `arsenal/web/piano.js`)
`onMidiMessage(ev)` → `noteOn(m, vel, tHw)` where `tHw = ev.timeStamp` mapped into the page clock once at first event (`ev.timeStamp` and `performance.now()` share an origin under Web MIDI). Keep `clock()` as the fallback when `timeStamp` is absent, and **log both**, so the delta is measurable forever rather than assumed.

Contract addition to the event record: `t_ms` (as today) plus `t_hw_ms` and `src: "hw" | "clock"`. Additive, so every one of the 69 existing sessions still reads.

### S2 — `feel` (new pure module, `arsenal/web/piano/score/feel.js`)
The only genuinely new organ, and it is small (~150 lines). Pure ES module, no DOM, no clock, same shape as its siblings.

```
createFeel({ params })
  .observe(span)     // { tA, tB, anchoredA, anchoredB, items:[{id, t_ms, slot, d}] }
  .profile(segId)    // the aggregate
  -> FeelProfile
```

Typed output, one record per placed onset:

```
dev: {
  phase:   (t - tA)/(tB - tA)            the atom. dimensionless, tempo-free
  slotPhase: phase - k/d                 signed offset in beat fractions
  ms:      slotPhase * P                 DERIVED, for display only
  P:       tB - tA
  anchored: true                         false => phase omitted entirely, not estimated
  spread:  t - groupLeadT                chord spread, kept SEPARATE from timing (finding (a))
  sigma:   the per-beat sigma of the decision   (exists at quantize.js:199, discarded)
  margin:  cost(runnerUp) - cost(chosen)       (new in cleanDivisions)
  gridId:  { rev, segId, beatsHash }           invalidation stamp
}
```

Aggregate, per (segment, d, slot, stream):

```
{ n, meanMs, sdMs, systematic: |mean|/sd, ciMs: [lo,hi] (bootstrap), coverage: anchoredSpans/allSpans }
```

Three rules the measurements force:

- **`phase` is primary, `ms` is derived.** 10 ms at 87 bpm and 10 ms at 230 bpm are different musical facts.
- **`anchored: false` means the field is absent, never interpolated.** 33.5% of spans, and the UI shows a gap.
- **Never report slot 0.** Recovery sd on the beat slot was **exactly 0.0** — structurally unmeasurable. "Your beat placement" is not a sentence this system may say. Only sub-beat placement.
- **`systematic = |mean|/sd` gates display.** The grounding measured 0.003–0.55 on real slots: the systematic part is at most half the noise. Below 1.0, grey the number or withhold it.

### S3 — `cleanDivisions` returns a margin (`quantize.js:223`)
The Viterbi keeps per-cell costs already; return the second-best `d` and its cost delta alongside each decision. Two consequences: a tuplet bracket decided by 0.17 on a scale where penalties are 1.6 gets drawn as ambiguous instead of as fact; and the three spurious d=3 beats at 480–560 s (deviations +41/−70, +74/−41, +22/−66 ms — two notes 73 ms apart smeared across a triplet grid) get caught by a max-|dev| sanity gate before they engrave as triplets. That failure mode is the one most likely to make him say the notation is lying.

Also fix the latent trap: `cleanDivisions`' `sigma` defaults to `QUANT_PARAMS.sigma0Ms` (40 ms) at `:223`. `index.js:346` passes `q.sigma()` correctly, but `bench.js` and the lab pages omit it, and at 40 ms triplet recall drops 14/14 → 6/14. Make `sigma` a required argument.

### S4 — `musicxml.js:369`, one conditional
```js
beam: beamOf.get(it), tuplet: k === 0 ? bracketOf.get(it) : null,
```
`tuplet` is gated to the chord's principal note; `beam` is not, so every `<chord/>` member carries a duplicate `<beam>`. I verified the code shape and the asymmetry directly. The notation lens measured 1,028 offending elements and 1,016 Verovio errors → 0 after stripping; **I did not install Verovio or reproduce that count.** The fix is `beam: k === 0 ? beamOf.get(it) : null`, plus a Verovio-load assertion in `tests/score_export.test.mjs` so a foreign consumer guards the export from here on.

### Where analysis lives
**In the browser, single-source, in pure JS.** Not a preference — the log is engineered for durability, not promptness: `log.js:146` `flushMs = 1000`, IndexedDB-buffered, backing off to one upload per 60 s when the server is unreachable. Feeding a live analyzer from it would fight its design. In-page, an onset is available 40–60 ms after its first note (`onsets.js:31`), the tick is 250 ms (`beat.js:70`), and the causal tick costs 0.033 ms mean / 0.156 p95. Python stays the adversarial verifier (`tests/test_score_export.py`), never a second tracker.

One drift landmine to close while we're here: `performance.py:1391` already groups onsets in Python at `ONSET_MERGE_MS = 40` with a comment pointing at `onsets.js`, and there is **no shared fixture between them**. `onsets.js` has since grown near-chord, roll merging and grace detection that the Python has not. Either delete the Python grouper in favour of reading the CLI's output, or give the pair a shared fixture the way `tempomap` has one.

## 4. Algorithms, and why over the named alternatives

**Beat tracking: keep multi-agent (BeatRoot) — `beat.js:132`.** Over global autocorrelation/tempogram, which returns "confident noise": whole-take max r was 0.0344 with seven rivals inside 14% of it, and `argmax` still names a winner. Over DP (Ellis/librosa), which is non-causal by construction and, fed this exact onset envelope, returned 162.16 bpm — a 1.88× octave error from its 120 bpm prior — while holding IBI to ±12% against a real 39% tempo range. Over a bar-pointer HMM, which is the principled answer and resolves metrical level structurally, but costs 1,000+ lines and scores 56.5 F on live performance in the literature. Multi-agent is the only family that keeps runners-up alive, which is what makes the ÷2 / ×2 / 2↔3 buttons a one-press fix rather than a rebuild. Note the honest reason to pay for agents: they do **not** improve the BPM number (induction alone Acc1 0.65 vs 0.61 with agents). They supply phase, a grid, and alternatives.

**Feel: phase within onset-anchored spans.** Over residuals-against-a-smooth-curve, falsified in §0(b) — 43.7 ms of beat residual at a mild smooth. Over deviation-against-the-notation-grid, which mixes 19.5% structural zeros into the statistic and is not a measurement of anything.

**Syncopation: Longuet-Higgins & Lee, per stream.** Over Keith 1991, which is unnormalised and on real polyphonic bars is a note-density proxy — the grounding measured corr −0.118 with LHL and showed it ranking a dense run above a sparse displaced figure, which is backwards. Over WNBD, which is bounded and smooth (corr +0.596) but knows only the beat, not the bar, so it cannot tell a displacement on beat 4 from one on beat 1 — keep it as a secondary gradual number. LHL wins for one decisive reason: **its score is attributable to a specific note**, so you can point at the staff and say "this one, 3 units." For a drummer, the monophonic-grid limitation is fatal (kick on 1 plus displaced snare must not score as nothing on 1), so take the **Sioros & Guedes 2011** polyphonic/velocity-weighted extension, computed per stream from `hands.js` voices and `onsets.js` velocities, both of which already exist.

## 5. Triplets, swing, syncopation

**Triplets.** Already handled and already correct on this take: the shipped grid detector read 3 tatums on 22% of ticks, `cleanDivisions` as `index.js:346` calls it catches 14/14 clean triplets, and 285 tuplet brackets are in the emitted MusicXML. My independent phase measurement agrees on *where* (minutes 5–6, 11–12). The real issue is not detection, it is **hysteresis lag**: `meterHold: 4` (`beat.js:83`) is what stops the display flickering and is exactly what lags a genuine feel change. Fix by surfacing rather than retuning — show the subdivision chip with its confidence, and let the 2↔3 family button be one press. The d=3 entry barrier is asymmetric by design (σ > 0.0575·P to enter, 0.1179·P to hold), so the **first triplet of a run** is the one at risk; that is the single beat the live pass missed on his take. The clean pass recovers it.

**Swing.** Report as a distribution, never a number: mode (not median — the median is pulled by the ¾ population), bootstrap CI, `σ_x` in ms, and n. His: **mode 0.5073 → ratio 1.030, CI [1.049, 1.073]**. Straight. The honest sentence is "straight eighths, ratio 1.03 (95% CI 1.05–1.07), n=1234" — and when `|mean|/sd < 1`, say "no measurable swing" instead of a ratio. A triplet with its middle note present is *not* ambiguous with a swung pair (3-grid rms 6.3–13 ms vs 4-grid 34–58 ms — a 3–7× signal). Only a triplet with the middle note *absent* is, and that is resolved phrase-level by whether the 1/3 position is occupied anywhere in the window.

**Syncopation ships last, and only after taps.** LHL needs committed bar phase, and a phase error of one beat rewrites every score in the bar. Inferred downbeat F is 0.578 overall and **0.173 on strong rubato** — and his wobble sits in the strong-rubato class. Syncopation on inferred phase would be noise with a number on it.

## 6. Microtiming preservation

It is already preserved on disk and nothing reads it back. `midi.js:5-11` writes **`performance.mid`** (PPQ 500, 1 tick = 1 ms, every logged onset at its true time, 0 ms error by receipt LR9b) *and* **`quantized.mid`** (PPQ 480, on the grid). Two layers, two files, and **no join between note *i* in one and slot *k* in the other.**

The missing artifact is the join table, and `index.js` already has stable `note.id`, `beats_ms` per measure (`:427-430`, exported at `:615`), and `perf: { t_ms }` per note. So `feel.js` needs no new data capture — it needs a `push` in `fitOf` and a field in two return objects.

**Deviations never enter MusicXML as notated content.** They live in a sidecar beside the two MIDI files. The score stays readable; the residual stays exact.

**Retirement rule.** The deviation layer is derived, never an atom. Every `dev` record carries `gridId = { rev, segId, beatsHash }`. When the grid changes — rebuild, family press, tactus or phase change — every deviation stamped with the old grid is **invalidated, not migrated**; a `dev` without that stamp is retired on sight. And if a tapped take shows the inferred rung cannot beat tape on his material (Acc1 < 0.5 or beat F < 0.5 at his wobble), retire the inferred rung from *notation* and keep it only for the `♩ ≈ 96` readout and the family buttons. The ladder already degrades to tape by design (`beat.js:122-129`), so retirement is a config change, not a deletion.

## 7. Build order, each stage falsifiable

**Stage 1 — the timestamp, and measuring what it was worth.** S1. Log `t_hw_ms` and `clock()` side by side for one session.
- *Passes if:* the measured `clock() − timeStamp` distribution has **sd ≤ 6 ms** on hardware timestamps, and his beat-to-beat wobble (currently med 4.4% / p90 18.2%) drops measurably on a comparable take.
- *Fails if:* sd stays above ~12 ms after the fix, or wobble does not move. That means his 18.2% p90 is his own rubato, not our noise — and then §2's table says the feel feature is **not shippable at any effort** and Stage 3 is cancelled, not deferred.
- This stage is cheap and it is the only one that can kill the project. Run it first for exactly that reason.

**Stage 2 — the three small correctness fixes.** S3 (margin + required `sigma`) and S4 (beam gating).
- *Passes if:* Verovio loads `take.musicxml` with **0 errors** (from 1,016), a Verovio-load assertion is green in `score_export`, triplet recall stays 14/14 with `sigma` required, and the three spurious d=3 beats at 480–560 s are flagged ambiguous rather than engraved.
- *Fails if:* gating `beam` to `k === 0` changes any existing receipt, or the margin gate flags more than ~5% of tuplets (then the threshold is wrong, not the code).
- Independent of Stage 1. Ship regardless.

**Stage 3 — `feel.js` and the deviation ribbon.** S2, gated on Stage 1 passing.
- *Passes if:* on the synthetic harness, injected microtiming is recovered at **≥70% with sign stable across 5 seeds** at the measured post-fix jitter; coverage is reported honestly (~66% on his take); and the per-slot table replicates across ≥3 independent segments at different tempi, as the grounding's did four-for-four on off-16ths.
- *Fails if:* recovery sign flips across seeds, or the per-slot means do not replicate across segments. Either means we are reporting our own noise.
- Surface as three layers: the score unchanged; a **deviation ribbon** under the staff (one signed tick per note, early left / late right) hosted in `ribbon.js`, which already interpolates against real `t` at `:372`; and a **feel card** per section carrying n, CI, and `|mean|/sd`.

**Stage 4 — taps, then syncopation.** `trackEvents` already accepts `taps` and `one` (`beat.js:669`); `score_cli.mjs` already accepts `--taps` and `--one`. He is a drummer; he can tap.
- *Passes if:* one tapped take moves that take from rung 4 (`rhythm: "unverified"`, 96% tape) to rung 3 with metric bars, and the tapped beats agree with inferred beats within ~8% on the steady passages.
- *Fails if:* tapped and inferred beats disagree on metrical level for more than ~20% of the take — which would mean the inferred rung is not merely uncertain but wrong, and notation should be tape-only until a bar-pointer model exists.
- **This is the cheapest high-value unbuilt thing in the lane.** Every `BEAT_PARAMS` value was tuned on synthetic playing (`tempo-meter.md:301` says so plainly); TM5 never happened; there is no labelled take in 69 sessions and ~132,000 events. One tapped take converts the whole lane from synthetic-tuned to measured.

What I would put in front of him **before any of this**, because it needs no notation and it is native to a drummer: the **tempo curve with a confidence band** over the piano roll he already has (`scripts/piano_roll_render.py`), and the **IOI histogram with subdivision lines drawn on it**. The second one shows him minutes 5–6 and 11–12 going triple, which is the actual answer to his question, and it costs a plotting script.

## 8. Honest limits, and how he notices

1. **One third of his playing carries no feel number** (33.5% of spans lack an anchored endpoint). He notices as gaps in the ribbon. Correct behaviour, but it will look like a bug unless labelled.
2. **His beat placement is unmeasurable, permanently.** Recovery sd on slot 0 was exactly 0.0. He will ask "am I pushing the beat?" and the honest answer is that this architecture cannot tell him — only where he puts things *between* beats. Answering that needs a metronome or a click reference, which is a different feature.
3. **Notation clutter is a grid symptom, not an engraving bug.** Median 7 ties and 19 note-pieces per bar on his take; the same engraver produces **0 ties and 0 brackets on oracle beats**. Do not retune the engraver. He notices as an unreadable page and will blame the notation.
4. **Every bar of his take is `kind: "tape"`, `rhythm: "unverified"`** (`index.js:611` certifies "inferred" only when nothing fell to tape). Across 18 sessions, 2 of 1,969 bars were metric. The system declines to vouch for his rhythm and that is already wired correctly. He notices as "why is there no bar line," and the answer is a true statement about the evidence.
5. **~69 changes/minute of notehead churn** in the provisional tail while a bar settles. For a drummer watching his own bar form, that flicker is the thing to tune.
6. **My recovery numbers are an optimistic bound.** My synthetic's wobble reached 6.0%/19.2% at worst; his measured is 4.4%/18.2% — comparable at p90, but his wobble comes from real playing with real tempo structure, not a random walk. Recovery at his actual wobble is bounded above by my table, not predicted by it.

**What I did not verify:** I did not install or run Verovio, so the 1,016 → 0 error count is the notation lens's measurement, not mine. I did not read all 697 lines of `beat.js` (contract header, params, `emit`, the settle loop, `ladder`, `trackEvents`). I did not open the lab page in a browser or test live Web MIDI. I did not read the 360 KB plan corpus, so some of what I propose may already be specified or ruled on there — `plan-amendments.md` and `tempo-meter.md` should be read before any of this is treated as new. I analysed one session of 69. I did not measure the actual handler delay — that is Stage 1's whole job, and my first drift sweep had a bug (`P` not passed, silently disabling the span filter) that produced a false "drift destroys recovery" result before I caught and corrected it.

## 9. The single riskiest assumption

**That his 4.4% / 18.2% beat-to-beat wobble is mostly our measurement noise rather than mostly his rubato.**

The whole design rests on it. If the wobble is dominated by the discarded MIDI timestamp, Stage 1 removes it, jitter falls under 6 ms, recovery lands at 72–94%, and he gets a feel ribbon that means something. If the wobble is genuinely his — a player who breathes 18% beat to beat — then the onset-anchored span is an intrinsically short, noisy baseline, §2's table puts us at the 12–15 ms rows where the **sign is not stable across seeds**, and no amount of engineering rescues it; the honest product becomes the tempo curve and the IOI histogram, and the microtiming ribbon never ships.

I cannot currently decompose the two, and neither can the grounding — the timestamp noise and his rubato are confounded in every one of the 69 sessions, because both were recorded through the same defective clock. Stage 1 plus one tapped take is the only experiment that separates them, which is precisely why it is Stage 1 and why it is allowed to cancel Stage 3.

**Files:** `E:\AI-Setup\arsenal\web\piano\score\beat.js` (`:504` the onset-anchored settle, `:122-129` ladder, `:669` trackEvents), `onsets.js` (`:68` group time, `:46-50` salience), `quantize.js` (`:106` the discarded residual, `:143` the unread runnerUp, `:223` the sigma-40 default and the margin-free clean pass), `index.js` (`:346`, `:427-430`, `:611`, `:615`), `musicxml.js:369`, `midi.js:5-11`, `ribbon.js:372`, `settle.js`, `hands.js`; `E:\AI-Setup\arsenal\web\piano.js` (`:3513` the handler, `:2651-2653` the clock stamp, `:673` clock, `:4602` the unread synthetic timeStamp); `E:\AI-Setup\arsenal\score_cli.mjs`; `E:\AI-Setup\tests\score_{beat,quantize,export}.test.mjs`; `E:\AI-Setup\state\arsenal\score\20260927-171534-085f6ee9\rt-lens\score.clean.json`.

**My probes** (scratch, disposable): `C:\Users\L5\AppData\Local\Temp\claude\E--\a90a987a-4b74-4e3e-9a06-cad82f47b6b7\scratchpad\{dev1.py,dev2.py,dev3.py,recover.mjs,sweep.mjs,cal.mjs,cal2.mjs}` — `cal2.mjs` is the jitter-threshold table and the one worth keeping as the Stage 3 acceptance harness.