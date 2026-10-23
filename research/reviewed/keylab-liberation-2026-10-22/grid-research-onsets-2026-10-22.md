# Grid-tracker research: onset timing precision for real-time beat tracking (2026-10-22)

The final report of a research agent (Claude, web), lane `onsets`, from the grid-tracker research workflow (run wf_4acc5ff4-38e). Each agent read the brief (grid-tracker-brief-2026-10-22.md) first. Persisted unedited per the full-fidelity rule.

---

**Lane report: detecting real tempo changes fast without false alarms**

**Bottom line**
- Treat a tempo step as a shift in the mean of the stable model's per-beat innovation. Detect it with a two-sided CUSUM, then use a window-limited GLR to find the change time and the new tempo. The IMM regime probability alone is not a good enough alarm.
- Re-initialise from the estimated change time, not from the alarm time. In IBT, "reset" beat "regen" on both speed and false requests.
- A step under about 2σ per beat cannot be detected within 4 s at any sane false-alarm rate. The high-volatility model has to absorb those.

**1. Detectors** (z_n = innovation for beat n, divided by σ)

*CUSUM* (Page 1954). Lorden 1971 proved it asymptotically optimal; [arXiv 2210.05181](https://arxiv.org/pdf/2210.05181) restates this. The Page and Lorden bibliographic details are from memory and were not fetched.
```
S+ = max(0, S+ + z - k);  S- = max(0, S- - z - k);  alarm if max(S+,S-) > h
change estimate = last n where S was 0
```
- Delay ≈ ln(ARL0)/KL, where KL = δ²/2 per beat.
- Siegmund's approximation (one-sided): ARL ≈ (e^(−2Δb) + 2Δb − 1)/(2Δ²), with Δ = δ − k and b = h + 1.166 ([Maghsoodloo notes](https://www.eng.auburn.edu/~maghssa/INSY7330/Cusum-Control-Charts-M2013-Maghsoodloo.pdf)). The two-sided ARL0 is about half.

I computed the table below with that approximation. As a check, k=.5 with h=4 or h=5 gives 169 and 469, against the published 168 and 465.

| k | h | ARL0 (beats, two-sided) | delay at δ=1.5 | δ=2 | δ=3 | δ=4 |
|---|---|---|---|---|---|---|
| .5 | 5 | 469 | 5.7 | 3.9 | 2.4 | 1.7 |
| .5 | 6 | 1286 | 6.7 | 4.6 | 2.8 | 2.0 |
| 1.0 | 3 | 1036 | 6.4 | 3.7 | 2.0 | 1.3 |
| 1.0 | 3.5 | 2821 | 7.4 | 4.2 | 2.2 | 1.5 |

*Page-Hinkley* (Page 1954; Hinkley 1971, Biometrika, citation from memory):
```
m_T = Σ_{t≤T}(x_t − x̄_T − δ);  M_T = min_{t≤T} m_t;  alarm if m_T − M_T > λ
```
- It is a CUSUM against its own running mean, which slowly absorbs the new tempo.
- River's defaults ([docs](https://riverml.xyz/latest/api/drift/PageHinkley/); BSD-3) are min_instances=30, delta=.005, threshold=50 and alpha=.9999. Thirty beats is about 13 s of warm-up.
- The IMM already gives us a prediction to test against, so CUSUM on its innovations is the better choice.

*Window-limited GLR* (Willsky & Jones 1976; Lai 1998). I only saw these in a [secondary summary](https://www.emergentmind.com/topics/window-limited-generalized-likelihood-ratio-glr-cusum), so treat them as UNVERIFIED.
```
g_n = max_{n−W<j≤n} (Σ_{i=j..n} z_i)² / (2(n−j+1));  alarm if g_n > h
change time = argmax j;  new period T' = T + σ·mean(z[j:n])
```
- The window should be W ≥ ln(ARL0)/KL_min, and each beat costs O(W).
- My Monte Carlo run (Gaussian, W=16, 30–200 runs, so rough): h=7 gives ARL0 ≈ 950 beats, with delays of 13.6, 4.1 and 2.1 beats at δ = 1, 2 and 3.

*BOCPD* ([Adams & MacKay 2007](https://arxiv.org/pdf/0710.3742), which I read in full):
```
π_r = p(x_t | ν_r, χ_r)
P(r_t=r+1, x_1:t) = P(r_{t-1}=r, x_1:t-1) · π_r · (1−H)
P(r_t=0,   x_1:t) = Σ_r P(r_{t-1}=r, x_1:t-1) · π_r · H
normalise;  ν_{r+1} = ν_r + 1;  χ_{r+1} = χ_r + u(x_t);  r=0 gets the prior
H = 1/λ_gap
```
- Cost is linear in t per step. Pruning tail mass below 1e-4 brings the average down to O(E[r]) (paper §2.4).
- I measured 11 µs per beat in numpy with 128 run lengths, which is negligible against the 20× budget.
- My Monte Carlo run (new-mean prior N(0, 3²), H=1/500, alarm when P(r<12) > .5): ARL0 ≈ 2100 beats, with delays of 52, 4.9 and 2.2 beats at δ = 1, 2 and 3.
- That matches CUSUM on large steps but is much slower on small ones: the broad prior on the new mean penalises small shifts.
- The Gaussian version is fragile against outlier onsets. A β-divergence robust variant reports cutting the false-discovery rate from up to 99% to 0% ([Knoblauch, Jewson & Damoulas 2018](https://wrap.warwick.ac.uk/108049/); I saw the abstract only).
- Best use for us: its run-length posterior is a principled "age of the current tempo" input for the hysteresis rule. It is not needed as the alarm.

**2. How published trackers handle tempo changes**

*Davies and Plumbley two-state model.* Sources: [Davies, Brossier & Plumbley, AES 2005](https://aubio.org/articles/davies05aesbeattracking.pdf), which I read, and the TASLP 2007 paper.
- A general state uses a Rayleigh-weighted comb filterbank over 6 s frames with a 1.5 s hop.
- After three consistent periods it switches to a context state with Gaussian period weighting, σ² = τ/8.
- The context state is replaced when a tempo change is observed. The exact rule in the 2007 paper is UNVERIFIED.
- Reaction therefore takes several 1.5 s hops. My inference: this explains aubio's 6.3 s relock on our shift suite.
- aubio is **GPL** ([aubio.org](https://aubio.org/)).

*IBT* ([Oliveira, Davies, Gouyon & Reis 2012](https://repositorio.inesctec.pt/server/api/core/bitstreams/5eb74efb-4891-443a-b0c9-fdbe341a54bc/content), read).
- It averages the best agent's score over W=3 s, every t_hop=1 s.
- It re-induces when the change in that average crosses below −th, with th=.03. It then pauses for one induction window (5 s).
- On 100 song transitions:

| variant | reaction time | induction requests |
|---|---|---|
| reset | 3.2 s (sd 1.6) | 107 |
| regen | 4.7 s | 142 |
| BTrack | 5.4 s | — |

- It ships in Marsyas, which is **GPL**.

*Bar-pointer HMM* ([Krebs, Böck & Widmer 2015](https://www.cp.jku.at/research/papers/Krebs_etal_ISMIR_2015.pdf), read).
- Tempo may change only at beat positions, with P ∝ exp(−λ|Φ̇_k/Φ̇_{k−1} − 1|).
- They use λ between 1 and 300; the best values were 95 to 125, and madmom's default is 100.
- So a 5% step costs 5 nats and a 10% step costs 10. In effect λ is a CUSUM threshold scaled by the step size.
- madmom's code is BSD, but its models are **CC BY-NC-SA, non-commercial** ([repo](https://github.com/CPJKU/madmom)).

*Others.*
- Real-time PLP ([Meier, Chiu & Müller 2024](https://transactions.ismir.net/articles/10.5334/tismir.189)) trades stability against adaptivity through kernel size and lookahead. It is MIT-licensed ([repo](https://github.com/groupmm/real_time_plp)).
- BTrack (Stark, Davies & Plumbley 2009) is **GPL-3** ([repo](https://github.com/adamstark/BTrack)).

**3. Recommendation for relocking within 4 s**

1. **Observation.**
   - Take the low-volatility model's per-beat IOI residual, built from strength-weighted onsets snapped to every grid line in that beat. More samples per beat means a smaller σ.
   - Estimate σ as a running MAD × 1.4826.
   - Clip z to ±2.5 (Huber).
   - Freeze the sums when beat confidence is low, such as in breakdowns or silence.
   - Leave octave and 3:2 ratios to the master-family vote, not the detector.
2. **Detector.** Two-sided CUSUM with k = 1.0 and h = 3.25.
   - ARL0 is about 1700 beats, roughly 12 minutes at 140 BPM.
   - With the clip, each beat adds at most 1.5, so an alarm needs at least 3 beats. That gives built-in hysteresis.
3. **On alarm.**
   - Run the GLR (W=16) over the same z to get the change time and the new period.
   - Re-seed the high-volatility model from the beats since the change time, and push the IMM regime toward high volatility.
   - Keep the old grid as a rival for 2 bars, and allow no new alarm for 1 bar. This is IBT's reset approach.
4. **What this means at 140 BPM** (T = 429 ms).
   - If onset jitter σ is 4 ms (UNVERIFIED; measure it on the synthetic suite), then σ_IOI ≈ 5.7 ms.
   - A 5% step is then 3.8σ, detected in about 1.5 beats.
   - A 2% step is 1.5σ, detected in about 6.4 beats, or 2.7 s.
   - If jitter is 10 ms, a 5% step is only 1.5σ.
   - Relock ≈ detection delay + 1–2 beats, which stays under 4 s for steps of 1.5σ or more.
5. **Calibration.** Replay the drift suite and pick the smallest h that gives zero alarms, then confirm relock on the shift suite.

The ARL and delay figures in the tables and Monte Carlo runs are my own computations and are approximate.
