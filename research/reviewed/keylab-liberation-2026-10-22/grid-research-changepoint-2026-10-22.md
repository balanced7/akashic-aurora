# Grid-tracker research: detecting real tempo changes fast without false alarms (2026-10-22)

The final report of a research agent (Claude, web), lane `changepoint`, from the grid-tracker research workflow (run wf_4acc5ff4-38e). Each agent read the brief (grid-tracker-brief-2026-10-22.md) first. Persisted unedited per the full-fidelity rule.

---

# IMM lane: two-volatility tempo filtering for the grid tracker

## 1. The IMM algorithm
Sources: Blom & Bar-Shalom 1988, IEEE TAC 33(8):780–783; Mazor, Averbuch, Bar-Shalom & Dayan 1998, IEEE TAES 34(1):103–123.

Setup: r models M_j, each with (F_j, Q_j, H, R_j). The Markov matrix is π_ij = P(M_j at k | M_i at k−1). These steps run once per measurement:

1. **Mixing probabilities:** c̄_j = Σ_i π_ij μ_i, and μ_{i|j} = π_ij μ_i / c̄_j.
2. **Mixed initial conditions:**
   - x0_j = Σ_i μ_{i|j} x_i
   - P0_j = Σ_i μ_{i|j} [P_i + (x_i − x0_j)(x_i − x0_j)ᵀ]
   - This is literally Daniel's "the volatile one gets guesses from the stable one".
3. **Model-matched Kalman filter, started from (x0_j, P0_j):**
   - x⁻ = F_j x0_j
   - P⁻ = F_j P0_j F_jᵀ + Q_j
   - ν_j = z − H x⁻
   - S_j = H P⁻ Hᵀ + R_j
   - K = P⁻ Hᵀ S_j⁻¹
   - x_j = x⁻ + K ν_j
   - P_j = (I − K H) P⁻
4. **Likelihood:** Λ_j = N(ν_j; 0, S_j). Compute it in the log domain.
5. **Mode probabilities:** μ_j = Λ_j c̄_j / Σ_l Λ_l c̄_l.
6. **Output only (not fed back):**
   - x = Σ μ_j x_j
   - P = Σ μ_j [P_j + (x_j − x)(x_j − x)ᵀ]

FilterPy's `IMMEstimator` (MIT, https://github.com/rlabbe/filterpy) does exactly this: `cbar = μ·M`, `omega[i,j] = M[i,j]μ[i]/cbar[j]`, `μ ∝ cbar·likelihood`. The cost is about r Kalman filters. With a 2-D state and r = 2–3, that is negligible against the 20× budget (my own derivation).

## 2. Mapping to beat tracking
The model is beat-indexed, with state x_k = [τ_k (next-beat time), Δ_k (period)]. It comes from Cemgil et al. and was reused by Shiu, Cho, Chang & Kuo 2008, IEEE Trans. Consumer Electronics 54(3):1369–1377 ([PDF](http://mcl.usc.edu/wp-content/uploads/2014/01/200808-Robust-on-line-beat-tracking-with-Kalman-filtering-and-probabilistic-data-association-KF-PDA.pdf)):

```
x_{k+1} = [[1,1],[0,1]] x_k + w_k      z_k = [1 0] x_k + v_k
predict(now): τ_k + nΔ_k > now ;  phase = (now − τ_last)/Δ
```

- **Skipped beats:** use F(γ) = [[1,γ],[0,1]] and Q(γ) = q[[γ³/3, γ²/2],[γ²/2, γ]]. This is Hainsworth & Macleod 2004, eqs. 15–16, citing Bar-Shalom.
- **Beats with no evidence:** run the time update only, and set μ ← Πᵀμ.
- **What the two models share and differ in:** both use the same F and H. They differ in Q, and optionally in R.
- **The key design choice is the measurement.** Cemgil et al. feed the Kalman filter a *tempogram*, a comb-filter score over all onsets, as a 2-D observation of (τ, log₂Δ). The alternative was the nearest onset. In their Table 3 the tempogram made tracking "more accurate and consistent". A higher filter order or the binary switch did not help on their test set.
- **So for us:** the grid-hypothesis scorer's (phase, period) output should be the IMM measurement, with H = I₂ and R taken from the score-peak width. Raw onsets should not be fed in.
- **Log period:** Cemgil warps the period to log₂ so it stays positive and tempo changes are relative. That makes the τ transition nonlinear. The options are an EKF, or keeping Δ linear and setting Q ∝ Δ² (my suggestion).

## 3. Published music trackers with switching or multiple models
I searched and found **no beat tracker using the Blom–Bar-Shalom IMM by name**. The search was not exhaustive.

- **Cemgil, Kappen, Desain & Honing**, JNMR pp. 259–273, 2000/2001 (the volume is cited as both 28(4) and 29(4), UNVERIFIED) ([PDF](http://hans.fugal.net/comps/papers/cemgil_2001.pdf)). The switch sits in the **observation noise**: a narrow Gaussian for normal beats and a broad one for outliers. The dynamics do not switch. Parameters were learned by EM.
- **Cemgil & Kappen 2003**, JAIR 18:45–81 ([arXiv 1106.4863](https://arxiv.org/abs/1106.4863)). A switching state-space model: the switch is the score location and the continuous state is tempo. Inference uses Rao-Blackwellised particle filters.
- **Hainsworth & Macleod 2004**, EURASIP JASP 2004(15):2385–2395 ([PDF](https://www.repository.cam.ac.uk/bitstreams/81a6d656-9be3-48f0-9a3d-ef096c02d985/download)).
  - A jump-Markov linear system with a 24-subdivision grid prior p(c) ∝ exp(−log₂ d(c)), where d is the reduced denominator. **This is Daniel's parsimony rule.**
  - It is offline and non-causal.
  - Metropolis-Hastings moves for doubling or halving the tempo were "counterproductive". Errors at plausible tempo ratios persisted.
- **Shiu et al. 2008, KF-PDA.** Causal.
  - It uses a validation gate with γ = 9 (99.7%).
  - PDA-II weights onsets by intensity distributions learned for beats and non-beats.
  - P-score was 87.3% against 74.1% for nearest-strongest onset on MIREX06.
  - The authors say PDA replaces Cemgil's switch.
- **Gu & Raphael**, ISMIR 2012 ([PDF](https://archives.ismir.net/ismir2012/paper/000145.pdf)), and **McDonald, McBride, Gu & Raphael 2021**, Annals of Applied Statistics 15(3) ([arXiv](https://arxiv.org/abs/1907.06244)). Switching Kalman filters over constant, slowing, speeding and accent regimes. Offline analysis only.
- **Krebs, Böck & Widmer**, ISMIR 2015 ([PDF](https://www.cp.jku.at/research/papers/Krebs_etal_ISMIR_2015.pdf)). A discrete HMM where tempo changes only at beats, with f = exp(−λ|ratio − 1|) and λ ∈ [1, 300] "for roughly constant tempo". This is the discrete counterpart of choosing Q.
  - Its implementation, madmom, has BSD 2-clause source code, but its **model and data files are CC BY-NC-SA 4.0, which is NON-COMMERCIAL**.
- **Naming trap:** Böck, Krebs & Widmer ISMIR 2014, "multi-model approach", means several RNNs, one per style. It is not dynamical multiple models.
- **Patent flag:** US 8,889,976 ([USPTO](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8889976)) describes switching Kalman filters with small and large observation-error models for tempo. Its claim scope and assignee are UNVERIFIED.

## 4. Process-noise choices
- **Tracking practice:** use near-constant-velocity models that differ only in Q. Zhang, Bar-Shalom & Watson 2011, JAIF 6(1) ([PDF](https://isif.org/files/isif/2024-01/jaif-june2011_article1.pdf)), used q₁ = 0.01 and q₂ = 2 m²/s³ (a 200× ratio) with sojourn times of 15 s and 20 s.
- **Transition matrix for a variable interval T**, for any pair of rates λ₁, λ₂ (generic form): with e = e^{−(λ₁+λ₂)T},
  `Π(T) = 1/(λ₁+λ₂)·[[λ₂+λ₁e, λ₁(1−e)], [λ₂(1−e), λ₁+λ₂e]]`, where 1/λ_m is the expected sojourn time.
- **Discrete form:** sojourn τ_i = T/(1 − p_ii). Attributed to Bar-Shalom, Li & Kirubarajan 2001; I only saw it in a secondary source (UNVERIFIED).
- **Rule of thumb:** set σ between ½Δa and Δa, where Δa is the largest change per step. Source: Labbe, *Kalman and Bayesian Filters in Python*, ch. 7 (text CC BY 4.0, code MIT).

**Starting values at 140 BPM (Δ = 428.6 ms).** These are my own derivations, UNVERIFIED, and should be tuned on the bench:

| item | value |
|---|---|
| steady model | σ_Δ ≈ 0.05–0.2 ms/beat, σ_τ ≈ 1–2 ms |
| volatile, step-following (a 140→128 step is 40.2 ms) | σ_Δ ≈ 20–40 ms/beat |
| volatile, ramp-following (the same change over 8 bars is 1.26 ms/beat) | σ_Δ ≈ 0.6–1.3 ms/beat; a third model may be worth adding |
| Krebs λ = 100, for comparison | about 1.4% std, roughly 6 ms/beat |
| R | hop 512 at 44.1 kHz is 11.6 ms, so σ ≈ 3.4 ms before sub-frame interpolation |
| Π per beat | p_ss ≈ 0.993 (about 60 s of steady tempo), p_vv ≈ 0.875 (about 8 beats); volatile share at equilibrium about 5% |

## 5. Pitfalls
- **An outlier looks like a manoeuvre.** Worked example (mine): with R = (5 ms)², one syncopated onset 40 ms off is 8σ for the steady model but about 1σ for the volatile one. The likelihood ratio is about e³¹, which overwhelms the 0.007 prior.
  - Result: the IMM flips on a **single** off-beat bass note and follows it. That is beat_a's failure again.
  - Fixes: a gate (γ = 9); a broad-R outlier mode (Cemgil); IMM-PDA (Houles & Bar-Shalom 1989, IEEE TAES 25(2):176–189); and measuring from the all-onset grid score.
- **Octave and phase errors are not Gaussian.** No Q moves the filter from 140 to 70, or from the off-beat onto the beat (Hainsworth's moves failed). Keep that choice in the discrete grid-family layer with hysteresis, and re-initialise the IMM when the family changes.
- **Off-beat capture.** Nearest or strongest-onset association grabs half-beat notes (Shiu Fig. 3). Hainsworth reports that without amplitude modelling the beat is assigned to "the most frequent subdivision". Accent weighting is needed.
- **Missing evidence.** Predict-only steps let μ drift toward Π's stationary distribution while P grows.
- **Models that cannot be told apart.** If R dominates S, the likelihoods are equal and μ never moves (my derivation; Li & Jilkov 2005 on model-set design, UNVERIFIED).
- **Per-hop rather than per-beat stepping.** Q and Π must then be rescaled per interval.
- **Numerics.** Use log-sum-exp, a floor on μ around 1e−6, and a symmetrised P or the Joseph form.

## Licences
| code | licence |
|---|---|
| FilterPy | MIT |
| Stone Soup ([GitHub](https://github.com/dstl/Stone-Soup)) | MIT; whether it has an IMM is UNVERIFIED |
| Labbe's book | text CC BY 4.0, code MIT |
| madmom | code BSD 2-clause, models CC BY-NC-SA (non-commercial) |

I found no GPL or AGPL code in this lane. I know of no released code for the papers above (UNVERIFIED).
