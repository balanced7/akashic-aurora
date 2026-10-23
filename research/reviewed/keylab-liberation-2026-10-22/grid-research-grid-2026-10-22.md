# Grid-tracker research: fitting a beat grid to onsets, and DJ-software beatgrids (2026-10-22)

The final report of a research agent (Claude, web), lane `grid`, from the grid-tracker research workflow (run wf_4acc5ff4-38e). Each agent read the brief (grid-tracker-brief-2026-10-22.md) first. Persisted unedited per the full-fidelity rule.

---

**LANE: beat-grid fitting and DJ beatgrids.** This was read-only. I used no GPL or non-commercial code, only papers and manuals. Derivations marked "(ours)" are mine and not taken from a source.

**1. Phase by circular statistics**
- Let θ_j = 2π t_j / P, with w_j the strength of onset j. Define C_k(P) = Σ w_j e^{ikθ_j} and R_k = |C_k| / Σw_j.
- Under a von-Mises grid model, the maximum-likelihood anchor is φ̂ = arg(C_k)/k, modulo P/k. Source: Mardia & Jupp 2000, *Directional Statistics*.
- **Confidence (Rayleigh):** in the unweighted case Z = nR̄² and p ≈ e^{−Z}. Sources: Fisher 1993; Wilkie 1983, http://wexler.free.fr/library/files/wilkie%20(1983)%20rayleigh%20test%20for%20randomness%20of%20circular%20data.pdf.
  - Weighted form (ours): Z_k = |C_k|² / Σw_j². Its expected value is 1 when phases are uniform, so 1 − e^{−Z} is a calibrated value for the contract's `confidence` field.
- **Causal update (ours):** on each onset, C_k ← e^{−Δt/τ}·C_k + w·e^{ikθ}, vectorised over a tempo bank.
  - Cost: about 700 tempi × 4 harmonics × about 10 onsets/s ≈ 3e4 complex operations per second, far inside the 20× real-time budget.
- **Octave families are one object (ours):** C_k(P) ≡ C_{2k}(2P). The 70, 140 and 280 BPM hypotheses are the same coefficients indexed differently. Indexing the bank by tatum frequency f = k/P makes Daniel's "one master family" structural.
- **Jitter alone does not stop over-fine grids:** with timing jitter σ_t, E[R_k] ≈ exp(−(2πkσ_t/P)²/2) (wrapped normal; Mardia & Jupp). Quantised electronic music has a very small σ_t, so a 64ths grid fits about as well as a 16ths grid. An explicit Occam term is needed (section 3).
- **Tempo resolution (ours):** a period error ΔP shifts the phase at the end of a window of length W by about W·ΔP/P. That requires ΔBPM/BPM ≤ σ_t/W. For W = 8 s, σ_t = 10 ms and 140 BPM, the bank step must be about 0.18 BPM or finer. Laroche 2001 makes the same point about needing a fine tempo search.

**2. Phase histograms**
- Laroche 2001 histograms transient times modulo the beat (his Fig. 4).
- Eck's autocorrelation phase matrix keeps lag × phase (Eck, ICASSP 2007, https://research.google/pubs/beat-tracking-using-an-autocorrelation-phase-matrix/).
- Eck & Casagrande (ISMIR 2005) score meter by the Shannon entropy of the phase distribution. A peaky phase histogram means low entropy, which means a good period.

**3. Grid likelihood with parsimony (MDL / Occam)**
Laroche 2001, http://labrosa.ee.columbia.edu/~dpwe/papers/Laro01-swing.pdf:
- **Model:** maximum likelihood under constant tempo, p(t) = Σ_{i=0..3} p_i G([t]_P − b_i). The b_i are the four 16th positions in a beat. Weights p = (.4, .15, .3, .15). G is a Gaussian whose width is tied to the 16th interval.
- **Search:** exhaustive over tempo (70–140), swing (0–40% in 10% steps) and 32 phases.
- **Grid choice:** he picked 16ths by hand, judging halves too coarse and eighths too fine.

Proposed generalisation (ours):

```
p(t|P,φ0,G,π) = (1−ε) Σ_{m∈G} π_m N([t−φ0−mP]_P; 0, σ_t²) + ε/P
S(G) = Σ_j w_j log p(t_j)
```

- Each density integrates to 1 over a period, so naming a grid line costs −log π_m ≈ log|G| nats. That is the MDL code length (Rissanen 1978; Grünwald 2007) and the Bayesian Occam factor (MacKay 2003, ch. 28).
- When onsets sit on 16ths, a 64ths grid pays log 4 ≈ 1.4 nats more per onset, so the coarser grid wins.
- When onsets really sit on 32nds, the coarser grid pays the residual cost or drops to the ε floor, so the finer grid wins.
- The ε floor makes off-grid onsets count against a grid, with a bounded cost. This automates Laroche's hand choice.

Prior art, details unverified:
- Gouyon, Herrera & Cano 2002 (AES 22nd conference) estimate the tatum period and phase with the two-way mismatch procedure borrowed from F0 estimation. My reading is that its grid-to-onset term penalises empty grid lines. UNVERIFIED: the PDF was blocked.
- Seppänen 2001 (WASPAA) estimates the tatum from an inter-onset-interval histogram plus a remainder-error function, with short-term memory. Equation UNVERIFIED.
- Cemgil, Desain & Kappen 2000 (*Computer Music Journal* 24(2)) treat rhythm quantisation as Bayesian. That their grid prior favours simpler subdivisions is UNVERIFIED: the PDF returned 403.

**4. Subdivision family and swing**
- Marchand & Peeters, DAFx-15 (https://www.ntnu.edu/documents/1001201110/1266017954/DAFx-15_submission_59.pdf):
  - They fit Gaussians to autocorrelation peaks of the onset-energy function, in [d_e/2, d_e] and [d_e, 3d_e/2], where d_e is the straight 8th.
  - A frame counts as swing if both amplitudes are positive, both σ < d_e/4, and both means fall inside their intervals. Swing ratio sr = μ_l/μ_s: 1:1 is straight, 2:1 is triplet feel, 3:1 is hard swing.
  - Their dataset labels "ternary" separately from "swing".
- Gouyon, Fabig & Bonada (DAFx-03) use sr = (d_e + d_s)/(d_e − d_s) from the second inter-onset-interval peak.
- Causal proposal (ours):
  - Let ψ = frac((t − φ̂)/P_beat). Take the circular mean ψ̄ of the off-beat cluster, ψ ∈ (0.4, 0.85), and set sr = ψ̄/(1−ψ̄).
  - Choose the family by the Occam-penalised S for {0,¼,½,¾} (straight 16ths) vs {0,⅓,⅔} (triplets) vs {0,ψ̄} (swung 8ths).
  - Laroche's swing (a delay on 16ths 2 and 4) covers swing at the 16th level.

**5. Why grid fit alone cannot fix the beat phase (the drift failure)**
- Laroche states that his 16ths template repeats every 16th, so the beat phase is known only up to a 16th. Only the uneven p_i break the tie.
- Worked illustration on the drift suite (16ths numbered 0–15, beats at 0/4/8/12; used for analysis only, never as constants):
  - The bass at {3,6,10,13,15} alone gives C_1 = −2 − i, which puts the beat about 0.57 beat late, roughly on the off-beat.
  - Kick and snare add +2d. Whenever the bass weight is larger than the drum weight, the phase lands off-beat. That is exactly beat_a's seeded failure (F .000).
  - Shifting the grid by two 16ths produces identical counts by metrical level: 2 on beats, 2 on 8ths, 3 on 16ths.
- So a positional metrical prior ties. The decision has to come from accent features that separate percussive hits (transient sharpness, high-band flux) from sub-bass, or from the database seed. Raw low-band energy cannot do it.

**6. DJ software**
- **Mixxx** (GPL: GPL-2.0-or-later per https://en.wikipedia.org/wiki/Mixxx; PR #3476 moved toward GPLv3, current exact version UNVERIFIED; described from docs only):
  - Its main analyser wraps the Queen Mary tracker (qm-dsp, GPL-2.0; Davies & Plumbley 2007).
  - PR #3626 ("Ironing beats", merged 2021-03-15, https://github.com/mixxxdj/mixxx/pull/3626):
    - keep regions of constant spacing within 25 ms of the raw beats;
    - the longest region sets the BPM and its allowed range;
    - round the BPM to a 1/12-BPM step only if every beat stays within 25 ms;
    - take the phase from the longest region, adjusted by at most 25 ms;
    - join regions that share tempo and phase.
  - The "Assume constant tempo" preference turns this on and off (https://manual.mixxx.org/2.3/id/chapters/preferences/beat_detection).
- **rekordbox** (6.0 manual, https://cdn.rekordbox.com/files/20200323144552/rekordbox6.0.0_manual_EN.pdf):
  - "Normal" analysis is for a fairly steady tempo and takes a BPM range; "Dynamic" is for significant tempo changes.
  - Grid edits: shift ±1/3 ms, widen/narrow ±1/3 ms, ×2/÷2, "1.1Bars", TAP, Analysis Lock.
- **Traktor:**
  - Default detection range 78–155 BPM. Grid lines repeat at an equal spacing from the first gridmarker (https://support.native-instruments.com/support/solutions/articles/69000879457-how-to-set-beatgrids-in-traktor).
  - Traktor Pro 4 adds multiple markers with tempo zones (https://www.digitaldjtips.com/reviews/traktor-pro-4-review/). Whether analysis places those markers automatically is UNVERIFIED; reviews describe them as manual.
- **Serato:**
  - A BPM-range option prevents half/double tempo.
  - The DJ 5.0 public beta (September 2026) adds "Lucid Beatgrids": Fixed (one BPM plus one downbeat) and Flexible (a Beat Warp Marker wherever the tempo changes) (https://www.digitaldjtips.com/serato-fixes-its-beatgrids-in-dj-5-0-beta/). The official support page returned 403.
- **Lessons for the tracker:**
  - All of these analyse the whole track offline, so none is causal.
  - Constant tempo is the default, and tempo-following is a separate mode. That is Daniel's low/high volatility split.
  - The octave is chosen by a BPM-range prior.
  - A tempo prior toward round BPMs is justified for DAW-produced tracks.
  - Corrections are global (translate, scale, double/halve, re-anchor the bar), never per-beat snaps.

**Licences:**
- Mixxx and qm-dsp are GPL: read for descriptions only, never copy.
- rekordbox, Serato and Traktor are closed and proprietary: manuals only.
- Everything else in this report is a paper; no code was taken.
