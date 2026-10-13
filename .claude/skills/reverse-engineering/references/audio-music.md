# Audio and music — the operator's guide

Reverse engineering a *sound*, a *space*, a *mix*, a *passage*, and *game audio*. Distilled from
`research/reviewed/reverse-engineering-2026-10-13/audio-music.md` (the full report, five closed-loop
demos on synthetic sound we made, every source). **Not legal advice**; the legal note is below, the
full map in `method-legal-cleanroom.md`. Third-party plug-ins are untrusted samples too, and Daniel's
recordings stay under an ignored path (`state/re/<case>/` for a case; parts of `state/` are tracked).

**Never on the host:** "An untrusted sample (any file under study that the house did not build or record itself, unless Daniel has ruled that kind of file trusted) is never run, parsed, decoded or extracted on this machine: it is handled only inside a disposable VM or sandbox that is reverted afterwards, and it is kept outside the repo."

## The one-page version

1. **Every audio question is one of five shapes: a sound, a space, a mix, a passage, or a game's audio
   logic.** A *sound* asks "what made this?" (oscillator, filter, string, sample). A *space* asks
   "what did the room or box do to it?" (an impulse response). A *mix* asks "what are the parts and how
   were they balanced?" (stems, loudness, tonal balance). A *passage* asks "what notes and chords?"
   (transcription, harmony, voicing). Game audio asks "what rule decides which sound plays when?" Route
   the question first; the first tool follows from the shape.
2. **The spectrogram is the oscilloscope of this field** — frequency up, time across, level as colour.
   Its window length is a shutter speed: long windows resolve close partials of a low note, short
   windows catch a drum attack. Look at the same sound with two or three window lengths.
3. **Reverse engineering a sound is a closed loop:** analyse → guess a recipe → re-make it → compare
   with a stated number **and your ears** → repeat. **Run the loop first on a sound whose recipe you
   already know,** so you can score the method before you trust it.
4. **A good match is not "the" recipe.** Many recipes make the same sound: our test recovered a decay
   time 56% wrong while the spectral distance barely moved. Say "a patch that matches to distance D
   under loss L on synth S", never "the original patch".
5. **An impulse response is the fingerprint of a linear, time-invariant system** (a room, a static
   reverb). It cannot capture things that change over time (chorus, modulated reverb) or with level
   (compressors, saturation) — for those, learn a black-box model from input/output pairs (Neural Amp
   Modeler).
6. **Stem separation is an educated guess, not an un-mixing.** Demucs, BS-RoFormer estimate what each
   part probably was. Never measure a part's EQ or level from a separated stem as if it were the real
   multitrack.
7. **Loudness has a standard; use it** — integrated LUFS, loudness range (LU), true peak (dBTP), per
   ITU-R BS.1770 / EBU R 128. The house has a verified meter: `py -m arsenal.media audio` reads sines
   at exact levels back exactly.
8. **For Daniel's own piano, MIDI is the truth and audio is the test.** The practice log holds every
   note; `arsenal.practice` reads it. Audio transcription is for recordings with no MIDI, and the
   practice log is the perfect calibration set for it.
9. **Game audio is best learned by observing your own play and by reading projects published for
   learning** (Power Up Audio released Celeste's complete FMOD project in 2018). Opening a commercial
   game's packed audio is dual-use with legal limits; **if anything is encrypted, stop.**
10. **Copyright in music has two layers** — the composition (notes, words) and the sound recording (the
    fixed sounds), separate rights. Re-making a sound from scratch does not copy the recording (17
    U.S.C. 114(b)), but can still copy the composition; imitating a famous voice raises publicity
    rights; sampling a recognisable fragment needs a licence in practice.

## Concepts, plainly

Sample rate is the clock (Nyquist = half of it; above folds back as aliasing); bit depth is the ADC
resolution; dBFS measures against full scale; **true peak** estimates between samples. Waveform = level
over time (loudness, rhythm); spectrum = level over frequency (the ingredient list); spectrogram stacks
spectra (the STFT, windowed with a Hann taper). To separate two partials Δf apart, use a window ≥ about
2·sample-rate/Δf samples (A1's 55 Hz harmonics at 48 kHz need ≥ ~1,750; use 4,096); zero-padding
smooths, does not add resolution. Partials at whole multiples of f0 are harmonics (one pitch); real
piano strings run sharp (inharmonicity f_n = n·f0·√(1+B·n²)). The **source-filter** idea: a source
(buzz, noise) shaped by a filter (resonator, synth low-pass, vocal tract); the harmonic pattern tells
you the source, the overall slope and bumps the filter.

**Synthesis fingerprints** (observation → inference, never a product): one line = sine; all harmonics
falling ~6 dB/oct = sawtooth family; odd only ~6 dB/oct = square; every k-th missing = pulse width 1/k
(or a pluck comb); odd ~12 dB/oct = triangle; a steeper roll-off above a frequency = a low-pass (~6
dB/oct per pole, a bump = resonance); a bright band sweeping down per note = a filter envelope;
sidebands around a carrier changing while pitch holds = FM (Chowning); new harmonics as level rises =
distortion (odd-only = symmetric clipping); partials sharp with height = a real/modelled string.

**Envelopes:** ADSR on amplitude, plus filter-cutoff and pitch envelopes. Decays are exponential (τ =
"falls to 37% every τ"; T60 ≈ 6.9τ). **Measuring an envelope needs a frame that does not beat against
the pitch period** (our Drill measured a fixed 512-sample frame on a 220 Hz tone: ripple fired a false
note-off 197 ms early and inflated decay 56%; a 4-period frame fixed it).

**Impulse response and convolution** (the room's fingerprint, by TDR analogy): if a system is linear and
time-invariant, one IR captures everything it does; convolve to apply it. Measure it well with an
**exponential sine sweep** (Angelo Farina): high SNR, and harmonic distortion separates out in time (the
k-th harmonic lands L·ln(k) seconds before the linear IR — observed to four decimals). What an IR
cannot capture: anything time-variant or level-dependent — use Neural Amp Modeler for amps/pedals.
Reverb in a finished recording can only be *estimated* (watch the spectrogram tail after a hard stop).

**Mixes and stems:** summing throws information away. Separators (Demucs hybrid transformer,
BS-RoFormer, Open-Unmix) *estimate*, scored by SDR (Demucs ~9.0 dB, BS-RoFormer ~9.8 dB averaged — your
song may do far worse, with audible bleed; the six-stem piano is especially poor). **Loudness:** LUFS
(average, K-weighted, gated), true peak (the boost spike), loudness range, crest factor (limiting
flattens peaks → a histogram piles up under full scale). Targets: EBU R 128 −23 LUFS; Spotify −14 LUFS
default, true peak below −1 dBTP.

**Music:** pitch tracking (pYIN, CREPE — monophonic); onsets/beats/downbeats; AMT (polyphonic audio →
MIDI — a protocol decoder that can be wrong in crowded stretches and never knows intent); **chroma**
folds the spectrum into 12 pitch classes (chord templates; Chordino's NNLS front end exists because a
strong bass note's harmonics leak into chroma — our demo: an A bass put C# into A minor and A minor beat
A major by only 0.03); key by correlating pitch-class histograms with key profiles; **voicing** (octaves,
spacing, inversion, doublings) is lost by chroma — it needs note-level evidence (MIDI or a transcription).

**Game audio:** middleware (FMOD, Wwise) sits between game code and the card — the game says "event
*Bow_Fire* happened, Intensity is 0.7" and a sound designer decides what that means. Concepts: events,
parameters/RTPCs, switches/states, random containers, snapshots/ducking, busses, banks (.bank/.bnk),
interactive-music structure (segments, transitions, stingers), voice limits/stealing. **Adaptive music:**
horizontal re-sequencing (switch at a bar/beat), vertical layering (fade layers with game state),
stingers (short hits on an event), transitions, generative. **Feedback** (Overwatch's "play by sound":
an importance score 0–120 bucketed so one high-priority sound dominates; different ally/enemy voice
lines; per-hero footsteps; *Juice It or Lose It*).

## The method

1. Route the question (sound/space/mix/passage/game logic); checklist + evidence each needs.
2. Identity and provenance: hash; container, codec, sample rate, bit depth, channels, duration, every
   track (`py -m arsenal.media probe` and `audio`); where it came from and under what licence; keep
   third-party files out of the repo.
3. Overview pass, once: integrated loudness + true peak; a whole-file spectrogram; a long-term average
   spectrum (the codec-cutoff check lives here).
4. Hypothesis about the generator (fingerprint table for sounds; the LTI test for spaces; arrangement
   for mixes; texture for passages).
5. Zoom where a question remains (right window length, right segment — a held plateau for timbre, an
   attack for transients, a tail for reverb).
6. Close the loop: re-make and compare with a stated distance + listening; **first run it once on a
   known synthetic target and score recovered-vs-true.**
7. Ledger; revisit the checklist; when rebuilding, list observed vs our design choices.

## Playbooks in one line each

- **A sound:** pitch (pYIN) → harmonic table (long Hann FFT, read levels at k·f0) → filter fit →
  pitch-synchronous ADSR → resynthesise and search (grid for a few params; CMA-ES for tens; DDSP for a
  differentiable synth; learned inverse models). Report "a patch at distance D under loss L on synth
  S". The best loss depends on the synth (Salimi et al. 2025).
- **A space/box we own:** one interface for play + record; **low** level (distortion biases RT60);
  sweep long enough that L·ln2 exceeds the room's decay; deconvolve (REW); read frequency response,
  RT60 (T20/T30 on the Schroeder integral), reflections, distortion orders; **score the meter on a
  known IR** (a mild-distortion 6 s sweep inflated RT60 10%).
- **A mix:** lossy-history check; loudness; long-term average spectrum section-by-section (same
  instrumentation); mid/side and L-R correlation per band; stems for listening only (Matchering learns
  the *direction* of a tonal difference, not a setting).
- **A passage:** have MIDI? → `arsenal.practice`, `pianocue voicing`, `replay_harmony`. Without MIDI:
  Basic Pitch (polyphonic), Kong (piano + pedal) or Transkun (piano), MT3 (multi-instrument); beats
  from librosa/madmom; harmony from notes (best) or Chordino; voicing only from notes; score with
  mir_eval.
- **Game audio:** Route 1 (always first, always legal) — record your own play, use the game's volume
  sliders as a stem separator (music-only and SFX-only passes), analyse onset clusters (round-robin
  counts), pitch spread, short-term LUFS, ducking. Route 2 — read a published learning project (Celeste
  FMOD). Route 3 (dual-use, understanding only, VM) — vgmstream/wwiser *read* owned-game banks; **if a
  bank is encrypted, stop** and record "encrypted, not analysed".

## Routing table (audio/music)

Markers as in the master table: **(VM)** is VM-only whatever the file; **(trusted on host; untrusted → VM)**
runs on the host only for files we built or recorded, or that Daniel has ruled trusted.

| Artifact or question | First tool | Evidence | What it cannot tell you |
|---|---|---|---|
| Unknown audio file: what/what happened? (trusted on host; untrusted → VM) | `py -m arsenal.media probe` then `audio` | Container, codec, rate, tracks, LUFS/LRA/TP | Provenance; encoding history (next row) |
| "Is this really lossless/high-res?" (trusted on host; untrusted → VM) | Long-term spectrum / spectrogram | Brick-wall cutoff, empty bands, bit-depth use | Which encoder exactly (a fingerprint) |
| A single synth/instrument note (trusted on host; untrusted → VM) | pYIN + harmonic table + RMS envelope (librosa) | f0, harmonic pattern, filter shape, ADSR, noise share | Product/preset/routing; uniqueness of the recipe |
| "Give me synth parameters" (trusted on host; untrusted → VM) | Render-and-compare search on a declared synth (DawDreamer, Synplant, Harmor) | A patch at a stated distance under a stated loss | That it is the original patch |
| A retro game sound effect (trusted on host; untrusted → VM) | sfxr/jsfxr parameter match | A small parameter set that reproduces it | The original tool |
| A room/speaker/static effect we own | Exponential sweep + deconvolution (REW) | IR, RT60/EDT, frequency response, reflections, distortion orders | Time-variant / level-dependent behaviour |
| An amp/pedal/saturator we own | Input/output capture + Neural Amp Modeler | A model that imitates it | Behaviour outside the training range |
| Reverb on a finished recording (trusted on host; untrusted → VM) | Spectrogram tail after stops | Approx decay time, pre-delay (inference) | The true IR (blind problem) |
| A finished mix: what parts? (trusted on host; untrusted → VM) | Demucs / BS-RoFormer (CPU) | Estimated stems for listening | The real multitracks; parts' true EQ/levels |
| How loud/how mastered? (trusted on host; untrusted → VM) | `arsenal.media audio` (ebur128) + sample histogram | I, LRA, TP, limiting/clipping signs | The processing chain |
| "Make ours sit like theirs" (trusted on host; untrusted → VM) | LTAS at 1/3 oct, section by section; Matchering | Tonal-balance difference, width, level | Arrangement differences as EQ |
| A melody (one voice) (trusted on host; untrusted → VM) | pYIN / CREPE; Tony for editing | f0 contour, note segments | Polyphony; intended spelling |
| A polyphonic passage (trusted on host; untrusted → VM) | Basic Pitch; piano: Kong (pedal) or Transkun; ensemble: MT3 | MIDI notes with timing, velocity | Hands, notation, pedal (most), meter under rubato |
| Chords/key of a recording (trusted on host; untrusted → VM) | Notes first (transcribe → house naming); else Chordino / chroma | Chord labels, key areas | Inversions, extensions, major/minor over strong bass |
| Daniel's own playing | `arsenal.practice`, `pianocue voicing` (MIDI truth) | Windows, chords, keys, cadences, voicings | Tone, touch-to-sound, room |
| A game's adaptive music | Own play, music-only via sliders + beat tracking + event log | Which states change music, layers vs switches, quantised transitions | Authored rules/values; untriggered branches |
| A game's feedback SFX | Own play, SFX-only; onset clustering, pitch spread, short-term LUFS | Variation count, randomisation, priority, ducking | Voice-limit settings; intent |
| How professionals author game audio | Celeste FMOD project; official FMOD/Wwise samples + profiler | The actual authored structure | That it generalises beyond that team |
| An owned game's packed audio (VM) | vgmstream / wwiser, at understanding level | Structure: events, containers, transitions | Anything encrypted (stop: §1201); reuse rights |
| "Can we use this sample/voice/melody?" | `method-legal-cleanroom.md`, then a lawyer | The map of the lines | An answer for the specific facts |

## Lessons (trigger-phrased)

- Use when extracting an amplitude envelope from a pitched sound, before fitting attack/decay/release:
  make the RMS frame a whole number of pitch periods (or smooth it) and require a sustained drop before
  calling note-off. Don't when the sound is unpitched noise.
- Use when proposing any analysis pipeline for an unknown sound/room/mix, before trusting its numbers:
  run it first on a synthetic target whose recipe you know and report recovered-vs-true per parameter.
  Don't when the measurement is already pinned by a house test (e.g. `arsenal.media` loudness on sines).
- Use when a resynthesis reaches a low spectral distance, before reporting parameters as right: check
  envelopes and pitch separately and say "a patch at distance D", not "the patch". Don't when the goal
  is only "a usable similar sound".
- Use when measuring an IR with a sine sweep, before reading RT60: low level, one interface, a sweep
  longer than the room's decay, and score the meter on a known IR. Don't when the device is strongly
  nonlinear/time-variant — use input/output learning.
- Use when a file is offered as lossless, before using it as a reference: check its long-term spectrum
  for a brick wall. Don't when the source is band-limited by nature.
- Use when naming chords from audio chroma, before calling major/minor: check whether the bass's 5th
  harmonic lands on the other third, and prefer notes. Don't when MIDI exists.
- Use when separating stems, before measuring any part's EQ/level: treat stems as estimates for
  listening, expect bleed, label any stem measurement as the separator's. Don't when the real
  multitracks exist.
- Use when studying a game's music/feedback, before opening any game file: record your own play
  music-only and SFX-only via the sliders, log events, beat-track transitions, read a published
  learning project. Don't when the question truly needs authored values — then follow the VM/legal
  rules.
- Use when a game bank/stream turns out encrypted/DRM-protected, before any further step: stop, record
  "encrypted, not analysed", never look for keys. Don't when it is our own project's build.
- Use when any recording/sample/voice might go into our music/game, before release: assume a
  recognisable fragment needs a licence, re-make sounds instead of sampling (114(b)), never imitate an
  identifiable voice, use our own / CC0 / CC BY (credited) material.
- Use before installing an audio ML package (Demucs, Basic Pitch, madmom, Essentia): read the
  model-weights licence separately from the code licence, check the Python version (Basic Pitch stops
  at 3.11), remember the pinned house Python — each install is **Daniel's decision**, maybe in a
  separate venv.
- Use when analysing Daniel's piano audio, before transcription: use the practice log's MIDI as ground
  truth, align with `arsenal.media avsync` (every key sounds twice, keyboard on mic + synth on desktop,
  70–95 ms apart), keep outputs under an ignored path (`git check-ignore -v <path>`).

## Gaps (build proposals)

`media spectrum` (spectrogram + LTAS + codec-cutoff fingerprint + sample histogram); `audio profile`
(partials + envelope profiler, the Drill-A closed loop as a primitive); `audio ir` (sweep +
deconvolution + RT60 + distortion orders, with the too-short-sweep warning); `audio stems` (Demucs/
BS-RoFormer wrapper, weights-licence recorded, outputs outside the repo); `audio transcribe` with a
calibration harness scored against the practice log; `audio chords` sharing names with the MIDI path,
with the bass-harmonic check; `audio match` (render-and-compare synth search); `audio eqmatch`; a
game-audio observation kit; a sound-kit generator (sfxr-style, presets as data, per-category loudness
QC); a disposable VM profile for untrusted media/game files; a licence register for audio models and
datasets.

## Legal note (not legal advice; US, EU and UK orientation, dated 2026-10-13)

In the **US**, studying a program to reach its unprotected ideas can be fair use (*Sega v.
Accolade*, 9th Cir. 1992; *Sony v. Connectix*, 9th Cir. 2000), but a EULA or terms of service can
forbid reverse engineering and be enforced (*Bowers v. Baystate*, Fed. Cir. 2003; *Davidson v.
Jung*, 8th Cir. 2005), and DMCA §1201 separately bans circumventing access controls; its exemptions
(§1201(f), (g), (j); 37 C.F.R. §201.40) excuse only the act, under their stated conditions, never
tools. In the **EU and UK**, a lawful user may observe, study and test a program (Directive
2009/24/EC art. 5(3); CDPA s.50BA) and decompile for interoperability within art. 6's limits (CDPA
s.50B), and contract terms against those rights are void (art. 8; CDPA s.296A). In **both**,
trade-secret law allows reverse engineering a lawfully obtained product unless a valid contract
forbids it (18 U.S.C. 1839(6)(B); Directive 2016/943 art. 3(1)(b)), and ideas, methods and observed
facts are free, while code, art, audio and text are protected and a distinctive look may be protected
(*Tetris Holding v. Xio*, D.N.J. 2012, including as trade dress; republishing a whole extracted table
is a separate question in
the EU, where a database right can apply). **For this domain:** a song carries two copyrights, the
composition and the sound recording; 17 U.S.C. 114(b) lets us re-make a sound without copying the
recording, but not the composition. Sampling law is split (US: *Bridgeport*, 6th Cir. 2005, against
*VMG Salsoul*, 9th Cir. 2016; EU: *Pelham*, a sample recognisable to the ear is a reproduction, and
*Pelham II*, 2026, on pastiche), so the house does not sample recordings it does not own or license.
Imitating an identifiable voice raises publicity rights (*Midler*, *Waits*, the Tennessee ELVIS
Act), and model weights carry their own licences, separate from the code. Opening a commercial
game's encrypted audio is circumvention: stop. The full map with its caveats is
`method-legal-cleanroom.md`; anything we ship that leans on someone else's product goes past a
lawyer first.

## Sources

Full report: `research/reviewed/reverse-engineering-2026-10-13/audio-music.md` (five closed-loop demos
E1–E9, all sources S1–S70). Authors/tools credited there: Julius O. Smith III; librosa; Sonic
Visualiser (C4DM); sms-tools (MTG); DDSP (Magenta); Chowning; Angelo Farina; REW (John Mulcahy); Neural
Amp Modeler (Steven Atkinson); Demucs (Défossez); BS-RoFormer; Open-Unmix; Matchering; pyloudnorm;
Basic Pitch (Spotify); Kong et al.; Transkun; MT3; Chordino/NNLS (Mauch & Cannam); madmom; mir_eval;
FMOD; Wwise; vgmstream; wwiser; the Overwatch audio team; Jonasson & Purho; and **morluto/rea** for the
evidence discipline.
