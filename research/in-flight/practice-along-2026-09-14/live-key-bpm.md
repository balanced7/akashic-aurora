# Lane: live key and BPM from the loopback audio

| | |
|---|---|
| Date | 2026-09-14 |
| Status | Research and design only. No code edited, nothing installed or downloaded, no accounts, no windows opened. |
| Question (Daniel, Discord, verbatim) | "Can we integrate Spotify as well and auto set bpm and key? That way I can practice along to music and control Spotify via the preview!" |
| This lane | Estimating key (and key changes), tempo and beat phase **in real time in the browser** from the Focusrite "Loopback L + R" input the piano page already opens. The sibling lane `windows-media-controls.md` covers track identity and transport (SMTC). |
| Grounded in | `arsenal/web/piano.js` (audioIn, tickMeter, tickKey), `arsenal/web/play.js` (ensureAudioGraph, analyseFrame, detectBeat), `arsenal/web/piano/nashville.js` (createKeyTracker, rankKeys), `arsenal/web/piano/transport-test.html` (OnsetProbe AudioWorklet), `arsenal/analysis.py`, `research/in-flight/piano-jam-2026-09-14/jam-spec.md`, and the sibling lane. |

---

## 1. Short answer

1. **Doable with our own code, in the page, with nothing to install.** An AudioWorklet on the loopback input does
   the signal processing: a mono sum, a 10 ms onset-strength frame, and a decimated-FFT chroma frame every 250 ms. The
   main thread runs the estimators: key at 10 Hz, tempo at 4 Hz, and beat-phase smoothing per onset frame. The 60 fps
   render loop only reads cached state and extrapolates the beat clock. Estimated cost is well under 2% of one core
   (section 3.4; measure it in drill S0).
2. **Key: reuse `createKeyTracker` as it is**, fed by an audio pitch-class histogram built to the same contract as
   `pcHistory` (section 4.2). Its hysteresis, playing-time clocks, leading-tone rule and `lock()` carry over. Its
   cadence and home-chord cues need chord names, so they stay off until audio chord reading exists (v2).
   - **Expect template-level accuracy, not certainty.** Published *exact-key* rates are 65-80% on pop and 65-70% on
     EDM, and only the best systems reach them (section 4.5).
   - The common errors are the **relative key and the key a fifth away**. Those are exactly the errors that shift
     every Nashville number.
   - So the page must show confidence and a runner-up, and offer one-click fixes (lock, relative, ±5th). It can also
     use track metadata as a prior when Daniel approves a source.
3. **Tempo: onset strength, then autocorrelation or comb filtering, gets a tempo in about 4-8 s.** Octave errors
   (half or double tempo) remain the main failure.
   - Classical estimators score around 50-78% on exact-octave accuracy (Acc1) but about 90% when the octave is
     ignored (Acc2) (section 5.3).
   - The fix is product-level: a prior range, **×2 / ÷2 buttons remembered per track**, the existing tap control, and
     metadata BPM as a tie-breaker.
   - Beat phase comes from a causal comb-phase estimator smoothed by a phase-locked loop (PLL), with loopback latency
     measured once by a click drill (section 5.6).
4. **Libraries.** None fits cleanly enough to adopt in v1 (section 7).
   - Essentia.js is **AGPL-3.0**; aubio, libKeyFinder and BTrack are **GPL-3**. The repo is public Apache-2.0, so
     adopting any of them is Daniel's licensing call.
   - `realtime-bpm-analyzer` (Apache-2.0) gives BPM without beat phase, and folds everything into 90-180 bpm, which is
     wrong for his 60-80 bpm ballads.
   - `web-audio-beat-detector` (MIT) works on AudioBuffers only.
   - Meyda (MIT) has chroma but no key or tempo.
   - Loading any of them from a CDN at runtime is a download, so it needs Daniel's approval.
5. **Daniel's own playing** is in the same loopback (through FL Studio or Kontakt), but his MIDI is known. v1 keeps
   two keys side by side:
   - **Track key:** from audio, with frames down-weighted while he plays and onsets gated near his note-ons.
   - **Your key:** the existing MIDI tracker.
   - The page shows whether they agree. Subtracting his predicted piano chroma from the audio chroma is v2, after a
     solo calibration drill (section 6).
6. **Metadata APIs are a prior, never the truth** (section 8).
   - **Spotify:** Audio Features closed to new apps on 2024-11-27, and since February 2026 Development Mode apps
     also require Premium.
   - **GetSongBPM:** free, but needs an account and a **mandatory backlink even for private use**.
   - **ReccoBeats:** free, terms not found. **Soundcharts:** paid.
   - **AcousticBrainz:** frozen CC0 dumps. It was shut down partly because its BPM and key estimates were often wrong.
   - Sending song titles out leaks listening history, so metadata stays **off by default**.
7. **Offline validation needs no install:** librosa 0.10.2 (ISC) is already on this machine. Ground truth comes from
   FL Studio renders in known keys and tempos (with modulations and tempo ramps) and from Daniel's own corrections.
   Beat This! (MIT) and Essentia (AGPL, no Windows wheels) are optional upper-bound references, only after approval
   (section 9).

---

## 2. What exists today (read tonight)

| Where | What it does now | What it means for this lane |
|---|---|---|
| `piano.js` `audioIn` (line ~2475) | `getUserMedia` with `deviceId` exact, `echoCancellation`, `noiseSuppression` and `autoGainControl` all **false**, `channelCount: {ideal: 2}`; one `AnalyserNode` (`fftSize` 1024), **never connected to a destination** ("the Focusrite Loopback already carries the speaker mix, so playing it back would feed back"); `tickMeter` reads RMS for the meter; the track is cloned into recordings | The processing-off constraints are exactly right for onset and pitch analysis: AGC would flatten onsets. The listener must also stay off the destination. `new AudioContext()` uses the device rate (probably 48 kHz). |
| `play.js` `ensureAudioGraph`, `analyseFrame`, `detectBeat` | `AnalyserNode` FFT 2048, smoothing 0, read from the render loop; `sameAsLastRead` skips duplicate reads; per-band AGC; positive spectral flux over 20 Hz-16 kHz; `detectBeat`: bass power ≥ 1.6× its average, rising, refractory 180 ms | A visual pulse, not a tempo or a phase. Sampling an AnalyserNode from `requestAnimationFrame` both drops and repeats frames (hence `sameAsLastRead`), which is why this lane moves analysis into an AudioWorklet. |
| `analysis.py` `audio_features` | offline PyAV decode to mono 48 kHz, hop 480 / window 2048 / Hann, band dB and flux | The live onset function uses the **same 480-sample hop (10 ms)**, so the offline twin and live frames align one-to-one. |
| `nashville.js` `createKeyTracker` | Krumhansl-Kessler Pearson over a decaying 12-bin history; `holdSec` 5, `margin` 0.04, `minR` 0.55; `FAST_TAU` 4 s, `SLOW_TAU` 24 s; `FIRST_SEC` 8, `FIRST_WAIT` 16; clocks count only playing time (`ACTIVE_SEC` 1.5 after growth); leading-tone, home-chord and cadence cues; `lock()` | Section 4 reuses it unchanged, behind an adapter that makes audio look like `pcHistory`. |
| `piano.js` `pcHistory`, `tickKey` | decays with τ = 12 s; each note-on adds `0.5 + vel/127`; the tracker ticks at 10 Hz (`KEY_TICK`) | These fix the units the tracker's thresholds assume (`MIN_WEIGHT` 2, `FIRST_WEIGHT` 6). |
| `transport-test.html` | registers an **AudioWorklet from a Blob URL** (`OnsetProbe`), batches onsets to the port every 8 quanta, samples `ctx.getOutputTimestamp()` every 100 ms | The worklet pattern and the clock-pair receipt already run in this Chrome. The latency drill (5.6) reuses both. |
| `serve.py` | no `Cross-Origin-Opener-Policy` / `Cross-Origin-Embedder-Policy` headers | No `SharedArrayBuffer`. MessagePort messages are enough at these rates (tens per second). |
| `jam-spec.md` | the page keeps time with a bar clock (9.1 tempo map); tap tempo (four taps, median, 40-200 bpm); "Follow me" (v2); a MIDI loopback guard; a warning that Claude's voice reaches the Loopback when Chrome plays through the Focusrite | The live tempo and phase can later feed a "follow the track" source for the tempo map. Claude's cue notes are known and can be gated like Daniel's (6.4). |
| Sibling lane | SMTC gives title, artist, play state and a coarse position (republished about every 4.5 s); no BPM or key. Python here has `librosa 0.10.2`, `av 17.0.0`, `numpy`; **no** `madmom`, `essentia`, `mir_eval`, `aubio` (checked tonight) | A track change from SMTC resets the estimators and selects stored per-track corrections (4.6, 5.3). |

---

## 3. Signal chain

```
Spotify / FL Studio / Chrome ─> Windows mixer ─> Focusrite playback ─┬─> speakers
                                                                     └─> Loopback L+R (digital copy)
                                                                            │  WASAPI capture
piano page: getUserMedia (EC/NS/AGC off) ─> MediaStreamSource ─> AudioWorkletNode "listen" (0 outputs)
   worklet, per 128-frame quantum:                                          │
     mono = (L+R)/2 ─┬─> onset path: 1024 Hann, hop 480 (10 ms) ─> log-flux bands ─┐
                     └─> chroma path: anti-alias LP, ÷8 ─> 4096 Hann @ 6 kHz,       │ port.postMessage
                                      hop 1500 (250 ms) ─> peaks ─> 12+12 bins ─────┤ (batched, ~10/s)
   main thread:                                                                     v
     onset ring (8 s) ─> tempo (4 Hz: ACF + comb + prior + hysteresis) ─> beat phase (comb + PLL)
     chroma ─> audio pc history (τ 12 s) ─> createKeyTracker (10 Hz) ─> track key + confidence
     MIDI (known) ─> activity weights and onset gates ─────────────────────────────┘
   render loop (60 fps): read state; extrapolate beat clock via getOutputTimestamp pairs; draw
```

### 3.1 The worklet

- **One AudioWorkletNode with `numberOfOutputs: 0`**, fed from the existing `audioIn.source`. The analyser stays for
  the meter.
  - *To verify in S0:* that Chrome keeps processing a zero-output worklet node that has no path to the destination.
  - Fallback: route it through a `GainNode` with gain 0 to the destination. That is silent, so it cannot feed back,
    but it breaks the letter of piano.js's "never connected" rule, so it would need a comment.
- **Pure DSP modules.** The FFT, window, flux, decimator and peak-to-chroma are plain ES functions with no
  AudioWorklet globals. The worklet imports them as a Blob URL, as `transport-test.html` does. Node runs the same
  modules over PCM that PyAV decodes, for fixtures and validation (section 9).
- **An in-house radix-2 FFT** (about 60 lines), so nothing is vendored. All buffers are preallocated, so the audio
  thread does no garbage collection.
- **Frame times** come from `currentFrame`, as `OnsetProbe` uses it, so every onset and chroma frame carries its
  AudioContext sample index.

### 3.2 Onset path (tempo and phase)

- Window 1024 (21 ms at 48 kHz), hop 480 (10 ms). Magnitude is compressed as `log(1 + γ·|X|)` (γ about 100) and
  compared frame to frame.
- The positive differences are summed in **three bands**:
  - low, under 200 Hz: kick and bass;
  - mid, 200 Hz-2 kHz: snare body, chords and piano;
  - high, over 2 kHz: hats.
- Optionally, a max-filter across frequency before the difference (the SuperFlux idea) keeps vibrato and sweeps from
  reading as onsets. That helps EDM risers and worship pads.
- The sent value per frame is `[low, mid, high]`. The main thread forms `odf = low + mid + 0.5·high`, subtracts a
  100 ms moving mean, and half-wave rectifies.

### 3.3 Chroma path (key)

- **Decimate ÷8 to 6 kHz** after two cascaded biquad low-passes at about 2.4 kHz, then take a 4096-point FFT: 1.46 Hz
  per bin, a 0.68 s window, hop 1500 (250 ms).
  - A semitone at A1 (55 Hz) is 3.3 Hz, about 2.2 bins; at E2 (82 Hz) it is 4.9 Hz, about 3.3 bins. So pitch classes
    resolve from about A1 up.
  - A full-rate 4096 FFT (11.7 Hz per bin) cannot separate semitones below about 400 Hz.
  - The decimation factor is derived from `ctx.sampleRate` (÷8 at 48 k, ÷7 at 44.1 k gives 6.3 k).
- **Peaks, not bins.** Take local maxima above a spectral-whitening floor (a running median across about 1/3 octave)
  within 55-2000 Hz. Refine each with parabolic interpolation, then map it to a pitch class with a cos² weight over
  ±0.5 semitone around the nearest centre (HPCP-style). The contribution is `sqrt(magnitude)`, so one loud bass note
  does not swamp the triad above it.
- **A second 12-bin bass chroma** covers 55-220 Hz only. It feeds the tonic cue (4.4).
- **Tuning.** A slow circular mean of the peaks' cent offsets (EMA τ about 20 s, clamped to ±50 cents) shifts the
  pitch-class centres. Recordings off A440 would otherwise smear across bins.
- **Harmonic emphasis.** A per-bin median over the last 3 magnitude frames before peak picking suppresses drum hits
  that land in one 250 ms frame. It is a cheap stand-in for median-filter harmonic/percussive separation.
- **Tonal gate.** A frame counts only if its RMS exceeds -45 dBFS, its chroma is not flat (max/mean > 1.6, say), and
  its spectral flatness under 2 kHz is below a threshold. Silence, spoken intros, noise risers and drum-only bars add
  nothing. Every threshold here is a starting value to tune on the fixtures in section 9.

### 3.4 Timing and CPU budget (estimates; measure in S0)

| Work | Rate | Rough cost |
|---|---|---|
| Worklet mono sum and ring copy | 375 quanta/s | negligible |
| 1024 FFT + 3-band log flux | 100/s | about 0.03-0.06 ms each, so 3-6 ms/s (under 1% of a core) |
| Decimator biquads | 48 k samples/s | about 0.5 ms/s |
| 4096 FFT at 6 k + peaks + chroma | 4/s | about 0.2 ms each |
| Tempo: ACF over 800 frames × about 100 lags, plus comb | 4/s | about 0.3 ms each |
| Phase comb + PLL | 10-100/s | negligible |
| `tracker.update` (24 keys × a few Pearson passes) | 10/s | already paid by piano.js today for MIDI |
| Render loop | 60 fps | reads only; no analysis in rAF |

The WebGL render dominates the page. The listener does not change its frame budget. The 128-frame render quantum is
fixed, which is fine here: Chrome 153 (stable 2026-09-08) adds `renderSizeHint` for other sizes, but it is only a hint
([Chrome 153 notes](https://developer.chrome.com/release-notes/153)).

---

## 4. Key from the audio

### 4.1 Why reuse the MIDI tracker

`createKeyTracker` is already tuned against Daniel's real sessions. Its hysteresis design carries straight over to
audio, which is noisier still:
- a lead banked in playing time, drained 2× when lost;
- a doubled hold for recently shown keys;
- a fast-histogram support check;
- a provisional first key;
- a stale key after a long pause.

It also names the key the way the Nashville row wants: the relative-major preference, and `lock()`. A second, separate
audio key engine would drift from those rules.

### 4.2 The adapter (audio pitch-class history, same contract as `pcHistory`)

- Keep `audioPc[12]`. It decays with τ = 12 s on the wall clock, exactly as `pcHistory` does.
- For each gated tonal frame of duration `dt` (0.25 s), add `RATE · dt · w_his · chroma_norm[pc]`:
  - `chroma_norm` sums to 1, so a loud chorus does not outvote a quiet verse.
  - `RATE` is about 4 units/s, roughly the note-on weight of a steady comp. It keeps `MIN_WEIGHT` 2 and
    `FIRST_WEIGHT` 6 meaningful: after 1.5 s of music W ≥ 6, but `FIRST_SEC` 8 still gates the first key.
  - `w_his` is the down-weight while Daniel plays (6.2).
- Call `audioTracker.update(audioPc, t, null)` at 10 Hz from the same tick as `tickKey`.
  - `chord = null` turns off the cadence and home-chord cues, which need chord names.
  - The leading-tone rule reads the histogram only, so it stays on.
- **Playing-time clock.** The tracker treats growth as playing, and gated frames add no growth. So a pad-only intro,
  a breakdown or a pause banks nothing and ages nothing: the behaviour its header describes for MIDI silence.
- **Track change** (SMTC title change, from the sibling lane) or 17 s of silence restarts it:
  - on a track change, create a fresh tracker instance, which is cleaner than relying on `FRESH_DROP`;
  - on a long silence, let the existing `FRESH_DROP` stale-key rule act.
- **Stereo.** L+R summing is fine. A side-channel (L−R) chroma is not worth its cost in v1.

Parameters to re-tune for audio, offline: `holdSec` (start at 8: audio evidence arrives continuously and denser than
note-ons), `minR` (audio chroma correlates lower, so start at 0.45), `margin` (0.04).

### 4.3 Profiles

- **Krumhansl-Kessler** is our twin-tested default. The values are the same arrays as `nashville.js` and Essentia's
  `krumhansl`.
- **Temperley (1999)** major `5.0 2.0 3.5 2.0 4.5 4.0 2.0 4.5 2.0 3.5 1.5 4.0`, minor
  `5.0 2.0 3.5 4.5 2.0 4.0 2.0 4.5 3.5 2.0 1.5 4.0`. It is a well-tested general profile with less weight on the
  tonic than KK.
- **EDM-trained profiles** (`edma`, `bgate`, Faraldo et al.) weight the minor subtonic more and zero out chromatic
  degrees. `bgate` scored 72.4 weighted on the KeyFinder pop and dance set, against 76.1 for a CNN
  ([Korzeniowski & Widmer 2018, Table 2](https://arxiv.org/abs/1808.05340)).
- Essentia's `key.cpp` lists all of them and ranks keys by Pearson correlation, as we do
  ([MTG/essentia key.cpp](https://github.com/MTG/essentia/blob/master/src/algorithms/tonal/key.cpp)). That file is
  AGPL-3.0. **Take profile numbers from the original papers and record the provenance** rather than copying from the
  AGPL source.
- `scoreKeys` takes a profile pair as a parameter only for the audio tracker. The MIDI tracker and its Python twin
  stay on KK. That is a small, testable change to `nashville.js` in a later build slice, not tonight.
- Choose by the offline validation in section 9. Plausible outcome: KK or Temperley for pop, worship and ballads, and
  `edma` when the tempo is 118-135 bpm with four-on-the-floor low-band onsets. Treat that as a hypothesis.

### 4.4 Audio-only cues (v1 and v2)

- **Bass tonic cue (v1).** Bass chroma (55-220 Hz) decays over `SLOW_TAU`. In a relative-major versus relative-minor
  tie (the tracker's most common near-tie), add a small bonus (about `CAD_W` 0.1 scale) to the key whose tonic owns
  more bass time. It enters through `rankKeys`' existing `bonus` argument, so no tracker internals change.
- **Transposition-shaped jump (v1).** Worship and pop modulate by +1 or +2 semitones for a last chorus. Suppose the
  **fast** (4 s) histogram's best key is the shown key moved by +1, +2 or −1 semitones in the same mode, and it scores
  at least as high as the shown key did before. Then accept the switch after `holdSec/2` instead of `holdSec`. The
  whole profile rotates, a shape a borrowed chord does not make. Without this, a truck-driver modulation takes about
  5-10 s of playing time to show.
- **Chord reading from audio (v2).** Beat-synchronous chroma matched against triads and sevenths, with bass chroma for
  inversions, would produce `Theory.detect`-shaped chords for `hear()`. That turns on the cadence and home-chord cues.
  It is risky (wrong chord names would fire false cadences), so it waits for validation data.

### 4.5 What accuracy to expect

The weighted score (mir_eval, MIREX) gives full credit for the exact key, and partial credit for a fifth, the relative
key, or the parallel key. For Nashville numbers only **exact** counts.

| Material | System | Weighted | Exact | Source |
|---|---|---|---|---|
| EDM (GiantSteps Key) | CNN (AllConv) | 74.6 | 67.9 | [Korzeniowski & Widmer 2018](https://arxiv.org/abs/1808.05340) |
| EDM (GiantSteps Key) | MIREX 2017 submissions | 50.5-74.1 (FK1 CNN 74.1; BD1 59.6) | n/a | [MIREX 2017 key results](https://music-ir.org/mirex/wiki/2017:Audio_Key_Detection_Results) |
| Pop (Billboard) | CNN | 85.1 | 79.9 | Korzeniowski & Widmer 2018 |
| Pop (Billboard 2012) | MIREX 2017 submissions | 67.4-82.3 | n/a | MIREX 2017 |
| Pop/dance (KeyFinder set) | `bgate` profile | 72.4 | 65.0 | Korzeniowski & Widmer 2018 |
| Beatles (Isophonics) | BD1 | 75.1 | 66.0 | Korzeniowski & Widmer 2018 |
| Classical | CNN | 96.6 | 95.2 | Korzeniowski & Widmer 2018 |

Reading for this project:
- Those are **whole-track, offline** numbers. A live estimate after 10-20 s will do worse at first and converge later.
- In the Korzeniowski table, **fifth plus relative errors alone are 11-21%** (e.g. GiantSteps: fifth 7.0, relative
  8.1).
- A reasonable planning figure for our template tracker on Daniel's music, until measured: **exact key on about 60-75%
  of pop, worship and ballad tracks** once settled, **lower on EDM**. Most misses will be the relative key, the IV or
  the V. That is a hypothesis for section 9, not a measurement.

So the UI must make fixing cheap:
- **Lock.**
- **Relative** (swap major and minor).
- **±5th.**
- A shown runner-up ("E♭ major, or C minor?").
- A correction stored per track (4.6).

### 4.6 Per-track memory (local)

- Daniel's corrections (key lock, tempo octave, "1 is here") are keyed by a hash of SMTC title and artist. They are
  stored locally, in `localStorage` or a git-ignored `state/arsenal/practice-along/tracks.json`.
- On the next play they become a strong prior: the tracker starts `lock()`ed to the stored key, and unlocks if the
  audio disagrees by more than a margin for `2·holdSec`. The tempo family's level is pre-chosen.
- This is the cheapest accuracy gain available, and nothing leaves the machine.

---

## 5. Tempo and beat phase

### 5.1 Onset strength

- The ODF from 3.2 at 100 frames/s goes into an 8 s ring buffer (800 frames).
- A confidence value is kept alongside it: the ratio of ODF peak energy to its median over 4 s. Pad intros, rubato
  piano and breakdowns read low, and the tempo view then **holds** its last value, dimmed, instead of guessing.

### 5.2 Tempo estimate (every 250 ms)

1. **Autocorrelation** of the last 6 s of ODF, unbiased (divided by overlap), over lags for 50-200 bpm.
2. **Pulse enhancement.** Score each candidate τ by `ACF(τ) + 0.5·ACF(2τ) + 0.25·ACF(4τ)` (and `ACF(3τ)` for
   triple feel). This is the cross-correlation-with-pulses idea from Percival and Tzanetakis 2014, and it favours
   periods whose multiples also line up.
3. **Prior:** a log-normal weight over tempo, centred at 105 bpm with σ about 0.9 octave. librosa's
   `beat_track` / `tempo` use a similar prior (`start_bpm` 120).
   - When metadata BPM exists, centre the prior on it with σ about 0.3 octave.
   - When Daniel stored an octave choice, use that.
4. **Tracking with hysteresis**, as the key tracker does: a Viterbi-like pass over the tempo candidate curve with a
   transition penalty proportional to |Δ log tempo|. A new tempo must lead for 3 s of confident ODF before replacing
   the shown one, so a half-time bridge does not flip the display for one bar.
   - A real change (a tempo ramp, a new section) lands in about 3-5 s.
   - First lock needs about 4-8 s of confident ODF.
5. **Fine BPM.** Parabolic interpolation around the ACF peak, then a slow median over 10 s. Show an integer BPM, but
   keep the float for the beat clock.

A comb-filter resonator bank (Scheirer 1998; Klapuri 2006) is the continuous alternative. It updates per ODF sample
and yields tempo and phase together. Keep it in reserve for v2 if the ACF lags in practice.

### 5.3 Octave errors (half and double tempo)

The literature is blunt about this:
- The review [AI and Tempo Estimation (arXiv 2401.00209)](https://arxiv.org/abs/2401.00209) says autocorrelation,
  comb-filter and DFT systems "suffered from frequent octave confusion".
- With classifier-based octave correction, Acc1 reached 69.6% against Acc2 91.2% (Dutta 2018). Wu 2015 reached Acc1
  78.5% on Ballroom and 62.6% on Songs.
- Even the CNN of Schreiber & Müller 2018 scores Acc1 74.2% against Acc2 92.1% on the combined sets (73.0% Acc1 on
  GiantSteps).
- Metrics: Acc1 means within ±4% of the annotated tempo; Acc2 also accepts ×2, ×3, ½ and ⅓.

For practice, the "right" octave is **the one Daniel counts**, not an annotator's. Design:
- Keep the **tempo family** `{T/2, T, 2T}`, plus `{2T/3, 3T/2}` when the triple-pulse score beats the duple one
  (6/8, shuffles).
- Choose the shown member by, in order:
  1. Daniel's stored choice for this track;
  2. metadata BPM within ±4% of a family member;
  3. **low-band periodicity**: a kick on every member-T beat (four on the floor) argues for T, and a backbeat snare
     every 2T in the mid band argues for the half-time reading;
  4. a default range of 70-150 bpm.
- **Controls:** `×2`, `÷2` and `tap` (the jam deck already has a four-tap median). A tap within ±8% of a family member
  selects that member without re-estimating.
- Known pitfall: `realtime-bpm-analyzer` folds its output into **90-180 bpm** by design
  ([docs](https://www.realtime-bpm-analyzer.com/guide/realtime-bpm-detection)), so a 72 bpm worship ballad reads 144.
  Our range must not be hard-coded.

### 5.4 Beat phase (v1: comb phase and PLL)

- Every 100 ms, for the current period P (in ODF frames), cross-correlate the last 4P of ODF with a pulse comb at each
  phase φ in [0, P). Weight the pulses 1, 0.8, 0.6, 0.4 from newest to oldest, and give each pulse a ±2-frame
  triangular shape.
- The best φ is a phase **measurement**. A first-order PLL smooths it:
  - `phase += (P_meas_error) · k`, with k about 0.15;
  - the period is nudged by `k₂ · error`, with k₂ about 0.01;
  - the PLL resets when the tempo tracker changes P.
- **Phase confidence** is the comb peak's prominence (peak over mean). Below a floor, the page hides the beat pips
  rather than showing wrong ones. Rubato ballads mostly land here, and that is honest.
- **v2: a causal cumulative score** (Ellis 2007's dynamic programming made online, as in BTrack: the ODF plus a
  momentum term over past beat scores within a log-Gaussian window around one period back). It is more robust
  through syncopation. BTrack itself is GPL-3 ([adamstark/BTrack](https://github.com/adamstark/BTrack)), so we would
  re-implement from the DAFx-09 paper, not from its code.

### 5.5 Bars and downbeats

- **v1: no automatic downbeat.** A "this is 1" button (or a tap on beat 1) sets the bar phase. The PLL then carries it
  at 4 beats per bar by default, 3 when the triple score wins.
- **v2:** harmonic-change novelty on beat-synchronous chroma (chords mostly change on bar lines in pop and worship)
  plus low-band accent. That gives a bar-phase guess with a confidence value, still correctable with the button.
- For reference offline, Beat This! (MIT, ISMIR 2024) tracks beats and downbeats
  ([CPJKU/beat_this](https://github.com/CPJKU/beat_this)).

### 5.6 Latency and clocks

**Chain, per step (estimated, to be measured):**
1. The Focusrite output and its Loopback copy are simultaneous, or nearly.
2. WASAPI capture buffering: about 10-20 ms (guess).
3. Chrome's MediaStream to the context: about 10 ms (guess).
4. Worklet quantum: 2.7 ms.
5. Onset window centre: 10 ms. The frame index already corrects for this once subtracted.
6. Main-thread batching: up to 21 ms at 8 quanta per post.
7. Render loop and scanout: 0-17 ms plus the display.

End to end, perhaps 40-80 ms. Only steps 2-3 (capture latency) bias the *timestamps*. Steps 6-7 only delay *when we
learn*, and extrapolation absorbs them.

**Timestamps.** Each onset frame carries its context sample index n.
- Its context time is `n / sampleRate − window/2`.
- The moment that sound left the speakers is `context_time − L_in`.
- The render loop maps context time to `performance.now()` with pairs from `audioIn.ctx.getOutputTimestamp()`, as
  `transport-test.html` already samples every 100 ms.
  - Those pairs describe the output path. The input path shares the same context clock, and the offset is `L_in`.
- Claude's voice lives in a different AudioContext (cues.js), so each context is mapped to `performance.now()`
  separately. That is the jam spec's clock.

**Measuring L_in (drill S0, no install; Daniel present because it makes a sound).**
1. Claude's voice schedules clicks at known context times `T`. Chrome must be outputting through the Focusrite, which
   the jam spec already notes feeds the Loopback.
2. The listener detects them at `T'` in the loopback input.
3. `T' − T = L_out + L_in`. Take `L_out` from `AudioContext.outputLatency` (reported in Chrome; Baseline 2025,
   [MDN](https://developer.mozilla.org/en-US/docs/Web/API/AudioContext/outputLatency)), so `L_in = (T' − T) − L_out`.
4. Store `L_in` per device label.
5. `MediaTrackSettings.latency` would have given this directly, but MDN lists it as unsupported in Chrome
   ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/MediaTrackSettings/latency)).

**What precision matters.** Visual beat pips within about ±30 ms look locked. Audible clicks against Spotify would
need tighter than that, and nothing in v1 clicks along by default. The jam transport following the track's tempo is a
v2 "follow" source, and it would then need the PLL's variance as well as its phase.

---

## 6. Daniel's playing in the same loopback

### 6.1 What reaches the Loopback

- His KeyLab MIDI goes to FL Studio or Kontakt, then out through the Focusrite playback, so it is in the Loopback
  (jam-spec 15.2 implies this sound path; **to confirm with Daniel**).
- The piano page sounds only Claude's cues: `createClaudeVoice` in `cues.js`. When Chrome outputs through the Focusrite,
  those cue notes are in the Loopback too.
- **Known exactly:** every note-on and note-off with velocity, and the sustain pedal (the page's `sounding` map and the
  practice log), plus every Claude cue note (the cue player's schedule).

### 6.2 Key evidence: keep two keys, weight frames (v1)

- **Track key:** the audio tracker, with `w_his` per chroma frame.
  - `w_his` = 1 while he is silent (no note sounding or pedal-held within 1.5 s).
  - `w_his` = 0.3 while he plays.
  - This is **unbiased per pitch class**: it listens harder while he rests, and never deletes the pitch classes he
    plays.
  - Hard-masking his pitch classes would be biased. He mostly plays in key, so masking would remove the true key's own
    strongest evidence.
- **Your key:** the existing MIDI tracker, unchanged.
- **Agreement readout:** `outShare(hisHistory, trackKey)` (already in nashville.js) is the share of his note weight
  outside the track key's scale. "In key with the track: 94%" is practice feedback in itself.
- **Which key drives the numbers** is Daniel's choice (open question 4). Recommended default: the track key once it is
  "fair" or "sure", otherwise his.

### 6.3 Key evidence: subtraction (v2)

- Predict his piano's chroma contribution: per note, velocity-scaled energy on the note's pitch class and its first
  harmonics' pitch classes (octave +12 and fifth +19, weighted 1 : 0.5 : 0.25), decaying with the key-release or pedal
  state.
- Subtract `g_band · predicted` from the audio chroma, floored at 0.
- Fit `g` (per octave band) in a **solo calibration drill**: the song paused, Daniel plays for 30 s, and a
  least-squares fit of predicted against measured chroma gives `g`.
- Timbre changes (a different Kontakt patch) invalidate `g`, so keep it per instrument name if FL reports one.
  Otherwise re-drill.

### 6.4 Onset evidence: gate his note-ons (v1)

- His strikes are onsets and would pull the tempo toward his rhythm.
- For each of his note-ons at wall time `t_on`, scale the **mid and high** ODF bands by 0.3 over
  `[t_on + L_midi − 10 ms, t_on + L_midi + 40 ms]`. Leave the low band alone unless he plays below C3, so a kick under
  his chord still counts. Gate Claude's cue notes the same way.
- `L_midi` is MIDI to FL to audible to Loopback. **Self-calibrate it:** with the song paused, cross-correlate his
  note-on train with the ODF over 20 s. The lag of the peak is `L_midi`. Store it per device.
- **v2 rhythm feedback:** his onset offsets against the track's beat grid (a histogram of ms early or late), the
  jam-spec MUSIC rhythm talking points applied to Spotify.

### 6.5 Routing alternative (Daniel's setting, not ours)

- Windows 11 can send each app to its own output device (Settings, Sound, Volume mixer).
- Suppose the Focusrite can loop back a playback pair that only Spotify uses, with FL and Chrome on another. Then the
  Loopback would carry the track alone, and 6.2-6.4 become unnecessary.
- Whether his interface model allows this is **unknown here**. It is also a settings change, so it is his step to try,
  or not.

---

## 7. Library survey

| Library | Live key | Live tempo | Beat phase | Licence | Delivery here | Fit |
|---|---|---|---|---|---|---|
| **Our own** (this design) | yes (KK tracker) | yes | yes (comb + PLL) | repo's Apache-2.0 | none | **Recommended v1** |
| [Essentia.js](https://github.com/MTG/essentia.js) 0.1.3 | HPCP + Key (many profiles) | RhythmExtractor, Percival BPM, TempoCNN models | beat positions from rhythm extractors | **AGPL-3.0** ([LICENSE](https://github.com/MTG/essentia.js/blob/master/LICENSE); no commercial option in the file) | CDN (jsDelivr) or vendored WASM: a download | A strong **reference** to compare against, in-browser or Node, if Daniel accepts AGPL for a local experiment. Vendoring it into the public Apache-2.0 repo is a licensing decision. The WASM build is AudioWorklet-capable per the MTG paper ([TISMIR](https://transactions.ismir.net/articles/10.5334/tismir.111)). |
| [Meyda](https://github.com/meyda/meyda) | chroma only (Gaussian filterbank over FFT: 12 bins, A440, `centerOctave` 5, `octaveWidth` 2) | no | no | MIT ([meyda.js.org](https://meyda.js.org/)) | CDN or vendor: a download | Low. Its chroma at full-rate FFT sizes lacks bass resolution (3.3), and it has no key or tempo. |
| [aubio](https://aubio.org/) / [aubiojs](https://github.com/qiuxiang/aubiojs) | no | yes (causal Tempo) | yes | aubio **GPL**; the aubiojs wrapper is MIT but links GPL code | WASM: a download | Good algorithms. Adoption is a GPL decision. |
| [realtime-bpm-analyzer](https://github.com/dlepaux/realtime-bpm-analyzer) 5.0.15 | no | yes (200 Hz low-pass, peak intervals; `bpm` about 1/s, `bpmStable` after about 5-15 s) | **no** | Apache-2.0 | npm/CDN: a download | Cross-check only. It **folds to 90-180 bpm** (5.3). |
| [web-audio-beat-detector](https://github.com/chrisguttandin/web-audio-beat-detector) | no | on an AudioBuffer (`analyze`, `guess` → bpm + first-beat offset; default 90-180) | offset only | MIT | npm/CDN: a download | Low. It could run on a rolling 15 s buffer as a phase sanity check. |
| [webKeyFinder](https://github.com/dogayuksel/webKeyFinder) / [libKeyFinder](https://github.com/mixxxdj/libkeyfinder) | yes (worker, streams) | no | no | **GPL-3.0-or-later** | WASM: a download | Reference only (GPL). |
| [BTrack](https://github.com/adamstark/BTrack) | no | yes | yes (causal cumulative score) | **GPL-3** | C++ | Algorithm reference (5.4 v2). Re-implement from the paper. |

**Offline Python, for validation:**

| Package | What it gives | Licence | On this machine |
|---|---|---|---|
| librosa 0.10.2 | `chroma_cqt`, `beat.beat_track` (Ellis DP), `feature.tempo`; no key function (KK over chroma is 20 lines) | ISC | **installed** |
| [madmom](https://github.com/CPJKU/madmom) | RNN onsets, beats, downbeats, tempo, CNN key | code BSD; **models CC BY-NC-SA 4.0** | not installed (approval) |
| [Beat This!](https://github.com/CPJKU/beat_this) | beats and downbeats, a transformer model (ISMIR 2024) | MIT (code and weights) | not installed (torch; approval) |
| [BeatNet](https://github.com/mjhydri/BeatNet) | online beats, downbeats, tempo, meter (CRNN + particle filter) | CC-BY-4.0 | not installed (torch, madmom, pyaudio; approval) |
| Essentia (Python) | KeyExtractor, RhythmExtractor2013, TempoCNN | AGPL-3.0 | **no Windows wheels**: Linux/macOS or WSL only ([install docs](https://essentia.upf.edu/installing.html)) |
| mir_eval | key weighted score, tempo, beat F-measure | MIT | not installed. The metrics are about 50 lines to re-implement; installing needs approval. |

---

## 8. Track-metadata APIs for BPM and key

| Source | What it gives | Terms and state (2025-2026) | Use here |
|---|---|---|---|
| Spotify Web API | once: `audio-features` (tempo, key, mode) | Audio Features and Audio Analysis closed to new apps since **2024-11-27** ([Spotify blog](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)). Since **Feb/Mar 2026**, Development Mode requires the owner to have **Premium**, allows one Client ID and 5 users, and supports fewer endpoints ([Spotify blog 2026-02-06](https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security), [migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)) | No BPM or key from Spotify. |
| [GetSongBPM](https://getsongbpm.com/api) / GetSongKEY | tempo, key, time signature by search | Free API key (**account sign-up**). A backlink to getsongbpm.com is **mandatory for any use, private included**, and accounts without one can be suspended without notice (per the API page, quoted in search results). 3,000 requests/hour per a third-party write-up ([MusicTech Lab](https://musictechlab.io/blog/software-development/integrating-tempus-metronome-with-the-getsongbpm-api-what-bpm-really-means-and-how-to-use-it)), which also warns about crowd-sourced errors and half/double-time confusion. The terms page returned 403 to our fetch, so these terms are second-hand. | A **prior** only, after Daniel approves the sign-up **and** a backlink (e.g. on the piano page or the akashiclabs site). |
| [ReccoBeats](https://reccobeats.com/docs/documentation/introduction) | Spotify-style features, including tempo and key; accepts Spotify track IDs | free; rate limits "configured internally" and not published ([rate limiting](https://reccobeats.com/docs/documentation/rate-limiting)); terms not found tonight | Possible prior; read the terms first. |
| [Soundcharts](https://soundcharts.com/en/audio-features-api) | BPM, key, mode, time signature, and more | commercial | Not for a personal practice page. |
| [Deezer API](https://developers.deezer.com/api) | `bpm` on a track's detail record | accept the developer terms; the field is often absent on listings (third-party docs) | Weak prior. |
| [AcousticBrainz](https://acousticbrainz.org/download) | frozen dumps with BPM and key (Essentia-computed) | CC0; shut down in 2022, partly because BPM and key were often "clearly wrong" ([MetaBrainz blog](https://blog.metabrainz.org/2022/02/16/acousticbrainz-making-a-hard-decision-to-end-the-project/)) | No: a large download, stale, and a caution about automatic estimates. |

**Rules if any source is enabled:**
- Send only title and artist, from SMTC.
- Cache the answer locally (git-ignored).
- Never send session data.
- Show the source's value next to the live one ("track says 72, hearing 144 → ÷2?").
- The live estimate plus Daniel's correction always wins.

**Spotify content rules.**
- Spotify's User Guidelines prohibit ripping or recording content, and using content to train ML or AI models
  ([User Guidelines](https://www.spotify.com/us/legal/user-guidelines/)).
- This lane analyses audio **transiently, in memory**. It stores no Spotify audio and no per-track feature dataset
  beyond Daniel's own corrections, and trains nothing on Spotify audio.
- Validation clips must be his FL renders or files he owns (section 9).
- **Flag:** the piano page's recorder already mixes the loopback input into takes (`startRecording` clones
  `audioIn`'s track). A Spotify song playing during REC lands in the file. Daniel should know that before
  practice-along recordings become routine.

---

## 9. Validation plan (offline first, no installs)

1. **Ground truth without downloads.**
   - (a) **FL Studio renders** of MIDI arrangements in known keys and tempos: drums + bass + pad + piano; pop,
     worship-style (72 bpm half-time, a pad intro, +2 semitone last chorus), EDM (126 bpm four-on-the-floor, A minor
     with detuned saws) and a rubato piano ballad. The truth is exact and time-stamped.
   - (b) **Daniel's corrections** logged by the page (lock, ×2/÷2, "this is 1") as labels.
   - (c) Optionally, tracks he owns as files, with keys he confirms by ear.
2. **One code path.** The pure DSP and estimator modules (3.1) run in Node over PCM decoded with PyAV (`analysis.py`
   already decodes to 48 k mono). They produce the same frames and the same tracker outputs as the page, keeping the
   parity-twin habit the repo already has for nashville.js and nashville.py.
3. **Reference.** librosa 0.10.2: `chroma_cqt` + KK (key), `beat.beat_track` + `feature.tempo` (tempo, beats).
   Optionally, after approval, Beat This! and Essentia's KeyExtractor (in WSL) as upper bounds.
4. **Metrics** (re-implemented, about 50 lines):
   - key exact rate and MIREX weighted score;
   - time to first key;
   - key switches per minute on steady sections (flicker);
   - modulation detection delay;
   - tempo Acc1 and Acc2;
   - octave-choice rate against Daniel's labels;
   - beat F-measure (±70 ms);
   - phase error distribution after lock;
   - time to first tempo;
   - CPU per tick (measured in the page).
5. **Genre buckets and their named risks** (pass criteria set after the first run, not guessed now):

| Bucket | Tempo risks | Key risks | Mitigation in this design |
|---|---|---|---|
| Pop | usually easy; half-time choruses | relative major/minor on vi-IV-I-V loops; borrowed bVII | LT rule, bass tonic cue, runner-up and Relative button |
| Worship | 64-80 bpm with half/double-time sections; long pad intros with no onsets; builds | sus2/sus4/add9 pads; songs that open on the IV; +1/+2 semitone last choruses | tempo hold on low ODF confidence; per-track octave memory; transposition-jump rule (4.4) |
| EDM | easy tempo at 120-130; drum and bass 170-175 counted 87 | minor keys, detuned supersaws, noise risers, sidechain pumping, long breakdowns | EDM profile when four-on-the-floor; tonal gate drops noisy frames; bass chroma |
| Piano ballads | rubato, fermatas, few percussive cues | mostly easy (clear harmony) | phase confidence hides pips; tempo shown as "loose" |

---

## 10. How it surfaces (a sketch only; the UX belongs to the integration lane)

- A **Track** readout beside the key HUD:
  `Track  E♭ major · fair · or C minor   72 bpm  [÷2 ×2 tap]  ●○○○   You: E♭ major · 94% in key`.
- Buttons: **Lock**, **Relative**, **±5th**, **This is 1**. The source toggle (live / metadata prior) is off by
  default.
- **"Numbers from": track / me / auto.** Auto uses the track key when fair or sure, else his (6.2).
- **Jam deck hooks:**
  - "Loop at track tempo" seeds a run's `bpm`.
  - v2 "follow the track" turns the PLL into a tempo-map source (jam-spec 9.1), with the stream-loss rule replaced by
    a "lost the beat" rule on low phase confidence.
- **SMTC track change:** reset the audio tracker and tempo, and load that track's stored corrections.

---

## 11. Build slices (proposal)

| Slice | Content | Receipt |
|---|---|---|
| S0 drill (Daniel present) | confirm FL and Chrome reach the Loopback; zero-output worklet runs; click round trip gives `L_in`; CPU baseline with the 3D scene | numbers written to a dated drill note |
| S1 listen | worklet + pure DSP modules (FFT, decimator, flux bands, peaks to chroma, tuning, tonal gate) | Node fixtures: sine triads → chroma argmax; click trains at 60/90/140 bpm → ODF peaks within ±1 frame; a detuned-432 fixture → tuning estimate |
| S2 tempo and phase | ACF + prior + hysteresis, tempo family, ×2/÷2/tap, comb phase + PLL, phase confidence | synthetic fixtures with a tempo step and a ramp; FL renders: Acc1/Acc2 and beat F-measure against the renders' truth |
| S3 audio key | pc-history adapter, audio tracker instance, profile parameter, bass tonic bonus, transposition jump | FL renders: exact-key rate, switches/min, modulation delay; parity against the librosa reference |
| S4 his playing | frame weights, onset gating, `L_midi` self-calibration, agreement readout | fixture: known MIDI + render with and without his part; the key and tempo stay put while he plays |
| S5 memory and prior | per-track corrections; metadata prior **only after approval** | a stored correction is honoured on replay |
| v2 | chord reading from audio feeding `hear()`, downbeats, cumulative-score phase, chroma subtraction with a calibrated gain, follow-the-track transport | per feature |

---

## 12. Open questions for Daniel

1. Does your piano sound (FL Studio / Kontakt) and Chrome's sound play through the same Focusrite output that
   "Loopback L + R" captures? Which Focusrite model is it? That decides whether the routing alternative (6.5) exists.
2. For a slow worship ballad, do you count about 70 or about 140? (Recommended default: whatever you tap once; the
   page remembers it for that song.)
3. May we sign up for GetSongBPM, which needs a visible backlink, or should key and BPM stay purely "by ear"?
   (Recommended: by ear first; decide after S3's accuracy numbers.)
4. When the track's key and yours disagree, which should the Nashville numbers follow? (Recommended: the track's key
   once it is fairly sure.)
5. Are AGPL/GPL libraries (Essentia.js, aubio) acceptable for a **local-only comparison** experiment, never committed?
   (Recommended: not needed for v1.)
6. Should practice-along recordings include the Spotify audio? The recorder mixes the loopback in today (section 8).
