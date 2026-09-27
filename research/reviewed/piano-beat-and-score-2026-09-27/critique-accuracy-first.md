# critique:accuracy-first

_Verbatim agent return, workflow wf_fc6a68ac-233, 2026-09-27._

Verification complete. Findings below.

## Verified defects, ranked

**D1 — CRITICAL. Stage 1 (`rung4Floor: 8.0 → 5.0`), the design's self-declared "highest value per unit of work in the whole design", reverses a dated ruling and turns a green receipt red — one the author ran and reported.**

`E:\AI-Setup\arsenal\web\piano\score\index.js:71-74` carries its own calibration record: raised from 4.5 in 0.5 steps "until the precision of shown rung-4 bars held 0.80 on the held-out tempo suite (7.5: 0.772, 8.0: 0.856)". `E:\AI-Setup\research\in-flight\live-sheet-music-2026-09-14\plan-amendments.md:240` is the dated ruling with the full sweep (81 pieces, 2,592 bars, meter set to truth): precision at 4.5 / 5 / 5.5 / 6 / 6.5 / 7 / 7.5 = 0.657 / **0.681** / 0.697 / 0.710 / 0.709 / 0.728 / 0.772; at 8.0 = 0.856. And the live receipt prints it today — I ran `node tests/score_quantize.test.mjs`:

```
RECEIPT {"id":"LR4i","measured":{"rung4Floor":8,"precision":0.877,"shownShare":0.1474,...
 "belowGate":[{"rung4Floor":5,"precision":0.6981,"shownShare":0.4626,"shown":1199},...]},
 "threshold":"precision of shown rung-4 bars >= 0.80 at the rung-4 gate","pass":true}
```

So floor 5.0 trades precision 0.877 → **0.698** for shownShare 0.147 → 0.463: roughly a third of the newly drawn bars are wrong. LR4i goes red. The design reports "`score_quantize` **68/0**" — so it printed this receipt — yet §0.1 never mentions LR4i, and §8 Stage 1 names only LR3a as the receipt to hold, which is about random playing and is unaffected. `plan-amendments.md:240` also names the failure classes at the low floor: "289 bars whose lines sit on no true beat, 101 at another level or partial, 63 with wrong onsets, 9 with a wrong phase" — bar lines on no true beat is the worst possible artifact for a drummer.

Credit where due: the design's own numbers reproduce exactly. I ran `clean()` on `genTake` seeds 37/41/53, 4/4 ballad 80 bpm, 32 bars — rub0 at floor 8.0 gives `{tape:32}` on all three seeds; at 5.0 gives 30+19+25 = 74/96 metric. The measurement is honest. The *inference* — "a one-constant calibration defect ... set above what metronomic playing achieves" — is wrong. It is a deliberate precision/recall operating point, and §13 admits `plan-amendments.md` went unread, which is where the ruling lives.

**D2 — CRITICAL. On the operator's actual playing the change buys ~2% of ticks, because the binding constraint is the steadiness band, not the periodicity floor. The design asserts the exact opposite.**

I ran his session through the shipped tracker (`trackEvents` + `createOnsets`, 14,647 events, 4,633 note-ons, 3,919 ticks):

```
periodicity strength: p10 2.51  median 2.99  p90 4.21  max 8.28
bands:   { free: 2491, loose: 1246, steady: 182 }
drawing before the rung4 gate: { tape: 3750, bars: 169 }
floor 5.0 -> 93 of 3919 ticks pass (2.37%)     floor 8.0 -> 0
```

`tempo-meter.md:216` gives the reference bands: metronomic 6.9 / 8.4 / 11.3, mild rubato 4.1 / 5.3 / 7.5, strong rubato 2.5 / 3.2 / 5.5, random 2.2 / 2.7 / 3.2. His median 2.99 sits in the strong-rubato/random overlap — exactly what `tempo-meter.md:249` already concluded ("his wobble matches the strong-rubato synthetic set ... Expect rub2-like grid quality, with downbeat F near 0.17").

`drawing` is already `"bars"` on only 169 of 3,919 ticks (4.3%), because `beat.js:127` (`inferred.mode === "steady" ? "bars" : "tape"`) refuses 95.7% of ticks **before** `index.js:500` is consulted. §0.1 claims "The steadiness band is *not* the problem ... The periodicity floor at `index.js:500` rejects all of them." That is true on its synthetic rub0 slice and false on the only material that matters. And my gate run shows rub2 at floor 5.0 yields `{tape:34}`, `{tape:36}`, `{tape:35}` — **zero** metric bars on all three seeds, matching `plan-amendments.md:240`'s "rub2 shows none". Stage 1, run on the rubato level the repo says matches him, changes nothing.

**D3 — CRITICAL. The triplet/swing/sloppy rule does not solve the operator's core ask. The conditioning the design calls "load-bearing" censors precisely the evidence the rule needs, and on his take neither variant can ever output SWUNG or TRIPLET.**

From `score.clean.json`, 275 beats hold exactly two onset groups (40 ms merge). By the division the quantizer chose, with x = (t₁ − beatₖ)/P:

```
 d     n   min     p10   median   p90    max    sigma
 2   148   0.379  0.463  0.505  0.555  0.717   0.0388
 3    47   0.289  0.342  0.637  0.676  0.741   0.1375
 4    73   0.140  0.432  0.688  0.778  0.824   0.1653
```

The d=2 vs d=3 cost crossover under `quantize.js:13-14` (λ 0.5 / 2.0, P = 528 ms) is x = 0.597 at σ=20, **0.613 at σ=30**, 0.635 at σ=40, 0.700 at σ=60. The d=2 set is truncated right there — max 0.717, p90 0.555. Conditioning on "beats the quantizer read as d=2" therefore *deletes the swung pairs*, and σ_x = 0.0388 is the spread of a set selected for x ≈ 0.5, not a measure of his timing.

I reproduced both halves of the design's own observation, and the verdict flips with it. Conditioned: 172 usable pairs, median(x) 0.5053, σ_x 0.0374, E₃ = 1 → the rule says **STRAIGHT**. Unconditioned: n=275, median 0.5178, σ_x 0.1405, E₃ = 13 → the rule says **SLOPPY, refuses**. Neither path can emit SWUNG or TRIPLET. The design's thresholds make the two answers he actually wants unreachable on his own take.

Meanwhile the censorship-free histogram shows the real content — a primary mode at 0.50–0.55 (79 beats) and a genuine secondary shoulder at 0.60–0.80 (**79 beats, 29% of two-onset beats**). That is a plausible reading of his "strange rhythmic stuff that didn't come out how I wanted," and both variants of the rule are blind to it. The design writes "unconditioned, σ_x measured 0.024–0.140 and the rule said sloppy everywhere; conditioned, σ_x is 0.018–0.038 and it discriminates." It does not discriminate — it assumes the answer. This is a restatement of the problem, not a solution.

The circularity is compounded: on 164 of 172 eligible pairs (**95.3%**) the slot-0 note *is* the grid anchor (|t₀ − beatₖ| < 0.5 ms), and 855 of 1,084 exported beat times (**78.9%**) are exactly a logged onset. So P itself is one of his IOIs.

**D4 — HIGH. §3.4.2's `margin` is not a field pass-through; `cleanDivisions` never receives `runnerUp`, and the clean path produced every number the design cites.**

`divideBeat` returns `runnerUp` at `quantize.js:143`, and my repo-wide grep confirms zero readers (the two `tests/piano_spell.test.mjs:146,149` hits are an unrelated local). But `cleanDivisions` (`quantize.js:223-260`) calls `fitOf`, not `divideBeat`, tracks no second best, and its out object at `:253` has no `runnerUp`. The design says "`decide()` (`:199`) and `cleanDivisions()` (`:253`) carry it ... `cleanDivisions` at `:253` drops it. Add it there." Only the live path carries it. `index.js:346` — the path that wrote `score.clean.json` — uses `cleanDivisions`. Surfacing a per-beat margin in the export requires a second-best Viterbi quantity (second-best path, or per-beat local marginals), not a field. Consequence: the cited "seg2 beat 38 decided by **0.170**" cannot have come from the shipped clean pass, and is unverifiable as attributed.

**D5 — HIGH. Stage 0's `sigma` test cannot fail, and the exposure it names does not exist.**

§3.4.3 says "`bench.js` and the lab pages are the exposure." I read `bench.js` end to end (5,172 bytes): it imports only `measures.js` and `layout.js`, and contains no `cleanDivisions` and no `sigma`. `grep -rn cleanDivisions` over `arsenal/` and `tests/` returns exactly three call sites — `index.js:346`, `tests/score_quantize.test.mjs:244`, `:271` — and all three pass `sigma: q.sigma()`. The 40 ms default has zero live exposure, so the falsifier "Fails if any caller silently keeps the 40 ms default" is already satisfied. Making the argument required is fine hygiene; it is not the "latent trap that halves triplet recall."

**D6 — HIGH. Stage 0's Verovio test is unimplementable as specified, and it contradicts the design's own §3.7 rule.**

The defect itself is real and I reproduced it exactly with stdlib regex: **1,028 `<beam>` elements on `<chord/>` member notes, in 166 of 280 measures** (of 4,018 beams and 6,842 notes). The one-line fix at `musicxml.js:369` is correct. But the test is specified as "asserted in `tests/score_export.test.mjs`" — a Node suite — while the design verified the **Python** `verovio` (`py -c "import verovio"`). I confirmed absent from the pinned 3.11 (`C:\Users\L5\AppData\Local\Programs\Python\Python311\python.exe`), and there is **no `package.json` anywhere in the repo**, so no npm route either. §3.7's own law ("Python reads artifacts and argues with them") puts this in `tests/test_score_export.py`, which exists.

**D7 — MEDIUM. §4's "no surgery, one existing tested seam" overstates: the CLI cannot reach the fixed-beats seam Stage 3 depends on.**

Verified and credited: `index.js:102/:104` does bypass the tracker on fixed beats; `clean()` at `:665` accepts `beats`. Also verified and credited: `piano.js` has no consumer of the `header` model built at `index.js:537` / `meter.js:312-330` (grep finds only an HTTP `headers` hit at `piano.js:3776`), so "computed and thrown away for want of a HUD" holds. But `arsenal/score_cli.mjs:97` returns `{ span, meter, feel, one, bpm, taps, beats: null }` — hardcoded. `--taps` exists (`:91-96`) and `runTake` accepts `o.beats` (`:193`), but no flag sets it. Stage 3's continuous-tap path, which the design says is "the one TM5 needs," has no CLI route today.

**D8 — MEDIUM. The design's characterization of his rhythm is an artifact of un-merged chords, and the "one pulse, two subdivisions" premise fails its own test.**

`onsets.js:11` and `performance.py:41` (`ONSET_MERGE_MS = 40`) both merge note-ons within 40 ms into one group before the tracker sees anything. After that merge: 2,777 groups from 4,525 distinct onsets, median IOI **204 ms**, not 130. The census is broad and flat — 140 ms 13.3%, 160 ms 18.2%, 180 ms 17.1%, 200 ms 13.7%, 240 ms 10.2%, 280 ms 14.8%, 320 ms 17.7% — with no dominant subdivision pair. If 120 = P/4 and 160 = P/3 then P = 480 ms; measured, 480 ms IOIs are 2.49% and 960 ms 0.54%, so the putative pulse is nearly absent. Autocorrelation of the onset train over 150–1200 ms peaks at 160 ms at normalized strength 0.028 (top lags 160/320/330/660, all 0.021–0.028) — no tactus-scale periodicity, independently confirming D2. Local coexistence is real but a minority: 22.9% of 6 s windows carry ≥3 of both 120 and 160; 38.3% only 160; 35.7% neither.

**D9 — MEDIUM. §3.4.4's tuplet sanity gate is real but far smaller than billed.** Per-note residual vs the notated grid by chosen division: d=3 → n=499, median |e| 10 ms, p90 42, max 96. Notes exceeding half the triplet step (88 ms at P=528): **2 of 499 (0.4%)**; exceeding a quarter step (44 ms): 40 (8.0%). Worth doing, not a headline. The genuinely bad division is d=6 — median |e| 27 ms against an 88 ms step, n=106 — which the design does not gate.

**D10 — LOW. Factual slips and unread prior art that bears directly on the proposal.** The session is 13.18 min of note span (roll header `dur_ms=978963` = 16.3 min wall) with 4,633 notes, not "11.5 min, 4631 notes", and is not "one continuous take" — there is a single 104.7 s gap at t = 0.3 s. `margin` does not "exist at `quantize.js:143`"; `runnerUp: {d, cost}` does. `transcription.md:622` already ruled swing notation (Q6: "swing written as straight eighths plus `swing`, or as triplets"; "swing off until asked"). `tempo-meter.md:406-414` already specifies the offline tidy pass (§6.9) and the TM-D timestamp drill (§6.10), including the "±25 ms ... up to 69% of readouts" figure the design re-derives as its own.

## Claims that held

The self-anchoring law (§1) is the design's real contribution and it is **worse than stated**: on-beat n=1661 median |dev| **0.00 ms**, 52.4% within 0.5 ms, 57.9% within 2 ms; off-beat n=2940 median **19.50 ms**, 6.5% within 2 ms; and 855 of 1,084 exported beat times (78.9%) are exactly a logged onset. `beat.js:504-507` reads as described. Its answer to check #5 also holds: the `DeviationSet` join *is* computable from the shipped export today — I computed it — but it is meaningless on class C, and since 78.9% of beat times are his onsets, a class-B smoother is fit to already-contaminated input, which makes §9 more likely to fail than the design allows. All four test counts exact (133 / 68 / 84 / 40, 0 failed). Beam count exact. `<grace>` = 0, 280 `<sound tempo>`, 7 `<metronome>`. `midi.js:5-11`, `index.js:611`, `index.js:224`, `settle.js:22`, `beat.js:85/:101/:122-129`, `piano.js:2653/:3513/:4602`, `performance.py:41/:1391` all verified as cited. Library census: numpy 2.4.4, scipy 1.17.1, librosa 0.10.2, PIL 11.3.0, matplotlib 3.10.8 present; verovio, music21, madmom, mido, pretty_midi, partitura all absent from the pinned 3.11 — the design's correction of the notation lens is right, and `librosa.beat.beat_track` does accept `onset_envelope`.

**Not verified by me:** the LOO-residual statistics in §0.3/§2/§9 (I did not reimplement the smoother); the Verovio error census (not installed here, and I did not install it); the tapped-grid noise-floor simulation; the 3/4, 6/8 and non-ballad generator slices; whether class B inherits the anchoring — §9 remains the right experiment.

## Verdict

**Modify, substantially — and reorder.** The design's diagnostic core is genuine and its central discovery is correct and under-stated: the exported grid is interpolation through the player's own onsets (78.9% of beat times are literally his note times), which makes every per-note feel number in the current system a measurement of the anchoring, and the typed grid-provenance class that follows from it is the right architectural response. Two of its concrete fixes are real, cheap and should land now: the `musicxml.js:369` beam gate (1,028 bad elements, reproduced exactly) and the tuplet residual gate (smaller than claimed, and it should cover d=6, not just d=3). But the two things it ranks highest must not be built as written. Stage 1 is not a calibration defect fix; it is a 0.877 → 0.698 precision regression against a dated ruling the author did not read and a green receipt he printed and did not report, and on the operator's own playing it is worth 2.37% of ticks because the steadiness gate at `beat.js:127`, not the periodicity floor, is what refuses — so it delivers nothing where it matters while breaking what works. And the triplet-vs-swing rule, the operator's actual ask, is circular: conditioning on the quantizer's own d=2 reading censors the input set at exactly the crossover (x ≈ 0.613) that separates swung from straight, so the conditioned σ_x that the design reads as discrimination is the selection, and on his take the rule can only ever say STRAIGHT or refuse — never SWUNG, never TRIPLET — while 29% of his two-onset beats sit at x ≥ 0.60, visible only when you drop the conditioning. Rebuild that discriminator on the anchor-free interval ratio over all two-onset beats as a two-component mixture, and put Stage 3 (labelled takes, plus the CLI `--beats` flag that `score_cli.mjs:97` currently hardcodes to null) first, because the design's own §0.2 already proves inference will never notate his playing and every expressive claim downstream is gated on a class-A grid that does not yet exist.