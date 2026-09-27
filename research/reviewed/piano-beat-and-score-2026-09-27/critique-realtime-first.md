# critique:realtime-first

_Verbatim agent return, workflow wf_fc6a68ac-233, 2026-09-27._

## Verified defects, ranked

I ran the three suites (`score_beat` **133/0**, `score_quantize` **68/0**, `score_export` **84/0** — the review's counts are exact), opened every file it cites, and re-derived its central measurement from the shipped artifact. Its arithmetic is mostly sound and replicates. Its **reasoning about what that arithmetic implies is wrong in a way that inverts the build order.**

---

### D1 — CRITICAL. The confound the review calls undecidable is measurable on existing data, and the answer kills Stage 3.

§9: *"I cannot currently decompose the two, and neither can the grounding … Stage 1 plus one tapped take is the only experiment that separates them."* False.

With `t_i = T_i + e_i`, `e` iid variance σ², and intended IOI `D` smooth over a short run, the IOI autocovariance separates them in closed form: `σ² = (γ0−γ1)/3 = (γ0−γ2)/2`. Validated against synthetics with known jitter (true 4 → est 4.1, 8 → 7.7, 12 → 10.8, 20 → 15.0 ms — **downward-biased above 8 ms, so every number below is a floor**):

```
20260927-171534   sd(independent) = 11.8 ms (lag1) / 14.5 ms (lag2)
                  79% of within-run IOI variance is independent noise, not tempo motion
ACROSS 39 sessions with >=5 isochronous runs:
                  median 11.8 ms   min 8.6   max 15.4   100% >= 8 ms   38% >= 12 ms
```

The alternation confound that would inflate this has signature `acf2 ≈ +1.00` (I reproduced it: swing ratio 1.2, zero jitter → σ̂ 18.2 ms, acf1 −0.49, **acf2 +1.00**). Real sessions show acf1 −0.16…−0.33 with acf2 near zero. The estimate is not aliased swing.

Now read the review's own calibration table at 12 ms: *"the recovered sign is not consistent across random seeds."* His data is already there. Stage 1 can only remove the clock component, and that component is bounded: pooling 15,605 two-note chord groups across 41 sessions, P(spread ≤ 1 ms) = 7.0%, against 7.1% predicted at σ_clock = 8 ms and 56.4% at σ_clock = 1 ms — and real chords are not simultaneous in intent, so 8 ms is a ceiling, not an estimate. Even granting all of it, `sqrt(11.8² − 8²) ≈ 8.7 ms` survives the fix. **Stage 1 is described as "the only stage that can kill the project." The existing data already ran it, and it does not pass.**

### D2 — CRITICAL. Stage 3's acceptance test fails on real data, today, without building anything.

I computed the review's exact atom from `state\arsenal\score\20260927-171534-085f6ee9\lens6full\score.clean.json` — `beats_ms` per measure plus each note's `pos` and `t_ms` — restricted to spans with both ends onset-anchored. Its coverage numbers reproduce to the note: **1084 beats, 855 onset-anchored (78.9%), 720 of 1083 spans (66.5%)**, IBI p10 472 / median 632 / p90 735 ms, ratio 1.56.

Removing the slot-0 common offset (+7.5 ms — without that removal every slot inherits the same anchoring offset and "sign is stable" is vacuous):

```
slot   n     dev(ms)   |mean|/sd   bootstrap 95% CI     split-half
  0  1367     -0.0       0.000     [ -0.9, +0.9]       (structural zero)
  6   394     -3.3       0.094     [ -6.6, +0.3]  <-0  -6.0 then -0.1  (60x change)
  8   142    +12.4       0.429     [ +7.5,+17.2]       +10.5 / +14.1
 12   842     -0.3       0.010     [ -2.1, +1.5]  <-0  -0.2 / -0.3
 16   229    -10.7       0.383     [-14.4, -7.0]       -3.5 / -13.9
 18   341     -5.3       0.183     [ -8.3, -2.2]       -5.5 / -4.9
```

The off-eighth — the single most musically loaded slot, n=842 — is **−0.3 ms with a CI straddling zero**. Every slot is below the review's own 1.0 display gate. The ribbon would render nothing, or render its own scatter (per-note sd 26–35 ms against an 11.8 ms noise floor).

### D3 — CRITICAL, self-inflicted. The display gate is the wrong statistic and suppresses the one true finding.

`systematic = |mean|/sd` is a per-note effect size. What is estimable is the per-slot *mean*, uncertainty `sd/√n`. The only slots with real, replicating, CI-excludes-zero signal on his take are the **triplet** slots (8: +12.4 ms, CI [+7.5,+17.2]; 16: −10.7 ms, CI [−14.4,−7.0]; both split-half stable) — middle of the triplet pushed late, last pulled early. That is a genuine drummer-legible fact about his playing, and the 1.0 gate withholds exactly it. Gate on a CI that excludes zero; keep `sd` for the ribbon's honesty band, not for the decision.

### D4 — MAJOR. Question 4: the core ask is restated, not solved.

Nothing in the tree infers swing. `feel` is a **user setting defaulting to "straight"** (`quantize.js:58-66`, `index.js:64,101`, `score_cli.mjs:86`); the alphabet is {1,2,3,4,6}(+8) with fixed λ (`quantize.js:48-53`) and **no swung grid exists**. The duple/triple call is made by λ + `continuity 0.8` + `barBack 0.8` in a Viterbi (`quantize.js:229-257`) — a prior, not a measurement. On his actual data the discriminand is a continuum, not classes: adjacent group-IOI ratios `a/(a+b)`, n=2347, form one broad hump at 0.5 — **35.8% within ±0.035 of 1:1, 11.3% near 2:1, 10.2% near 1:2**, and the 1:2 and 2:1 shoulders are near-symmetric (222 vs 221 pairs), which is not swing (swing is asymmetric). The review's "3–7× signal" describes clean cases; the mass of his playing is between the classes, so "ambiguous" is the honest answer most of the time and the proposed margin will usually be small. Also: a feel change **closes a segment** (`index.js:165`), so the 2↔3 press is not a cheap per-passage toggle, and the review conflates the tactus family button (`beat.js` `chooseLevel`) with the meter/feel chip (`index.js:626`, `meter.js:188-247`).

### D5 — MAJOR. The brief's coexistence case is real; the review dismissed it on no evidence.

§1: *"I confirm the subdivision switches across the take rather than coexisting within it."* On sliding 20 s windows of his group IOIs, **6 of 65 windows carry a substantial 4:3 population** against the window's modal IOI, and in three the 4:3 population matches or exceeds the 1:1 population (t=320 s: 21 vs 21; t=750 s: 16 vs 10 plus 14 at 3:2; t=590 s: 14 vs 11). Twenty seconds is about ten bars. Duple and triple coexist at exactly the scale where notation must choose, and the design has no per-passage mechanism.

### D6 — MAJOR. Stage 3 is gated on a grid the suite says is wrong half the time in his regime.

`score_beat`'s own LR2-detail, from my run: at rub2, **acc1 0.4425, beat F 0.4588**. His IBI p90/p10 = 1.56 puts him at or past that class. Everything downstream of the grid — φ, bar phase, notation — is conditioned on a metrical level that is right under half the time there. The review applies this correctly to syncopation (F 0.173) and not at all to φ, where it bites just as hard: the both-ends-anchored filter fixes a *missing* onset, not a *wrong level*.

### D7 — MAJOR. Realtime is optimistic by an order of magnitude; the settle rule is omitted.

§3 cites "an onset is available 40–60 ms after its first note (`onsets.js:31`), the tick is 250 ms (`beat.js:70`)". But group finality is `avail = max(a.t+win, a.t+rollSpanMs, previous open group's window)` (`onsets.js:177,183`) with `rollSpanMs 120`, and chains; and a beat settles only when the agent has run **two beats past it** — `if (last >= b.idx + 2 || !alive)` at `beat.js:503`. A both-ends-anchored span needs the later beat settled: **≈2–3 beat periods, i.e. 1.3–1.9 s at his median IBI of 632 ms.** The quoted 0.033 ms tick is CPU cost, not latency. Provisional notation can form live; the feel number cannot, and the design never says so.

### D8 — MAJOR. The ruler is built on the noisiest available statistic, and the review missed it while getting the adjacent point right.

Finding (a) is correct and important — I confirm the mechanism (`beat.js:504` `let t = b.g ? b.g.t : b.t`; `onsets.js:68` group time = first note's time; 19.3% of placed notes have deviation exactly 0; overall mean +7.4 ms, median +3.0) and agree the spread must not be subtracted. But φ is then built on that same anchor without noticing the anchor is `min()` — the highest-variance order statistic of the chord:

```
40% of groups are multi-note; spread median 14 / p75 24 / p90 32 / max 40 ms
the leading note is the LOWEST pitch in only 40% of them (which hand anchors changes note to note)
first-note minus group centroid: median 7.0 ms, sd 5.4 ms
```

That 5–7 ms of pure convention noise enters **both endpoints of every span** before any feel is measured. A salience-weighted centroid would cut it and costs nothing — `onsets.js:46-50` already computes salience. This is the cheap improvement the design should have proposed.

### D9 — MAJOR, dependency. Stage 2's gate needs an uninstalled library, unargued.

`py -c "import verovio"` and `node -e "require('verovio')"` both fail. Stage 2 passes only if *"Verovio loads `take.musicxml` with 0 errors (from 1,016)"* with a Verovio assertion green in `score_export` — a gate on an install the review never argues for, in breach of the house rule it quotes. The 1,016 → 0 figure stays unverified. What **is** verified: `lens6full/take.musicxml` holds 1,444 `<chord/>` members, of which **exactly 1,028 also carry `<beam>`** and **0 carry `<tuplet>`** — the `musicxml.js:369` asymmetry is real and the count is exact. Tuplets are 279 start / 279 stop (558 elements), not "285".

### D10 — MODERATE. The "missing artifact" already ships.

§6: *"The missing artifact is the join table"* and `feel.js` *"needs a push in `fitOf` and a field in two return objects."* But `index.js:606-607` already emits per placed note `id, bar, tick, pos, t_ms, perf:{t_ms}`, and `index.js:429` emits `beats_ms` per measure. **That is the join.** I computed the entire deviation table from the shipped `score.clean.json` with zero repo changes — which is how D2 exists. The true statement is that no consumer reads it.

### D11 — MODERATE. Overstated difficulty on the margin.

*"`cleanDivisions` never computes a runner-up at all"* is literally true, but the Viterbi row already holds every division's cost (`quantize.js:242` `row.set(d, {cost, from, ks, fit, coll, pairs, local})`) and that row is in scope in the backtrack loop (`:249-255`). A per-beat local margin is one line, not "a new seam."

### D12 — MODERATE. A claimed latent trap with no call site.

*"`bench.js` and the lab pages omit [`sigma`], and at 40 ms triplet recall drops 14/14 → 6/14."* Repo-wide, `cleanDivisions` has exactly three call sites — `index.js:346`, `tests/score_quantize.test.mjs:244`, `:271` — and **all three pass `sigma: q.sigma()`**. `bench.js` does not call it. Making the argument required is fine hygiene; the justification is fabricated and 14/14 → 6/14 is unverified.

### D13 — MINOR. Citations and numbers.

- `performance.py` is at `E:\AI-Setup\arsenal\performance.py`, not `scripts/`; `ONSET_MERGE_MS = 40` is at **`:41`**, `:1391` is a use site. The drift claim itself is correct (`arsenal/performance.py:1389-1393` is a bare 40 ms first-onset window vs `onsets.js:31-42`'s near-chord/roll/run/grace rules).
- `clock()` returns **seconds** (`piano.js:287` `nowSec = performance.now()/1000`, `:673`); `ev.timeStamp` is milliseconds. S1's `noteOn(m, vel, tHw)` with `tHw = ev.timeStamp` is a unit mismatch against `pageSec` (`:2616`). Small, but it is the make-or-break one-liner.
- Wobble 4.3% / p90 17.0% from the shipped grid, vs the review's 4.4% / 18.2%. "96% tape" matches nothing: 274/274 bars are tape, 32 of 4633 notes are.
- The brief's own numbers are worse: "1,806 gaps of ~0 ms" does not reproduce (759 note IOIs ≤ 5 ms; 842 in the 0–20 ms bin), and the clean "120 and 160 ms" peaks are actually 140–160 (300), 160–180 (262), 120–140 (209). The review was right to reject the brief's framing and wrong in its replacement (D5).

---

## What checks out (for calibration)

The timestamp discard is real and exactly as described: `piano.js:3513-3520` reads `ev.data` only and calls `noteOn(m, vel)`; `:2651-2653` stamps `clock()`; `:4602` passes a `timeStamp` nothing reads. Coverage numbers reproduce to the note. All 274 bars are `kind: "tape"`, `rhythm: "unverified"` (`index.js:611`). Finding (a) is correct and the design's refusal to subtract chord spread is the right call. Finding (b)'s direction holds (IBI ratio 1.56). The librosa rejection replicates: I get **161.50 bpm** at the default prior (review: 162.16), and `start_bpm=80` gives 83.4 bpm with IBI p10/p90 650/789 — range 1.21 against a true 1.56, exactly the flattening described. madmom, music21, partitura, mido, pretty_midi are all absent and the design correctly needs none. **Question 5 answers cleanly in the design's favour:** microtiming does not round-trip through the grid — `LR9b` passed in my run ("every on, off and CC64 crossing at the log's `t_ms`, 0 ms error", 437 exports), so `performance.mid` is lossless and the sidecar plan is sound.

## Verdict

**Modify, hard, and reorder.** The correctness half is good work that should ship as-is: Stage 2's `musicxml.js:369` beam gating is a real confirmed defect (1,028 elements, counted), the margin is a one-line extraction, and the tempo curve plus the IOI-with-subdivision-lines plot are the right first things to put in front of a drummer. The feel half should not be built as specified, and its gating stage should not be run: Stage 1 was framed as the experiment that could cancel Stage 3, but the existing 69 sessions already answer it — per-onset independent scatter is 11.8 ms (floor) with remarkable consistency across 39 sessions, at most ~8 ms of which can be clock, which lands the design in the band its own table calls sign-unstable; and when I run its exact atom on its own artifact, the off-eighth comes back at −0.3 ms with a CI straddling zero and every slot below its own display gate. The salvage is real but smaller and differently shaped than proposed: gate on standard error rather than standard deviation and the **triplet** slots do speak (+12.4 / −10.7 ms, CIs excluding zero, split-half stable), which is genuinely a statement about his phrasing; report it per passage with n and CI, never as a per-note ribbon whose ticks are 26–35 ms of scatter around nothing. And the question he actually asked — am I ahead of or behind the beat — is unanswerable by this architecture in principle, not in practice, because the grid is welded to his own onsets (`beat.js:504`); answering it needs an external reference, which means his taps or a click, which is the cheapest unbuilt thing in the lane and the only one that speaks to a drummer directly.