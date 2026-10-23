# DeepSeek design lenses for the grid tracker (2026-10-22)

Five lens questions to DeepSeek through `py agent_cli.py ask --prompts-file ... --geometry lens` (ask id 3118068d,
1/5 branches ok). Each prompt carried the full brief
(research/reviewed/keylab-liberation-2026-10-22/grid-tracker-brief-2026-10-22.md). Persisted verbatim per the
full-fidelity rule.

## Lens 1: imm-layer  [ok]

## IMM beat-tracking layer

### State and transition
Use two models, both with state

\[
x_k = \begin{bmatrix} t_k \\ T_k \end{bmatrix}
\]

where \(t_k\) is the predicted next-beat time in seconds and \(T_k\) is the current beat period.

Per beat:

\[
x_{k+1} = F x_k + w,\qquad
F=\begin{bmatrix}1&1\\0&1\end{bmatrix}
\]

so the next beat is one period after the current one, and the period evolves.

### Process noise
**Model 1 — LOW volatility / grid-holder**

\[
Q_1 = \begin{bmatrix} (0.0005)^2 & 0 \\ 0 & (0.0005)^2 \end{bmatrix}
\]

in seconds². A period jitter of 0.5 ms per beat is tiny: over 16 beats it accumulates only about 2 ms of drift, so the grid stays put through syncopated bass notes. This is the “constant tempo” model.

**Model 2 — HIGH volatility / tempo-follower**

\[
Q_2 = \begin{bmatrix} (0.002)^2 & 0 \\ 0 & (0.01)^2 \end{bmatrix}
\]

A period standard deviation of 10 ms per beat lets the model move a 140 BPM grid to 128 BPM in roughly 3–4 beats, fast enough for DJ tempo steps. The 2 ms beat-time jitter absorbs small phase corrections without changing the period.

Reasons: high-vol must be fast enough to relock within the acceptance criterion of 4 s, but not so loose that every syncopated onset becomes a tempo change.

### Measurement model
The observation comes from the grid-fit layer, not from raw onsets. Each beat or bar, the best grid hypothesis reports:

\[
z_k = \begin{bmatrix} \hat t_k \\ \hat T_k \end{bmatrix}
\]

where \(\hat t_k\) is the grid-anchored beat time and \(\hat T_k\) is the grid period.

\[
z_k = H x_k + v,\qquad H=I
\]

\[
R = \begin{bmatrix} (0.008)^2 & 0 \\ 0 & (0.002)^2 \end{bmatrix}
\]

Reasons: onset interpolation at 512-hop 44.1 kHz gives roughly ±5–8 ms timing precision. The period estimate from a few bars of grid-matched onsets is reliable to about ±2 ms at 140 BPM; this is small enough to reject sub-division errors but large enough not to over-trust a single noisy bar.

Use Mahalanobis gating before accepting a measurement:

\[
\epsilon = z - H x^-,\qquad d^2 = \epsilon^T S^{-1} \epsilon
\]

Accept only if \(d^2 < 9\) (3σ). This stops syncopated off-grid onsets from hijacking the filter.

### IMM Markov matrix
Model 1 = stable, model 2 = volatile.

\[
\Pi = \begin{bmatrix}
0.98 & 0.02 \\
0.10 & 0.90
\end{bmatrix}
\]

per beat. The stable model is the default; it leaves only 2% of the time. Once in volatile, it returns to stable with 10% probability per beat, so after a DJ transition the tracker settles back into grid-holding mode in about 10 beats.

### Mixing step
For each target model \(j\), mixing probabilities are:

\[
\mu_{i|j} = \frac{\pi_{ij}\mu_i}{c_j},\qquad
c_j = \sum_i \pi_{ij}\mu_i
\]

Mixed input for model \(j\):

\[
x_{0j} = \sum_i \mu_{i|j} x_i
\]

\[
P_{0j} = \sum_i \mu_{i|j}\left[P_i + (x_i-x_{0j})(x_i-x_{0j})^T\right]
\]

This is the “volatile model gets guesses from the stable one” mechanism: when switching to high-vol, its prior starts from the stable grid rather than from a wild guess.

### Model likelihood
For each model \(j\), after prediction:

\[
S_j = H P_j^- H^T + R
\]

\[
\Lambda_j = \mathcal N(z_k;\ H x_j^-,\ S_j)
\]

Then mode probabilities:

\[
\mu_j = \frac{\Lambda_j c_j}{\sum_i \Lambda_i c_i}
\]

Clamp to \([0.01,0.99]\) to prevent total mode collapse.

### Combined output
\[
x = \sum_j \mu_j x_j
\]

\[
P = \sum_j \mu_j\left[P_j + (x_j-x)(x_j-x)^T\right]
\]

Report \(x[0]\) as the next predicted beat time and \(x[1]\) as BPM:

\[
\text{BPM} = 60 / x[1]
\]

The output is therefore a probability-weighted blend: near-constant BPM when stable, rapid period movement only when high-vol has strong likelihood.

### Compact numpy pseudocode
```python
F = np.array([[1,1],[0,1]])
H = np.eye(2)
Q1 = np.diag([0.0005**2, 0.0005**2])
Q2 = np.diag([0.002**2,  0.01**2])
R = np.diag([0.008**2, 0.002**2])
Pi = np.array([[0.98,0.02],[0.10,0.90]])

x = [x0.copy(), x0.copy()]
P = [np.eye(2)*0.1, np.eye(2)*0.1]
mu = np.array([0.95, 0.05])

def imm_step(x, P, mu, z):
    # predict each model
    xp = [F @ x[0], F @ x[1]]
    Pp = [F @ P[0] @ F.T + Q1,
          F @ P[1] @ F.T + Q2]

    # mixing
    c = Pi.T @ mu
    mu_mix = (Pi * mu[:,None]) / c[:,None]  # shape (2,2)

    x0 = [mu_mix[0,0]*xp[0] + mu_mix[1,0]*xp[1],
          mu_mix[0,1]*xp[0] + mu_mix[1,1]*xp[1]]

    P0 = []
    for j in range(2):
        Pj = sum(mu_mix[i,j]*(Pp[i] + np.outer(xp[i]-x0[j], xp[i]-x0[j]))
                 for i in range(2))
        P0.append(Pj)

    # update
    like = []
    xup, Pup = [], []
    for j in range(2):
        S = H @ P0[j] @ H.T + R
        e = z - H @ x0[j]
        K = P0[j] @ H.T @ np.linalg.inv(S)
        xup.append(x0[j] + K @ e)
        Pup.append((np.eye(2) - K @ H) @ P0[j])
        like.append(np.exp(-0.5 * e @ np.linalg.inv(S) @ e)
                    / np.sqrt(np.linalg.det(2*np.pi*S)))

    like = np.array(like)
    mu = like * c
    mu = np.clip(mu / mu.sum(), 0.01, 0.99)
    mu /= mu.sum()

    x_out = mu[0]*xup[0] + mu[1]*xup[1]
    P_out = sum(mu[j]*(Pup[j] + np.outer(xup[j]-x_out, xup[j]-x_out))
                for j in range(2))
    return x_out, P_out, xup, Pup, mu
```

### Failure modes
- **Volatile hijacking on syncopation**: if \(Q_2\) is too large or \(R\) too small, a loud off-beat bass 16th can be mistaken for a tempo change. Gating and period noise limits prevent this.
- **Stable model too stiff**: if \(Q_1\) is zero and mode probability is clamped to 0.99, the tracker cannot leave a wrong grid after a real tempo step. Small \(Q_1\) and 2% stable→volatile leak fix this.
- **Rapid mode switching**: unclamped likelihoods can oscillate every beat on half-time material. The Markov persistence and probability clamping add hysteresis.
- **Measurement outlier from sub-bass**: the grid-fit layer must only feed beat/bar observations after multi-bar agreement; a single bar’s fit should not enter the IMM un-gated.

## Lenses 2-5 (re-run as ask 34cd8548 with max_tokens 16000, after the first run starved at 4000; 4/4 ok)

## Lens 2: grid-scoring-parsimony  [ok]

## Grid score for “what grid do all these notes fit”

Represent each onset as `(t_i, s_i, band_i)`. Convert band profile to a grid weight:

```python
band_w = {"low": 1.2, "high": 1.0, "mid": 0.8}
w_i = s_i * band_w[band_i]
```

Use a rolling window of the last `N = 8` seconds, optionally with mild exponential recency:

```python
w_i *= exp(-(t_now - t_i) / 6.0)
```

A hypothesis is:

```python
H = (tau, Q, family, anchor)
```

where `tau` is beat period in seconds, `family` is straight or triplet, and `Q` is grid lines per beat:

```python
straight: Q = 2, 4, 8        # 8ths, 16ths, 32nds
triplet:  Q = 3, 6, 12       # 8th-triplets, 16th-triplets, 32nd-triplets
```

The grid interval is:

```python
delta = tau / Q
```

Grid lines occur at `a + k * delta`, where `a` is the anchor phase in seconds, `a ∈ [0, delta)`.

## Score

For a fixed `(tau, Q)` and anchor `a`, the normalised circular distance of each onset to the nearest grid line is:

```python
u = ((t - a) / delta) % 1.0
d = minimum(u, 1.0 - u)          # 0 = on grid, 0.5 = maximally off grid
```

Define:

```python
W      = sum(w)
A      = (1/W) * sum(w * cos(2*pi*d))      # alignment, in [-1, 1]
O      = (1/W) * sum(w * d**2)             # off-grid penalty
C      = log2(0.5 / delta)                 # parsimony
P_seed = -lambda_seed * (log2(tau / tau_seed))**2 if seeded else 0
```

The final per-hypothesis score is:

```python
score = A - lambda_off * O - lambda_par * C + P_seed
```

Typical values: `lambda_off = 0.5`, `lambda_par = 0.18`, `lambda_seed = 0.5`.

Alignment `A` already punishes off-grid onsets via `cos(2πd)`. The extra `O` term penalises large misses more strongly. Parsimony `C` is the key: finer grids have smaller `delta`, so `C` grows. Doubling tempo or moving from 16ths to 32nds halves `delta`, increasing `C` by exactly 1 bit. A 64th-note grid fits everything but is now too expensive.

## Best anchor in closed form

For fixed `tau` and `Q`, the best anchor maximises `A`. Let:

```python
alpha = 2 * pi * t / delta
V     = sum(w * exp(1j * alpha))          # complex-weighted sum
beta  = angle(V)
a_best = delta * beta / (2 * pi)
```

Then:

```python
A_best = abs(V) / W
```

This is the closed-form circular-statistics solution: the anchor phase that maximises the weighted sum of cosines. It costs one complex dot product per candidate tempo.

The beat-level phase follows from `a_best`:

```python
phase = (a_best / tau) % 1.0
```

For `Q > 1`, this phase is naturally quantised to one of `Q` sub-beat lines.

## Efficient tempo search

Search tempo candidates on a log-spaced grid. For realtime, use:

```python
bpm_candidates = geomspace(55, 200, 128)
taus = 60.0 / bpm_candidates
```

For every `Q` in `{2, 3, 4, 6, 8, 12}`, compute `V`, `A_best`, `a_best`, `O`, and `C` vectorised with numpy. Keep the top `K = 16` by coarse score, then refine each with parabolic interpolation in log tempo and recompute full score.

### Compact numpy pseudocode

```python
def score_hypotheses(t, w, taus, Qs,
                     lam_off=0.5, lam_par=0.18,
                     tau_seed=None, lam_seed=0.5):
    W = w.sum()
    out = []

    for Q in Qs:
        delta = taus / Q                       # (T,)

        # Circular vector sum for all taus at once.
        z = np.exp(2j * np.pi * (t[None, :] / delta[:, None]))
        V = (w[None, :] * z).sum(axis=1)       # (T,)

        A = np.abs(V) / W
        beta = np.angle(V)

        # Best anchor for each tau.
        a = delta * beta / (2 * np.pi)

        # Off-grid residual.
        u = np.mod((t[None, :] - a[:, None]) / delta[:, None], 1.0)
        d = np.minimum(u, 1.0 - u)
        O = (w[None, :] * d**2).sum(axis=1) / W

        # Parsimony: finer grid = larger C.
        C = np.log2(0.5 / delta)

        score = A - lam_off * O - lam_par * C

        if tau_seed is not None:
            score -= lam_seed * (np.log2(taus / tau_seed))**2

        out.append((Q, taus, score, A, O, C, a))

    return out
```

Top-K refinement:

```python
# Flatten all (Q, tau) candidates.
S = np.concatenate([s for _, _, s, _, _, _, _ in out])
idx = np.argpartition(-S, K)[:K]

for i in idx:
    # Parabolic interpolation in log-tau around idx, then recompute.
    refine_tau(i)
```

## Update cost

Let `M` be the number of onsets in the window, typically 100–300. With `T = 128` tempo bins and 6 subdivision values:

```text
coarse search: T * Q * M complex multiply-adds
             ≈ 128 * 6 * 256 ≈ 196k complex ops
```

The `exp` and complex dot products dominate. In numpy this is well under 1 ms per update on one core. With refinement of `K = 16`, total cost stays around `O(T Q M)`, so the tracker can run hundreds of times faster than realtime.

Scores are then smoothed per hypothesis:

```python
conf[n] = 0.9 * conf[n-1] + 0.1 * score
```

The master grid changes only when a rival family has higher smoothed confidence for several bars. This gives the hysteresis Daniel asked for.

## Lens 3: master-family-metrical-level  [ok]

## Master family and metrical level

Represent a grid hypothesis as `(g, φ, s)` where:

- `g` = smallest grid step used by that hypothesis (tatum period, seconds)
- `φ` = anchor phase on that grid (seconds)
- `s` = subdivision family: `4` = straight 16ths, `6` = triplet 16ths

For a beat period `T`, straight 16ths have `g = T/4`, triplet 16ths have `g = T/6`.

---

### 1. Merge hypotheses into families that vote together

Score every proposal on **all recent onsets**, not just the strongest or nearest note:

```python
def grid_score(g, phi, t, w):
    # t: onset times, w: onset strengths, recent ~8 bars
    d = np.abs(((t - phi) / g + 0.5) % 1.0 - 0.5)  # distance in grid units
    fit = np.sum(w * np.exp(-0.5 * (d / 0.03) ** 2))
    parsimony = lam * (1.0 / g)          # finer grids pay more
    return fit - parsimony
```

Hypotheses are merged if their tatums are small-integer related **and** their phases describe the same pulse train:

```python
R = [1.0, 2.0, 0.5, 3/2, 2/3, 3.0, 1/3, 4.0, 1/4]
edges = []
for i, j in pairs:
    ratio = max(g[i], g[j]) / min(g[i], g[j])
    if any(abs(ratio - r) < 0.03 for r in R) and phases_align(i, j):
        edges.append((i, j))

fam = union_find(edges)
g0[fam] = min(g[members])          # finest common tatum
fam_score[fam] = sum(score[members])
```

So 70, 140, 280 BPM straight/triplet variants collapse into one family and vote together. A 112 BPM fit is **not** in the 140 family; the ratio 140/112 = 5/4 is not an allowed metrical relation, so it remains a rival.

---

### 2. Choose which level is “the beat”

Within a family, the beat is a small integer multiple of the family tatum:

```python
for m in [1, 2, 3, 4, 6, 8, 12]:
    T = m * g0[fam]                 # candidate beat period
```

Choose `m` from three cues:

- **Accent:** kick and snare band onset strength at candidate beat positions.
- **Seed prior:** if `seed_bpm` exists, prefer `60/T` near it.
- **Tempo prior:** prefer a musically plausible range, usually 70–160 BPM.

```python
def beat_level_score(T, phi, onsets):
    beats = phi + np.arange(n_beats) * T
    kick = sum_strength_near(beats, onsets.low)
    snare = sum_strength_near(beats, onsets.mid)
    accent = w_kick * kick + w_snare * snare

    bpm = 60.0 / T
    seed_prior = -0.5 * ((np.log2(bpm / seed_bpm)) / 0.1) ** 2 if seed_bpm else 0.0
    tempo_prior = -0.5 * ((np.log2(bpm / 120.0)) / 0.35) ** 2

    continuity = -abs(T - prev_T) / prev_T
    return accent + seed_prior + tempo_prior + continuity
```

The family with the best **beat-level** score wins, not merely the best tatum fit.

---

### 3. Hysteresis

Keep a separate `master_fam`. A rival must outscore the master for several bars before a switch:

```python
best_fam = argmax(fam_score)

if best_fam != master_fam:
    if fam_score[best_fam] > fam_score[master_fam] + margin:
        rival_confirm[best_fam] += 1
    else:
        rival_confirm[best_fam] = 0

    if rival_confirm[best_fam] >= confirm_beats:   # e.g. 16 beats = 4 bars
        master_fam = best_fam
else:
    rival_confirm[:] = 0
```

Once locked, update the master grid with small averaged corrections, never per-note snaps:

```python
master_T   += 0.10 * (T_chosen - master_T)
master_phi += 0.05 * circular_diff(phi_chosen, master_phi, master_T)
```

---

### 4. Counting beats, bars, and downbeats

```python
beat_id = np.floor((now - master_phi) / master_T).astype(int)

# downbeat = beat 0 of 4/4 or 3/4
templates = {
    4: np.array([1.0, 0.30, 0.60, 0.30]),
    3: np.array([1.0, 0.45, 0.45]),
}

for L, tmpl in templates.items():
    for phase in range(L):
        meter_score[L, phase] = sum(
            beat_accent[phase::L] * tmpl[:len(beat_accent[phase::L])]
        )

meter_L, down_phase = argmax(smoothed_meter_score)
is_downbeat = (beat_id % meter_L) == down_phase
```

Apply the same few-bar hysteresis before changing meter.

---

### Why this defeats the failures

**beat_a locking 112 for 140.**  
112 is a rival straight grid, not in the 140 family. It may fit some syncopated off-beat bass 16ths, but it fails the kick/snare accent level. The 140 family includes 70/140/280, and the accent-selected beat level lands on kick and snare. Hysteresis prevents a flip after one second of weak 112 evidence.

**Seeded with 140, beat_a locking the off-beat bass.**  
beat_a snaps each expected beat toward the strongest onset inside ±100 ms, so the loud syncopated sub-bass drags the anchor. The design here does not snap. Phase is chosen by a global grid fit over all onsets, and the beat-level anchor is then chosen by kick/snare accent. Off-beat bass is still on the 16th grid, but shifting the beat anchor by a 16th misaligns kick/snare and lowers the accent score, so the master stays on the true beat.

## Lens 4: adversarial-failures  [ok]

1. **Half-time bass music, syncopated sub-bass**  
*Failure:* Scoring every onset equally lets loud off-grid sub-bass 16ths (3/6/10/13/15) outvote the sparse kick/snare. Parsimony then favors a finer grid at half or double the felt tempo, or locks phase to the bass line—exactly beat_a’s 112-for-140 lock.  
*Mitigation:* Weight onset votes by band: kick/snare accents decide beat-level phase, bass/other onsets only confirm subdivision; penalize off-grid bass less when kick evidence is strong.  
*Test:* 140 BPM, half-time kick on 1, snare on 3, loud syncopated bass 16ths never on beat, 30 s; assert F ≥ .85, BPM within 139–141, no half/double flips.

2. **Breakdowns/intros with no drums for 16–32 bars**  
*Failure:* With no strong onsets, confidence decays; low-vol holds, but if high-vol noise onsets (pads, FX) briefly outscore the master, hysteresis or regime mixing can re-initialize a wrong grid, so drums return out of phase.  
*Mitigation:* During low-onset-energy periods, freeze master tempo/anchor and decay confidence slowly; raise the evidence bar for any new hypothesis; keep counting from the clock.  
*Test:* 24 bars kick/snare at 128, then 24 bars pad-only, then drums resume; assert phase error at resume ≤ ±40 ms, no flips, BPM still 128 ± .5.

3. **Tempo automation ramps**  
*Failure:* Low-vol assumes near-constant tempo; if its probability stays high, BPM estimate lags the ramp. If high-vol wins late, hysteresis delays adoption, so beat predictions slide off by hundreds of ms over the ramp.  
*Mitigation:* Detect consistent one-direction tempo change, raise high-vol probability, and update master BPM with a small-lag smoother rather than step flips.  
*Test:* Linear 128→132 over 8 bars; assert mean BPM error < .5, F ≥ .85 during ramp, no tempo flips.

4. **Live drummers drifting ±3%**  
*Failure:* Small averaged corrections may be slower than drift, so phase accumulates error until a rival half/double grid outscores; hysteresis then causes a bar-long wrong lock instead of smooth following.  
*Mitigation:* Continuous bounded phase correction each beat proportional to drift estimate, plus a slow tempo update; never per-note snap, but enough stiffness to follow ±3% human drift.  
*Test:* Sinusoidal drift 120 ± 3 BPM over 60 s; assert F ≥ .85, CMLt ≥ .75, no flips, max phase error ≤ 80 ms.

5. **Swing and triplet feel**  
*Failure:* Straight-16th and straight-triplet families both misplace swung onsets; score penalties can make the tracker oscillate between subdivisions or bias beat phase toward swung 8ths/16ths.  
*Mitigation:* Model swing explicitly (e.g., triplet-swing family with adjustable swing ratio) or treat swing as bounded timing noise with asymmetric tolerance; penalize only large deviations.  
*Test:* Swing 16ths (54% ratio) at 120 with kick/snare, 30 s; assert F ≥ .90, correct triplet-vs-straight family, no subdivision flips.

6. **DJ crossfades with two tempos overlapping 8–16 bars**  
*Failure:* Two grids fight; voting may average into an impossible tempo or flip rapidly between 128 and 175. Hysteresis can hold the outgoing track too long after the incoming dominates.  
*Mitigation:* Keep separate families for distinct onset clusters; decide by accent energy and continuity, suppress flips during ambiguity, then switch once incoming outscores by a margin for >2 bars.  
*Test:* Crossfade 128→175 over 16 bars with both drum tracks present; assert no flips in first 4 bars, lock to 175 ± 1 by 4 bars after fade, F ≥ .85 overall.

7. **3/4 waltz time**  
*Failure:* A 4/4-centric master family may interpret a 3/4 waltz as 4/4 at 3/4 or 4/3 tempo (e.g., 120 3/4 → 160 or 90 4/4), or force a 4-beat phase cycle, so downbeats and BPM fail.  
*Mitigation:* Add a meter dimension (3/4, 4/4, 6/8) to master family; score bar-length accent periodicity, not just beat grid.  
*Test:* 3/4 at 120, kick on beat 1, snare on 2 and 3; assert BPM 119–121, phase aligned to beat 1, no 4/4 misfold.

8. **Very fast DnB at 174 felt at 87**  
*Failure:* The 87/174 octave family merges, but beat-level accent may vote for 87 when the benchmark counts 174 (or vice versa). Unseeded, it can rest at the wrong octave and half/double-flip late.  
*Mitigation:* Make beat level a weighted vote: snare on 2 and 4 at 174 vs kick/snare backbeat at 87; seed BPM strongly constrains; announce both levels but choose master beat by accent and seed.  
*Test:* DnB 174 with half-time feel, 30 s, seeded 174 and unseeded; assert F ≥ .85 at the intended beat level, no octave flips.

9. **Silence and track changes**  
*Failure:* During long silence, confidence decays but predictions continue from a dead grid; when a new track starts at a different tempo, old hypotheses may mask the new grid, delaying reacquisition or emitting false beats.  
*Mitigation:* Detect silence and reduce hypothesis strength faster; after >2 s of no onsets, enter re-init mode where new onsets can found a fresh grid quickly without hysteresis.  
*Test:* 10 s silence between a 140 BPM track and a 100 BPM track; assert relock ≤ 3 s, no false beats during silence, no carryover flips.

## Lens 5: tempo-change-detection  [ok]

## Comparison

**(a) CUSUM on beat-time residuals.** Best practical choice. Residuals `r = t_obs - t_pred` from the current grid are roughly zero-mean while locked, even with syncopation, if you use only high-confidence beats and robust scaling. A real tempo step makes residuals trend consistently one direction, which CUSUM detects in 2–4 beats. False alarms are controllable with an outlier gate, MAD scaling, and an IMM gate.

**(b) BOCPD on residuals/IOIs.** More principled for unknown change size, and can detect a step slightly earlier. But raw IOIs are dominated by syncopated 16ths and fills, so it would need heavy-tailed likelihoods and careful hazard tuning. On clean gated residuals it works, but CUSUM is simpler and usually sufficient.

**(c) IMM probabilities alone.** Not sufficient. The high-volatility probability rises during real tempo changes, but also during syncopation, fills, or transient ambiguity. It is a useful gate/confirmation, not a detector.

**Recommendation:** use **robust CUSUM on beat-time residuals**, gated by the IMM high-volatility probability. Optionally add BOCPD later if earlier detection is needed, but this is not required to meet the 4 s target.

---

## Detection thresholds

- Accept residual only if beat confidence `> 0.5` and `|r| <= 0.120 s`.
- Scale residuals with MAD over the last 8–16 beats, minimum `sigma = 5 ms`.
- CUSUM drift `k = 0.5`, threshold `h = 4.5` on standardized residuals.
- Require IMM high-volatility probability `p_high > 0.55` at alarm.
- On alarm, reset CUSUM and residual history.

At 140 BPM this fires in about 2–4 beats, well under 4 s.

```python
# state: Sp, Sm, res_hist, p_high
def detect(r, conf, p_high, state):
    if conf < 0.5 or abs(r) > 0.120:
        return False
    state.res_hist.append(r)
    if len(state.res_hist) < 8:
        return False

    x = np.asarray(state.res_hist)
    med = np.median(x)
    sig = 1.4826 * np.median(np.abs(x - med)) + 1e-3
    sig = max(sig, 0.005)
    z = (r - med) / sig

    k = 0.5
    state.Sp = max(0.0, state.Sp + z - k)
    state.Sm = max(0.0, state.Sm - z - k)

    if max(state.Sp, state.Sm) > 4.5 and p_high > 0.55:
        state.Sp = state.Sm = 0.0
        state.res_hist.clear()
        return True
    return False
```

---

## Re-seeding after a detected change

Keep a circular buffer of onset strength `env` at ~100 Hz for the last 8 seconds. On detection, re-run a fast grid search over BPM and phase. Score every candidate by how much onset energy lands on its grid, with an off-grid penalty and a parsimony penalty so fine grids do not win.

```python
def reseed(env, t_env, old_bpm):
    dur = min(8.0, t_env[-1] - t_env[0])
    total = env[(t_env >= t_env[-1] - dur)].sum()
    dt = t_env[1] - t_env[0]

    bpm_grid = np.arange(60, 201, 1.0)
    best = []

    for bpm in bpm_grid:
        period = 60.0 / bpm
        phases = np.linspace(0, period, 20, endpoint=False)
        n = int(dur / period) + 1

        rel = phases[:, None] + period * np.arange(n)[None, :]
        t_grid = t_env[-1] - dur + rel.ravel()
        vals = np.interp(t_grid, t_env, env)
        vals = vals.reshape(len(phases), n)

        on = vals.sum(axis=1).max()
        off = max(0.0, total * dt - on)
        parsimony = 0.15 * (bpm / 200.0) * total * dt

        score = on - 0.4 * off - parsimony
        best.append((score, bpm, phases[int(np.argmax(vals.sum(axis=1)))]))

    best = np.array(best)
    order = np.argsort(-best[:, 0])[:5]

    # prefer coarsest grid among octave/subdivision ties
    chosen = best[order[0]]
    for idx in order[1:]:
        cand = best[idx]
        ratio = cand[1] / chosen[1]
        if (abs(ratio - 2.0) < 0.05 or abs(ratio - 0.5) < 0.05):
            if cand[0] > chosen[0] and cand[1] < chosen[1]:
                chosen = cand

    new_bpm = float(chosen[1])
    new_phase = float(chosen[2])
    return new_bpm, new_phase
```

After reseeding:

- Set the **low-volatility IMM model** to `(new_bpm, new_phase)` with small covariance.
- Set the **high-volatility IMM model** to the top 2–3 candidates with wider covariance.
- Reset the master grid immediately to the best candidate; hysteresis is already satisfied by the CUSUM/IMM alarm.
- Clear residual/CUSUM state and continue predicting from the new master grid.

This avoids slow convergence because the new grid comes from the recent onset-strength buffer, not from incremental phase updates.
