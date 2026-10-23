# Grid-tracker research: IMM filtering applied to tempo and beat tracking (2026-10-22)

The final report of a research agent (Claude, web), lane `imm`, from the grid-tracker research workflow (run wf_4acc5ff4-38e). Each agent read the brief (grid-tracker-brief-2026-10-22.md) first. Persisted unedited per the full-fidelity rule.

---

# Multi-hypothesis beat tracking and metrical-level selection: findings for the grid tracker

## 1. Goto & Muraoka: BTS, 1994–2001

**Hypothesis.** Each agent holds (next beat time, inter-beat interval or IBI, beat type, reliability).
- 1996 build: 12 agents in 6 pairs. 1995 build: 28 agents in 14 pairs.
- Agents in a pair differ by strategy: frequency focus (all, low or mid bands), autocorrelation window (500 or 1000 frames of 11.61 ms), IBI search range (43–85 frames), and initial peak choice (largest or second-largest).
- Sources: [ICMAS96](https://staff.aist.go.jp/m.goto/PAPER/ICMAS96goto.pdf), [ICMC95](https://staff.aist.go.jp/m.goto/PAPER/ICMC95goto.pdf).

**Period.** Windowed, normalised vector autocorrelation (Goto & Muraoka 1996, eq. 1–2):
`Ac(τ) = Σ_{t=c-W..c} (o(t)·o(t-τ))·w(c-t) / Σ (o(t)·o(t))·w(c-t)`, with `w(t) = 1 - 0.5·t/W`. The IBI is the argmax of Ac inside the agent's IBI range.

**Phase.** A "prediction field" is the cross-correlation of the summed onset vector with a beat train at that IBI, over CcNumBeats = 12 past beats ([Goto 2001 JNMR](https://staff.aist.go.jp/m.goto/PAPER/JNMR2001goto.pdf), eq. 8–10). The agent then follows the peak that lies near the previous beat plus one IBI.

**Pair interaction (the defence against off-beat lock).** Each agent's beat time inhibits the matching neighbourhood of its partner's prediction field. If one agent tracks the midpoint between true beats, the other is pushed onto the true beat (ICMAS96). In the 1995 build the two agents also cover different IBI ranges, one faster and one slower, so that one survives a double- or half-tempo error.

**Reliability.**
- Goes up when the correlation-predicted beat matches the beat extrapolated from the last two beats, and down otherwise.
- Goes up when eighth-note chord changes fall on beats rather than on the eighth-note positions between them.
- Gets a further boost from drum-pattern match: detected BD/SD onsets are quantised to a 16th grid and matched against 8 stored patterns with weights O=1.0, o=0.5, .=0, x=−0.5, X=−1.0. Wrong-place hits therefore count against a hypothesis.
- A strong match marks the IBI as the quarter note (JNMR 2001, Fig. 11).

**Winner.** The manager groups hypotheses by beat time and IBI and sums reliability within each group. It takes the top group, repeats the grouping three times with a narrowing beat-time margin, and outputs the most reliable member (ICMAS96).
- Hysteresis 1: the beat type is only overwritten when the chord-change possibility is high compared with its recent maximum. Otherwise strong and weak beats keep alternating as before.
- Hysteresis 2: once reliability is high, an agent narrows its own IBI range.

**Metrical level.** Hard tempo prior of 61–185 BPM, a 4/4 assumption, then drum patterns or chord changes for the half-note and bar levels. Residual failures: an IBI of 0.75× or 1.5× in 2 of 45 drum songs, and an eighth-note displacement under heavy syncopation (JNMR 2001 §4.1).

**Licence.** I found no public code (UNVERIFIED).

## 2. Dixon: BeatRoot, 2001 and 2007

Sources: [Dixon 2001 TR/JNMR](https://www.ofai.at/papers/oefai-tr-2001-19.pdf), [Dixon 2007](https://webspace.eecs.qmul.ac.uk/s.e.dixon/pub/2007/jnmr07.pdf).

**Tempo induction.**
- Takes the inter-onset intervals (IOIs) between every pair of onsets, not just neighbours, and clusters them greedily with a 25 ms width. Clusters whose means drift together are merged.
- Each cluster is scored by its size plus a relationship term from related clusters: `score_i += f(d)·size_j` whenever `|I_i − d·I_j| < 25 ms`.
- The relationship factor is `f(d) = 6−d` for 1≤d≤4, `1` for 5≤d≤8, and `0` otherwise. I checked this against the worked example (C1 = 49) and against its restatement in IBT eq. 4.
- Octave-related tempi therefore vote for each other.

**Agents.**
- One agent is created per (tempo hypothesis, onset within the first 5 s).
- Inner window: ±40 ms. Outer window: 20% of the IBI before and 40% after (asymmetric because slowing down is more common).
- An onset in the inner window is accepted. Missed beats in between are interpolated, the IBI is updated as `IBI += err/CorrectionFactor` (value UNVERIFIED), and the score is updated as `score += (1 − relErr/2)·salience`, which is 0.5–1.0× salience.
- An onset in the outer window is accepted too, and the agent also spawns a clone that rejects it.

**Kill rules.**
- Duplicate: IBI within 10 ms and phase within 20 ms. The lower score dies.
- No matching onset for TimeOut seconds (value UNVERIFIED).

**Winner.** The highest cumulative score at the end of the piece. This is offline, so there is no causal switching.

**Metrical level.** BeatRoot has no explicit level selection. Its summed-salience score "is known to favour lower (faster) metrical levels" (Dixon 2007). On 1360 excerpts it tracked 613 at 1:1 and 535 at 2:1 ([Oliveira et al. 2010](https://archives.ismir.net/ismir2010/paper/000050.pdf), Table 2).

**Licence.** **GPL** (stated in Dixon 2007). Read the papers only.

### Causal successor: IBT (Oliveira, Gouyon, Martins & Reis 2010)

IBT is the closest published causal form of BeatRoot.
- Inner window ±46.4 ms. Outer window 0.2·P before and 0.4·P after.
- An inner-window hit updates `P += 0.25·err`.
- An outer-window hit spawns 3 children: phase-only, period-only, and half of each. Children inherit 80% of the parent's score.
- Scoring: `Δs = (1 − |err|/T_out)·(P/P_max)·SF(m)` for an inner hit, and `Δs = −(|err|/T_out)·(P/P_max)·SF(m)` for an outer hit. The `P/P_max` factor holds fast tempi back, so a finer grid cannot win just by predicting more beats. That is your parsimony rule in one term.
- Kill rules: duplicate (11.6 ms period, 23.2 ms phase); score more than 80% below the best; 8 consecutive misses; weakest agent when the pool is full at 30.
- The causal referee outputs the current best agent at every frame, with no explicit hysteresis.
- **Licence: GPL** (the paper says so). Do not copy.

## 3. Bar-pointer models

### Whiteley, Cemgil & Godsill 2006

Source: [ISMIR 2006](https://archives.ismir.net/ismir2006/paper/000044.pdf).

**State.** `X_k = [m_k, n_k, θ_k, r_k]`: bar position, tempo (velocity), meter, and rhythmic pattern.
- Position: `m_{k+1} = (m_k + n_k − 1) mod (M·θ_k) + 1`.
- Tempo: stays with probability `1−p_n` and moves ±1 with `p_n/2` each (p_n = 0.01).
- Meter and pattern can only switch when the pointer wraps past the bar end (p_θ, p_r = 0.1).

**Observation.** Onset counts are Poisson, with a Gamma prior whose mean is a hand-built pattern function `µ(m, r)`. The paper uses "duplet" and "triplet" bar patterns, which is exactly your subdivision family. The pattern has a noise floor between peaks, so off-grid onsets score low. With the Gamma integrated out:
`p(y|m,r) = b^a Γ(a+y) / (y! Γ(a) (b+1)^{a+y})`, where `a = µ²/Q` and `b = µ/Q`.

**Inference.** Exact forward filtering, `α_{k+1} = O_k Aᵀ α_k`, which is causal. Settings: M = 1000, N = 20.

**Results.** It correctly kept a constant tempo through a bar of triplets, and through two bars without eighth notes (which naively reads as half tempo).

### Krebs, Böck & Widmer 2015

Source: [ISMIR 2015](https://www.cp.jku.at/research/papers/Krebs_etal_ISMIR_2015.pdf). The paper text is CC BY 4.0.
- **One position state per audio frame:** `M(T) = round(4·60/(T·Δ))` per bar. Tempo states are spaced logarithmically, matching the 2–5% just-noticeable difference.
- **Tempo may change only at beat positions** (eq. 9), with probability `f = exp(−λ·|ṅ_k/ṅ_{k−1} − 1|)`. The best λ was 125 for the RNN beat tracker and 95 for the GMM bar tracker.
- At λ = 125: a 2% jump has relative weight e^−2.5 ≈ 0.08, a 5% jump e^−6.25 ≈ 0.002, and a halving e^−62.5. Once locked, the octave is effectively frozen, including a wrong octave.
- Accuracy rose on 32 of 33 test cases, with up to +20% relative CMLt.
- States fell from 11,520 to 5,617 (RNN tracker) and from 133,200 to 26,716 (bar tracker).

**Metrical level.** Bar-pointer models do not choose a level by score. The level is fixed by beats-per-bar, the pattern and the tempo range (55–215 BPM).
- [Krebs, Böck & Widmer 2013](https://archives.ismir.net/ismir2013/paper/000051.pdf) used a two-band onset feature (below and above 250 Hz) with 2-component GMMs tied per 16th-note cell. Modelling patterns this way "drastically reduces octave errors".
- For a half-time track, a "kick 1 + snare 3 at 140" pattern and a "backbeat at 70" pattern explain the same audio. Only the tempo prior or the seed separates them.

**Licences.**
- [madmom](https://github.com/CPJKU/madmom/blob/main/LICENSE): code BSD-2-Clause, but models and data are **CC BY-NC-SA 4.0 (non-commercial)**.
- [bayesbeat](https://github.com/flokadillo/bayesbeat): code BSD, models and data **CC BY-NC-SA 4.0 (non-commercial)**.

**Real-time cost (my own estimate, not measured).** At beat level with hop 512 at 44.1 kHz (Δ = 11.61 ms) and 55–215 BPM:
- M ranges from 24 to 94, giving 71 tempo states and about 4,200 states in total (about 17k at bar level).
- Each frame is one shift plus a 71×71 product at the beat states, about 10k flops, which numpy handles far faster than 20× real time.

## 4. What this means for the brief

**Scoring.** Use IBT-style signed, period-normalised scoring, plus Goto-style negative weights for off-grid hits. Off-grid notes then count against a grid, and a finer grid cannot win just by having more beats.

**Merging.**
- Duplicates: within about 10–12 ms in period and 20–23 ms in phase.
- Octave families: BeatRoot's `f(d)` gives the voting weights (step 4 of the skeleton).
- Winner: Goto's grouped reliability sum with three narrowing passes.

**Hysteresis.**
- Make scores leaky and cumulative, never a per-frame argmax, which is what IBT does.
- Allow tempo changes only on beats (Krebs 2015).
- Let the level or family switch only at bar ends (Whiteley's switching rule).

**IMM mapping (my proposal).** Make volatility a hidden regime variable with two values of λ, for example ~125 to hold and ~10–25 to follow (Krebs Fig. 2 plots 10/25/100). Let it switch at bar ends with probability p, the same way Whiteley switches r and θ. That is Daniel's stable/volatile pair as one exact forward filter.

**Off-beat bass.** Goto's paired agents with mutual inhibition are the published defence against the off-beat lock in the receipts. BeatRoot's outer-window branching also keeps the off-beat reading alive as a separate hypothesis instead of snapping to it.
