# Evidence: clean-room real-time beat tracking, licences and design (2026-10-22)

The final report of a research agent (sonnet, web), dispatched by Vandor for A16 T4: our own beat detector,
replacing aubio (GPLv3+). Persisted unedited per the full-fidelity rule; its UNVERIFIED marks are kept.

---

# Clean-room real-time beat tracker — research report

## 1. Licence table (code vs. model-weight licences checked separately)

| Implementation | Code licence | Weights licence | Safe to depend on |
|---|---|---|---|
| **librosa** (`beat_track`, `tempo`, `onset`) | ISC (BSD/MIT-equivalent) | n/a (DSP, no weights) | **YES** |
| **madmom** (CPJKU) | BSD-2-Clause | **CC BY-NC-SA 4.0** on all `.pkl` models/data (confirmed in `madmom/LICENSE`) | Code: yes. Pretrained models: **NO** (non-commercial) |
| **BeatNet** (Heydari/ISMIR 2021) | **CC BY 4.0** (non-standard for software; permits reuse incl. commercial, with attribution) | same CC BY 4.0 | Conditional — attribution required; its feature pipeline reportedly reuses madmom internals (**UNVERIFIED** whether NC weights are pulled in) |
| **Beat This!** (CPJKU, ISMIR 2024, Foscarin/Schlüter/Widmer) | **MIT** (`CPJKU/beat_this`) | ONNX export of official checkpoint; original `.ckpt` licence terms **UNVERIFIED** (hosted on CPJKU cloud, no explicit LICENSE seen) | Code yes; weights unverified — don't ship weights until confirmed |
| **BTrack** (Stark/Davies/Plumbley) | **GPLv3** | n/a | **NO** — read the paper only, do not copy code |
| **essentia** (MTG) | **AGPLv3**, dual-licensed commercially on request | n/a | **NO** |
| **aubio** | **GPL-3.0-or-later** | n/a | **NO** (this is what we're replacing) |
| **TempoCNN** (Schreiber/Müller) | **AGPL-3.0** | same | **NO** |
| **mir_eval** | **MIT** | n/a | **YES** (eval-only dependency) |
| **real_time_plp** (AudioLabs Erlangen, Meier/Chiu/Müller, TISMIR 2024, "zero-latency PLP") | **MIT** | n/a (DSP) | **YES** — best permissive real-time reference found; causal, Python, uses `sounddevice` |
| PyAudioWPatch (WASAPI loopback capture) | MIT/Apache-2.0 family | n/a | YES (capture only, not a tracker) |
| SoundCard (cross-platform numpy loopback) | reported BSD-3 on PyPI | n/a | likely yes — **UNVERIFIED** in this pass |

**Flagged GPL/AGPL/NC — do not copy code or ship weights from:** aubio (GPL-3+), BTrack (GPLv3), essentia (AGPLv3), TempoCNN (AGPLv3), madmom's model files (CC BY-NC-SA 4.0). Reading their papers for algorithm design is fine and is the intended path.

## 2. Algorithm comparison

**Onset detection — spectral flux / complex-domain** (Bello & Duxbury 2005 tutorial; Bello et al. 2004 ICASSP "phase+energy, complex domain"): rectified spectral-magnitude difference, optionally phase-deviation weighted. One FFT per hop, O(N log N), zero added latency beyond the hop/window. Fully clean-room from the published equations. **Best fit** — this is the front end regardless of back end.

**Tempo estimation:**
- *Autocorrelation of onset envelope* (used in Ellis 2007): needs ~4–8 s of context to stabilize, prone to octave/tatum confusion without a prior; cheap (FFT-based).
- *Comb filter banks* (Scheirer 1998; Klapuri/Eronen/Astola 2006; reused in Davies & Plumbley 2007): a bank of resonators each tuned to a candidate period, updated every hop (IIR, O(1) per resonator) — inherently causal, low latency, moderate cost (~100–200 bins). **Best fit for real time.**
- *Fourier tempogram* (Grosche/Müller-style STFT of the onset curve): good clean peak but typically recomputed every ~0.5–1 s window, not every hop — useful as a periodic re-seed, not the per-hop phase loop.

**Beat-phase / real-time tracking:**
- **Davies & Plumbley 2007** (context-dependent, two-state: general tempo-induction state + context-dependent locked state, both driven by a comb filterbank): causal, moderate lock-on latency (several seconds while in the general state), accuracy reported competitive with offline systems of its era. Exact published % not retrieved — **UNVERIFIED** precise figure.
- **Stark, Davies & Plumbley 2009 (BTrack)**: the real-time refinement of the above — onset function → comb-filter tempo → explicit phase/beat-prediction step that outputs the *next* beat ahead of the current hop, exactly the "predict don't react" behavior we need. Algorithm is published (DAFx-09); code is GPLv3 so must be reimplemented from the paper.
- **Ellis 2007 dynamic programming**: global optimum via backtrace over the *entire* onset envelope — fundamentally **offline**; a windowed/online DP variant sacrifices optimality and still needs a trailing buffer, so it's a poor fit for low-latency live tracking. Its useful transferable idea: a log-Gaussian tempo bias term, i.e. a prior — directly reusable as our seed prior.
- **Particle filters** (Hainsworth & Macleod 2004 — Rao-Blackwellised and Brownian-motion variants; BeatNet 2021 — cascaded two-stage PF on a CRNN activation): naturally sequential/causal, track tempo+phase jointly, handle tempo drift well. Compute scales with particle count (BeatNet: ~latency 20 ms reported; F-measure ≈75.4% on GTZAN and Ballroom, online/causal setting). A seed can initialize the particle cloud tightly around the known BPM, cutting both particle count and lock-on time substantially.
- **Böck DBN / bar-pointer models** (Böck/Krebs/Widmer 2014/2016; refined further by Beat This! 2024): state space over (tempo, phase[, bar]) with Viterbi decoding — SOTA offline accuracy (Beat This!: 89.1 F1 on GTZAN without DBN postprocessing, ~97.5 F1 beat / 95.3 downbeat on Ballroom 8-fold CV; Böck-style DBN baseline ≈88.7 F1 per Hung et al., cited in the Beat This! paper). Full Viterbi is non-causal (needs the whole sequence); a forward-filtering-only variant can run online at the cost of a few hundred ms of extra latency and a heavier per-hop matrix-vector product over thousands of states — too costly for a 512-sample/~11.6 ms hop budget on CPU-only numpy.

**Verdict:** comb-filter resonator bank (Scheirer/Klapuri/Davies-Plumbley lineage) for tempo, plus a light particle filter or a Kalman/IIR phase-locked-loop for phase, seeded with the external BPM, is the right weight class for this project — DP and full DBN are too offline/heavy; raw autocorrelation alone is too slow to lock and too octave-prone without the same seed prior anyway.

## 3. Evaluation

Standard metrics (Davies 2014 "Evaluating the Evaluation Measures"; implemented in `mir_eval.beat`, MIT): **F-measure** at ±70 ms tolerance window; **Cemgil score** (Gaussian-weighted error sum); **P-score** (McKinney, cross-correlation of impulse trains); **CMLc/CMLt** (longest/total correct run at the *correct metrical level*, both beats of a pair must be right); **AMLt/AMLc** (same but also accepting double/half-tempo and off-beat interpretations). Tempo accuracy uses **Acc1** (within ~4% of ground-truth BPM) and **Acc2** (also accepts ×2/×½/×3/×⅓ octave errors) — `mir_eval.tempo`.

Datasets (annotations generally open, **audio is research-use-only and must not be redistributed** — fine for private local evaluation only): **GTZAN** tempo/beat annotations (Marchand & Peeters; CC-BY-4.0 annotation set at `TempoBeatDownbeat/gtzan_tempo_beat`) but the underlying GTZAN *audio* has no clear commercial licence and is distributed informally by Marsyas on request; **Ballroom** (685 files, ISMIR-2004 tempo-induction-contest audio, research-use audio + separately available annotations); **SMC** (217 files, deliberately hard examples, no downbeats); **Hainsworth** (222 files); **Harmonix Set** (912 tracks — annotations openly released by the original team, audio not redistributed for copyright reasons). All five are usable locally for private benchmarking of our own tracker; none should be redistributed or bundled.

## 4. Recommended design (numpy-only, seeded, real-time)

**Onset function** per hop (hop=512, win=1024–2048, 44.1/48 kHz): rectified spectral-flux, `SF[n] = Σ_k max(0, |X_n(k)| − |X_{n-1}(k)|)`, optionally complex-domain weighted by phase-deviation for sharper attacks. O(N log N) FFT, dominates the per-hop budget (~tens of µs for N=2048 on any modern CPU — negligible against the 11.6 ms hop).

**Tempo with seed prior:** maintain a comb-filter-bank energy `E(τ) = Σ_i SF[n-i·τ]·w(i)` over candidate periods τ near the seed, combined with a log-domain Gaussian prior `P(τ) = exp(-(log τ - log τ_seed)^2 / (2σ²))` (σ ≈ 0.1–0.2 in log2-BPM, i.e. a soft few-BPM band) multiplied into the resonator bank response before picking the peak — this is the direct countermeasure to half/double-tempo flips, borrowed conceptually from Ellis's DP tempo bias term. Without audio evidence strongly contradicting the seed, τ stays locked near τ_seed; with sustained contrary evidence the prior widens/flattens over several seconds to allow re-lock to a genuinely different tempo.

**Phase tracking with lookahead:** keep a running estimate of the next beat time `t_beat = t_last + τ`, updated each hop by a simple phase-locked-loop / Kalman-style correction: `phase_error = (SF-weighted alignment of t_beat to recent onset peaks)`; `τ ← τ + k_τ·phase_error`, `t_beat ← t_beat + k_φ·phase_error`. Because the LED/visual pipeline has its own output latency L (frame + driver delay), fire the beat event at `t_beat − L` so the physical light lands on the true beat — i.e. predict forward rather than react to a detected onset.

**Confidence & re-lock:** track resonator-bank peak sharpness (peak/mean ratio) and phase-residual variance as a confidence score; below threshold, widen the tempo prior and allow larger phase corrections (fast re-lock); above threshold, narrow both (stability). A sustained miss count triggers a full re-seed from the external BPM database value if available, otherwise a fresh autocorrelation/comb-filter sweep over the whole plausible range.

**Downbeats later:** add a second, slower resonator/accent-tracking layer keyed to bar-length multiples of the locked beat period, using relative onset-strength accent patterns per phase-position (Klapuri/Böck-style accent modeling) — deferred, not needed for v1.

**Expected accuracy vs aubio:** aubio's beat tracker is a simple onset+tempo heuristic with no seed support and known octave-flip issues; a seeded comb-filter/PLL tracker should comfortably beat it on CMLt/AMLt and virtually eliminate octave errors on seeded tracks, while staying far cheaper than DBN/particle-filter neural trackers — but it will not reach Beat This!-class F1 (~89–97) since it forgoes learned onset models. Realistic target: F-measure in the 80s on clean seeded pop/EDM material, degrading on expressive/classical material — **UNVERIFIED** until benchmarked locally against GTZAN/Ballroom per §3.

**CPU budget per 512-sample hop (~11.6 ms @44.1 kHz):** one FFT (~2048-pt) + spectral flux ≈ tens of µs; comb-filter bank update over ~100–200 τ bins ≈ low hundreds of µs; PLL/Kalman phase update ≈ µs. Total comfortably under 1 ms per hop on any modern CPU, leaving >10× headroom versus the hop interval — well within a pure-numpy, single-core budget.

Sources: [librosa ISC licence](https://licensie.com/python/packages/librosa) · [madmom LICENSE](https://github.com/CPJKU/madmom/blob/main/LICENSE) · [madmom_models CC BY-NC-SA](https://github.com/CPJKU/madmom_models) · [BeatNet repo](https://github.com/mjhydri/BeatNet) · [BeatNet paper](https://arxiv.org/pdf/2108.03576) · [Beat This! repo](https://github.com/CPJKU/beat_this) · [Beat This! paper](https://arxiv.org/pdf/2407.21658) · [BTrack repo](https://github.com/adamstark/BTrack) · [Stark/Davies/Plumbley 2009 DAFx](https://www.researchgate.net/profile/Matthew-Davies-5/publication/228988158) · [essentia repo](https://github.com/MTG/essentia) · [aubio GPL](https://github.com/aubio) · [TempoCNN repo](https://github.com/hendriks73/tempo-cnn) · [mir_eval repo](https://github.com/mir-evaluation/mir_eval) · [mir_eval paper 2014](https://archives.ismir.net/ismir2014/paper/000320.pdf) · [real_time_plp repo (MIT)](https://github.com/groupmm/real_time_plp) · [Meier/Chiu/Müller 2024 TISMIR](https://audiolabs-erlangen.de/resources/MIR/2024-TISMIR-RealTimePLP) · [Davies & Plumbley 2007](https://researchgate.net/publication/3457779) · [Ellis 2007 beat DP](https://www.ee.columbia.edu/~dpwe/resources/matlab/beat_simple/) · [Hainsworth & Macleod 2004](https://www.repository.cam.ac.uk/bitstreams/81a6d656-9be3-48f0-9a3d-ef096c02d985/download) · [Scheirer 1998](http://biorob2.epfl.ch/pages/studproj/birg67315/tempo%20detection.pdf) · [Klapuri/Eronen/Astola 2006](https://www.researchgate.net/publication/3457523) · [Böck/Krebs/Widmer 2014](https://www.cp.jku.at/research/papers/Boeck_etal_ISMIR.2014.pdf) · [Bello & Duxbury tutorial 2005](https://www.researchgate.net/publication/3334132) · [GTZAN-rhythm annotations](https://github.com/TempoBeatDownbeat/gtzan_tempo_beat) · [GTZAN copyright note](https://www.kaggle.com/datasets/carlthome/gtzan-genre-collection) · [Harmonix Set paper](https://archives.ismir.net/ismir2019/paper/000068.pdf) · [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch) · [SoundCard](https://pypi.org/project/SoundCard/0.3.3).

**Explicitly marked UNVERIFIED:** exact Davies & Plumbley 2007 published accuracy/latency numbers; whether BeatNet's pipeline imports madmom's NC-licensed pretrained filterbank/model assets; Beat This! raw `.ckpt` checkpoint licence (vs. the MIT repo code); SMC/Hainsworth/Ballroom/Harmonix exact redistribution licence text (inferred as research-use-only from common practice, not read verbatim from a LICENSE file); SoundCard's BSD-3 licence (from PyPI metadata, not the repo's LICENSE file directly); expected F-measure of the proposed design versus aubio (needs local benchmarking per §3 to confirm).
