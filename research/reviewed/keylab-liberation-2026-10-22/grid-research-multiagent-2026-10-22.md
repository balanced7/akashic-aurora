# Grid-tracker research: multi-hypothesis / multi-agent beat tracking and metrical-level selection (2026-10-22)

The final report of a research agent (Claude, web), lane `multiagent`, from the grid-tracker research workflow (run wf_4acc5ff4-38e). Each agent read the brief (grid-tracker-brief-2026-10-22.md) first. Persisted unedited per the full-fidelity rule.

---

**Lane: onset timing precision at hop 512, causal, numpy/scipy only**

**Bottom line.** A 16th-note grid fit at 180 BPM needs onset times good to about σ ≤ 5 ms. Peak-picking on whole 512-sample frames gives 3.35 ms. Parabolic refinement gets 1 to 2.6 ms on clean hits. Running the detector internally at hop 128 gets 0.15 to 0.4 ms for about 14 µs per block, against a 580 µs budget at 20× real time. Two things are larger than any of these: the fixed per-band detection lag (3 to 18 ms) and the WASAPI render-side offset. Both have to be calibrated. The drift receipts point at hypothesis selection, not precision. Even at σ = 5 ms the tempo error is about 0.06 BPM.

**1. What precision the grid fit needs** (arithmetic, mine)
- At 180 BPM: a 16th is 83.3 ms, a 16th-triplet 55.6 ms, a 32nd 41.7 ms.
- Straight 16ths vs triplets: the nearest points the two grids don't share are 27.8 ms apart, so the decision boundary sits at ±13.9 ms.
- Parsimony: points that only the 32nd grid has sit 20.8 ms from a 16th. An onset on a 16th looks like a 32nd once its error exceeds 10.4 ms. With Gaussian error, that happens to 0.2% of onsets at σ = 3.35 ms, 3.7% at 5 ms and 19% at 7.9 ms. So the "coarsest grid wins" rule needs σ ≲ 5 ms. Score onsets with a Gaussian kernel of width about the measured σ, not hard bins.
- Tempo and phase are not precision-limited. A regression over N onsets spread across M beats gives σ_period ≈ σ·√12/(M·√N). With σ = 5 ms, N = 32, M = 16, that is 0.19 ms per beat, about 0.06 BPM at 140.
- Swing: a swung off-16th sits at s × (8th). At s = 2/3 it lands exactly on the triplet point, so no amount of precision separates "swung 16ths" from triplets. That needs an explicit swing parameter.
- The lights need less than the grid fit does:
  - Ear only: the just-noticeable timing shift is about 6 ms when notes are under 240 ms apart (Friberg & Sundberg 1995, JASA 98:2524).
  - Sound vs picture: ITU-R BT.1359 puts detectability at +45 ms (sound before picture) to −125 ms ([ITU](https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1359-1-199811-I!!PDF-E.pdf)). So a light can be about ±20 ms off and should err early. That standard was measured on TV material; transferring it to light flashes on beats is UNVERIFIED.

**2. Methods, with a simulation receipt**

I ran an in-memory simulation (nothing written to disk): causal Hann windows aligned to the newest sample, log spectral flux, 200 synthetic isolated hits per case. Results as bias / standard deviation:

| case | whole frames, hop 512 | parabolic, hop 512 | parabolic, hop 128 (N = 1024) |
|---|---|---|---|
| hi-hat, 4–16 kHz | 10.0 / 3.4 ms | 10.5 / 1.8 ms | 3.2 / 0.4 ms |
| kick, 30–200 Hz | 9.3 / 3.2 ms | 10.1 / 2.1 ms | 3.7 / 0.4 ms |
| kick click, 2–16 kHz | 18.3 / 3.4 ms | 18.2 / 1.1 ms | 8.4 / 0.15 ms |
| sub-bass, 30–200 Hz | 11.1 / 3.2 ms | 11.5 / 1.8 ms | 4.6 / 0.3 ms |

- **Parabolic interpolation** of the onset-function peak at frame k: δ = ½(d[k−1] − d[k+1]) / (d[k−1] − 2d[k] + d[k+1]), then t = t_k + δ·hop/sr. This is the quadratic peak fit from J. O. Smith's *Spectral Audio Signal Processing* ([CCRMA](https://ccrma.stanford.edu/~jos/sasp/Peak_Detection_Steps_3.html)), applied along time. It costs one extra internal hop of delay.
- **Smaller internal hop.** The contract fixes the input block at 512 samples, but the tracker can compute four 1024-sample frames per block. Measured on this machine: 14 µs for that batch, 21 µs for two 2048-point FFTs, 16 µs for a 512-sample IIR band filter (`sosfilt` with carried state). Short windows are fine for the low band, because onset flux doesn't need fine frequency resolution.
- **Phase-based timing.**
  - Formula: t̂ = t_c + Σ_band Re{X_mw·X_w*} / Σ_band |X_w|², where X_mw is the frame's FFT using the window m·w[m] (m counted in samples from the window centre).
  - Sources: Auger & Flandrin 1995 (the reassignment method); Röbel 2003 (centre of gravity of transient energy) ([PDF](http://recherche.ircam.fr/anasyn/roebel/paper/icmc2003.pdf)); Holzapfel, Stylianou, Gedik & Bozkurt 2010 (IEEE TASLP 18(6)), where the average group delay crosses zero when the window centre sits on an impulse.
  - Caveat (my derivation): by Parseval, the band sum is just the energy-weighted time centroid. On sustained notes it lands late, so apply it only to bins whose energy rose (positive flux).
- **HFC**, Σ k·|X|² (Masri 1996, via Bello et al. 2005): sharp peaks for clicks and hats, useless for sub-bass. Böck, Krebs & Schedl (ISMIR 2012) dropped HFC, phase deviation and rectified complex domain from their online comparison as inferior ([PDF](https://archives.ismir.net/ismir2012/paper/000049.pdf)).
- **Real mixes are worse than the simulation.** Böck, Arzt, Krebs & Schedl (DAFx 2012) report an online detector error of 0.3 ± 7.9 ms within a ±25 ms window and 0.1 ± 11.4 ms within ±50 ms. Manual annotation itself is accurate to about ±2 ms for percussive sounds and ±10 ms for soft ones ([PDF](https://www.cp.jku.at/research/papers/Boeck_etal_DAFx_2012.pdf)). SuperFlux runs at 200 frames/s to report onsets "with 5 ms accuracy" ([Böck & Widmer 2013](https://phenicx.upf.edu/system/files/publications/Boeck_DAFx-13.pdf)). Realistic: σ ≈ 2–5 ms on percussive electronic music, 8–11 ms on soft or dense material.
- **Per-band lag.** The lag is fixed per band and window, but differs between bands: the same kick reads 8 ms later in the click band than in the low band (N = 2048). Merging bands uncorrected smears every onset into a fake double. Calibrate each band by feeding synthetic hits through the exact pipeline, then subtract.

**3. Latency vs precision.** Lights come from `predict()`, so detection delay only affects how fast the tracker relocks. One frame of look-ahead for the parabolic fit (2.9 ms at an internal hop of 128) is affordable. Böck's online peak-picking uses no look-ahead at all (post_max = 0).

**4. WASAPI loopback and scheduling lights ahead**
- **Captured audio is early.** Microsoft: "WASAPI copies the output stream from the audio engine into the loopback application's capture buffer, in addition to copying the audio data to the hardware's render pin" ([docs](https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording)). So we hear the sound later than we capture it, by the endpoint buffer (10 ms by default), the driver and the DAC ([low-latency doc](https://learn.microsoft.com/en-us/windows-hardware/drivers/audio/low-latency-audio)). The Bluetooth delay is UNVERIFIED but large.
- **Delivery adds time.** Packets arrive roughly one 10 ms engine period late, plus the Python callback block.
- **Use the hardware timestamp.** `GetBuffer` returns `pu64QPCPosition` for the first frame of each packet, in 100 ns units ([docs](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer)). CPython's `perf_counter` uses the same clock as `monotonic`, which is `QueryPerformanceCounter` on Windows ([docs](https://docs.python.org/3/library/time.html)).
- **Silence breaks sample counting.** No packets arrive while nothing plays ([NAudio](https://github.com/naudio/NAudio/blob/master/Docs/WasapiLoopbackCapture.md)), so a clock built by counting samples freezes. The capture layer should re-anchor sample time to QPC on every packet. `feed(block)` carries no timestamp, so the tracker stays in stream time and the scheduler converts.
- **Send time for a light** = beat time converted to QPC + render latency − light latency (MIDI, USB and LED) − about 10 ms early bias. The render latency differs per device: measure it with a click test comparing loopback to a microphone (a standard method, UNVERIFIED here). Measure the light latency the same way.

**5. Licences**
- aubio: **GPL-3.0+** ([repo](https://github.com/aubio/aubio)).
- BTrack: **GPL-3.0** ([repo](https://github.com/adamstark/BTrack)).
- madmom: code is BSD-2, but its models and data are **CC BY-NC-SA 4.0, non-commercial** ([licence](https://github.com/CPJKU/madmom/blob/main/LICENSE)).
- All the methods above come from papers and are clean-room implementable in numpy/scipy.
