# Reverse-engineering audio and music

- **Reverse-engineering arsenal, 2026-10-13.** One of eight topic reports written the night Daniel asked the house to
  "have the whole reverse engineering arsenal", with an Archero-style game in mind for later (a viable upgrade path,
  new weapons and effects released for free).
- **Topic:** reverse-engineering a *sound* (spectrograms, envelopes, partials, resynthesis to recover synth
  parameters, convolution and impulse responses), a *mix* (stem separation, loudness, EQ matching), a *musical
  passage* (transcription, harmony, voicing), and *game audio* (FMOD and Wwise as concepts, adaptive music, how game
  sounds signal feedback), with the copyright boundary on samples and recordings.
- **Author:** Claude (the Vandor seat), as a research subagent. Sources were read on 2026-10-13. Primary sources first
  (tool documentation and READMEs, the authors' papers, statutes and court opinions), then secondary write-ups where a
  primary page would not render for the fetcher (named as such below).
- **What was run:** five closed-loop demonstrations on **synthetic sound we made ourselves** (section 7), CPU only, in
  the session scratchpad. No third-party audio, game, binary or recording was analysed. No house code was changed. No
  git command was run. No GPU was used.
- **Discipline:** the method follows the *discipline* of the REA skill (credited as morluto/rea, [S1]), not its server
  machinery: observations, inferences and unknowns are kept apart and tied to evidence IDs (E1-E9, section 7); the
  target is routed before a tool is chosen; work is summary-first; behaviour is never inferred from names; a finding
  ledger and the original checklist are revisited at the end (section 12).
- **Not legal advice.** Section 10 is a map of where the legal lines sit, written for a non-lawyer, so that we know
  when to stop and ask a lawyer. It is jurisdiction-aware (US, EU, a few UK notes) and dated.

---

## 0. The one-page version

If you remember nothing else:

1. **Every audio question is one of four shapes: a sound, a space, a mix, or a passage.** A *sound* asks "what made
   this?" (an oscillator, a filter, a string, a sample). A *space* asks "what did the room or the box do to it?" (an
   impulse response). A *mix* asks "what are the parts and how were they balanced?" (stems, loudness, tonal balance).
   A *passage* asks "what notes and chords are being played?" (transcription, harmony, voicing). Game audio adds a
   fifth: "what rule decides which sound plays when?" (the middleware's logic). Route the question first; the first
   tool follows from the shape.
2. **The spectrogram is the oscilloscope of this field.** It shows frequency (up), time (across) and level (colour).
   Like a camera's shutter, its window length trades sharpness in time against sharpness in pitch, and you choose
   the trade per question: short windows for drum hits, long windows for the partials of a low note.
3. **Reverse-engineering a sound is a closed loop: analyse, guess a recipe, re-make it, compare, repeat.** The
   comparison must be a stated number plus your ears. And first run the loop on a sound whose recipe you already
   know, so you can score the method before you trust it on the unknown (E1, E2).
4. **A good match is not "the" recipe.** Many recipes make the same sound. Our own test recovered a decay time 56 %
   wrong while the spectral distance barely moved (E1 vs E2). Say "a patch that matches to distance D", never
   "the original patch".
5. **An impulse response is a fingerprint of a linear, unchanging system** (a room, a speaker at low level, a static
   reverb). It cannot capture things that change over time (chorus, modulated reverb) or depend on level
   (compressors, saturation). For those, use input/output capture and learning (Neural Amp Modeler [S19]).
6. **Stem separation is an educated guess, not an un-mixing.** Tools like Demucs [S20] and BS-RoFormer [S21]
   estimate what each instrument probably sounded like. Never measure a part's EQ or level from a separated stem as
   if it were the real multitrack.
7. **Loudness has a standard; use it.** Integrated loudness (LUFS), loudness range (LU) and true peak (dBTP) per
   ITU-R BS.1770 and EBU R 128 [S26]. The house already has a verified meter: `py -m arsenal.media audio` (E8).
8. **For Daniel's own piano, MIDI is the truth and audio is the test.** The practice log holds every note exactly;
   the house harmony engine (`arsenal.practice`) already reads it. Audio transcription is for recordings that have no
   MIDI, and our practice log is the perfect calibration set for it (section 7.6).
9. **Game audio is best learned by observing your own play and by reading projects published for learning**, such as
   the complete Celeste FMOD project that Power Up Audio released in 2018 [S42]. Opening a commercial game's packed
   audio files is a dual-use act with legal limits (section 10.6); if anything is encrypted, stop.
10. **Copyright in music has two layers.** The *composition* (notes, words) and the *sound recording* (the actual
    fixed sounds) are separate rights. Re-making a sound from scratch does not copy the recording (17 U.S.C. 114(b)
    [S50]), but it can still copy the composition, and imitating a famous voice raises separate publicity rights
    [S57][S58][S59]. Sampling a recognisable fragment needs a licence in practice on both sides of the Atlantic
    [S51][S53].

---

## 1. How this report applies the REA discipline to audio

The REA skill [S1] is about shipped software, but its working rules transfer to sound almost one for one. This is how
the house should read them for audio work:

| REA rule (paraphrased) | What it means for audio |
|---|---|
| Route the target first | Decide whether the question is about a sound, a space, a mix, a passage or a game's audio logic before choosing a tool (routing table, section 13). |
| Observations, inferences and unknowns are kept apart, with evidence IDs | "The partials sit at whole multiples of 220.6 Hz" is an observation. "So it is a sawtooth-family oscillator" is an inference. "Which synth it was" is usually an unknown. Every claim cites a receipt: an `arsenal.media` receipt, a script result, a saved spectrogram. |
| Summary-first; never repeat an identical analysis without a changed input | One overview pass (probe, loudness, a whole-file spectrogram), then zoom where a question remains. Re-running the same separation model on the same file with the same settings teaches nothing. |
| Inspect resources and configuration alongside code; never infer behaviour from names | A preset called "Hall", a file called `boss_theme_intense.ogg` or a middleware event called `Music_Combat_High` is a *hint*, not evidence. Measure what it does. |
| A finding ledger with confidence, search boundary and unknowns; revisit the checklist | Section 12. |
| When rebuilding, separate observed behaviour from design choices | "The pickup sound rises in pitch with each pickup" is observed; "so we will rise a semitone per pickup, resetting after 1.5 s" is our design choice, and must be labelled as ours. |
| Never choose an example on the user's behalf | Worked examples on Daniel's own material (a practice session, an FL Studio project, his room) are *proposed*; he picks which one. |
| Bounded negative searches stay bounded | "No reverb tail above -60 dBFS within 2 s of the last note-off" is a bounded negative. "There is no reverb" is not. |

---

## 2. Concepts, plainly

### 2.1 Sound as numbers

A digital recording is a list of numbers, one per tick of a clock, describing how far a microphone diaphragm (or a
speaker cone) is pushed in or out.

- **Sample rate** is the clock: 44,100 or 48,000 ticks per second. Like an oscilloscope's sampling rate, it limits
  the highest frequency you can capture to half the rate (the *Nyquist frequency*): 22.05 kHz at 44.1 kHz. Anything
  above that folds back down as false tones (*aliasing*), the audio cousin of a moiré pattern.
- **Bit depth** is the resolution of each number: 16 bits gives about 96 dB between the loudest and the quietest
  step; 24 bits about 144 dB. Think of it as the ADC's resolution on a scope.
- **dBFS** (decibels relative to full scale) measures a sample's level against the largest number the format can
  hold. 0 dBFS is the ceiling; everything is negative.
- **True peak** (dBTP) estimates how high the waveform goes *between* the samples once it is turned back into a
  smooth signal. A file can have sample peaks at -0.1 dBFS and a true peak above 0, which clips in a decoder.

### 2.2 Waveform, spectrum, spectrogram

- The **waveform** (level over time) shows loudness and rhythm, and almost nothing about timbre.
- The **spectrum** (level over frequency, for one stretch of time) shows which frequencies are present: the
  ingredient list.
- The **spectrogram** stacks many short spectra side by side: frequency up, time across, level as colour. It is the
  single most useful picture in this field. The computation is the *short-time Fourier transform* (STFT): cut the
  signal into overlapping windows, taper each window's edges (a Hann window is the usual taper), and take a spectrum
  of each one. Julius O. Smith's free online book is the primary reference [S2].

**The window length is a shutter speed.** A long window (say 4,096 samples, 85 ms at 48 kHz) resolves frequencies
about 12 Hz apart but blurs anything faster than 85 ms. A short window (256 samples, 5 ms) catches a drum attack
sharply but cannot tell two partials apart unless they are about 190 Hz apart. Rules of thumb:

- To separate two partials that are Δf apart with a Hann window, use a window of at least about 2 × sample rate / Δf
  samples. The harmonics of A1 (55 Hz) are 55 Hz apart, so at 48 kHz you need at least about 1,750 samples: use 4,096.
- *Zero-padding* (adding silence before the FFT) makes the picture smoother; it does not add resolution.
- When in doubt, look at the same sound with two or three window lengths. Our sound-matching distance does exactly
  that (a *multi-resolution* STFT distance, the loss family DDSP made popular [S6]).

**Frequency axes.** A linear axis is good for spotting harmonic spacing. A log axis or a *constant-Q transform* (CQT)
puts every octave the same height, which matches musical pitch. A *mel* axis approximates how human hearing spaces
pitch. Chroma (section 2.9) folds all octaves into 12 pitch classes.

### 2.3 Partials, harmonics, noise, and the source-filter idea

Most pitched sounds are a stack of sine waves called **partials**. When the partials sit at whole multiples of a
lowest frequency (the **fundamental**, f0), they are **harmonics**, and we hear one pitch. When they do not (bells,
metal bars, drums), we hear a clang or an ambiguous pitch.

- **Inharmonicity:** a real piano string is stiff, so its upper partials run sharp:
  f_n = n · f0 · sqrt(1 + B · n²), with B a small stiffness number (Harvey Fletcher's 1962 model). Our chord demo
  synthesises piano-like tones this way (section 7.4).
- **Noise** components (breath, bow scrape, hammer thump, snare wires) are broadband and show up on a spectrogram as
  smeared regions rather than lines.
- **Formants** are fixed resonant peaks (a voice's mouth shape, a guitar body) that stay put while the pitch moves.
- **The source-filter model** says many sounds are a *source* (a buzz, a noise) shaped by a *filter* (a resonator, a
  synth's low-pass filter, a vocal tract). Reverse-engineering often means separating the two: the harmonic
  *pattern* tells you about the source, the overall *slope and bumps* tell you about the filter.

Spectral modelling (Xavier Serra and Julius Smith's *sinusoids plus noise*, taught with the MTG's sms-tools [S5])
analyses a sound into tracked partials plus a noise residual and can resynthesise it from those.

### 2.4 Envelopes

An **envelope** is how something changes over a note's life.

- The classic **ADSR** amplitude envelope: *attack* (rise time), *decay* (fall to the held level), *sustain* (the held
  level while the key is down), *release* (fall after the key is let go).
- Synths also put envelopes on **filter cutoff** and **pitch**. On a spectrogram, a filter envelope looks like a
  bright band that sweeps down as the note goes on; a pitch envelope bends every partial line together.
- Decays are usually exponential. A time constant τ means "falls to about 37 % (-8.7 dB) every τ seconds". The time
  to fall 60 dB, T60, is about 6.9 τ.

Measuring an envelope sounds trivial and is not: the measurement window must not beat against the waveform's own
period (section 8, lesson 1; E1 versus E2).

### 2.5 Synthesis families and their fingerprints

This table is the "which oscillator was it?" cheat sheet. Each row is an *observation you can make on a spectrogram*
and the *inference it supports*. None of it identifies a product.

| What you see | What it suggests | Notes |
|---|---|---|
| One line only | Sine (or a very heavily filtered tone) | |
| All harmonics, falling about 6 dB per octave | Sawtooth family | Even and odd harmonics at comparable levels (E2: even minus odd -3.6 dB over the first ten, which a 1/n series plus a filter explains) |
| Odd harmonics only, falling about 6 dB per octave | Square wave (50 % pulse) | |
| Every k-th harmonic missing | Pulse of width 1/k (25 % pulse: every 4th missing) | Plucked strings show the same comb from the pluck position |
| Odd harmonics falling about 12 dB per octave | Triangle | |
| Harmonics then a steeper roll-off above some frequency | Low-pass filter; slope ≈ 6 dB/octave per filter pole | A resonant bump at the cutoff means resonance (Q) |
| Bright band sweeping down during each note | Filter envelope | |
| Sidebands spaced at a fixed distance around a carrier, brightness changing while pitch holds | FM synthesis | John Chowning's 1973 paper is the primary source [S7]: sidebands at carrier ± k × modulator, amplitudes set by the modulation index; non-integer ratios give bell-like inharmonic spectra |
| Sum and difference tones, carrier absent | Ring modulation | AM keeps the carrier |
| A harmonic comb with a formant-like peak that sweeps | Hard sync | |
| Spectrum shape morphing, partial spacing fixed | Wavetable scanning | |
| Slow amplitude wobble at a steady rate | Two detuned oscillators (beat rate = detune in Hz), unison, chorus | |
| New harmonics appearing as level rises | Distortion or saturation; odd-only means symmetric clipping, even means asymmetric | E3 shows this in an impulse-response measurement |
| A pattern repeating at a fixed interval inside a long note | A sampled sound's loop points | Samples also show velocity layers (timbre jumps at a level threshold) and round-robins (near-identical repeats) |
| Partials running sharp with height | A real or physically modelled string | Fletcher's inharmonicity |
| Lines continuing after the note stops, smeared | Reverb; discrete repeats mean delay | |

### 2.6 Impulse responses and convolution: the room's fingerprint

If a system is **linear** (twice the input gives twice the output) and **time-invariant** (it behaves the same
today and tomorrow), then everything it does is captured by one recording: its **impulse response** (IR), its
reply to an infinitely short click. To make any sound "as if played in that room", you **convolve** it with the IR
(every sample of the sound launches a scaled copy of the IR; the copies add up). That is exactly what a convolution
reverb plug-in does (FL Studio ships one, Fruity Convolver).

*Hardware analogy:* a time-domain reflectometer (TDR) sends a fast edge down a cable and reads the reflections to
find every impedance bump. An impulse-response measurement does the same to a room or a speaker.

**How to measure one well: the exponential sine sweep.** A click is too quiet to beat background noise. Angelo
Farina's method (AES Convention, February 2000 [S17]) plays a sine whose frequency rises exponentially (say 20 Hz to
20 kHz over several seconds), records the result, and convolves the recording with a time-reversed, level-tilted
copy of the sweep. Out comes the IR, with two bonuses:

- the signal-to-noise ratio is high, because the sweep's energy is spread over seconds;
- **harmonic distortion separates out in time**: the k-th harmonic's response lands L · ln(k) seconds *before* the
  linear IR (L is the sweep's time per natural-log of frequency ratio). We observed this to four decimal places (E3).

Room EQ Wizard (REW, John Mulcahy, free with an optional Pro upgrade [S18]) does the whole job with a GUI: sweeps,
IR, RT60, waterfalls.

**What an IR cannot capture.** Anything that changes with time (chorus, flanger, modulated reverb tails) or with
level (compressors, limiters, amp saturation beyond mild distortion). For level-dependent boxes, the modern approach
is black-box learning from input/output pairs: Neural Amp Modeler (Steven Atkinson, MIT licence [S19]) plays a
standard input file through an amp or pedal, records the output, and trains a network that imitates it.

**Reverb in a finished recording** (no access to the room) cannot be measured, only estimated: watch how fast the
spectrogram tail falls after the music stops, or after a hard stop, and report it as an inference. Removing it
("blind dereverberation") is an ill-posed problem; DDSP reports it on trained domains [S6], not as a general tool.

### 2.7 Mixes and stems

A **mix** is the sum of many parts (stems) after each was processed (EQ, compression, reverb) and balanced. Summing
throws information away: two parts playing the same frequency at once land in the same spectrogram cell, and nothing
in the mix says which part owned how much of it.

**Stem separation** therefore *estimates*. Modern separators (Demucs's hybrid transformer [S20], BS-RoFormer [S21],
Open-Unmix [S23]) are trained on multitrack datasets such as MUSDB18 (150 tracks, four stems, academic use only
[S24]) to predict what each part probably was. Quality is scored by **SDR** (signal-to-distortion ratio, dB, higher
is better): the fine-tuned Demucs reports 9.00 dB averaged over stems on the MUSDB-HQ test set [S20]; BS-RoFormer
reports 9.80 dB without extra data and won the music track of the Sound Demixing Challenge 2023 [S21]. Those are
averages; your song may do far worse, and the stems keep audible "bleed" from other parts. Demucs's own README warns
that the six-stem model's piano stem suffers heavy bleeding and artefacts [S20].

*Hardware analogy:* recovering per-core power draw from a single wall-socket meter. With a good model of each core's
typical behaviour you can guess well, but the meter itself never told you.

### 2.8 Loudness: average power versus boost spikes

- **Integrated loudness (LUFS)** is the programme's average perceived loudness, measured with a K-weighting filter
  (approximating the ear's sensitivity) and two gates that ignore silence (ITU-R BS.1770; EBU R 128 [S26]). It is
  like a chip's sustained power draw.
- **True peak (dBTP)** is the highest inter-sample peak: the boost spike.
- **Loudness range (LU)** is how much the loudness moves over the programme (EBU Tech 3342).
- **Crest factor** (peak minus RMS) is how spiky the waveform is. Heavy limiting flattens peaks: the crest factor
  drops and a histogram of sample values piles up just under full scale.

Targets differ by destination. EBU R 128 broadcast is -23 LUFS (version 5.0, November 2023 [S26]). Spotify
normalises playback to -14 LUFS by default (-11 "loud", -19 "quiet") and asks for masters with true peak below
-1 dBTP, or below -2 dBTP if the master is louder than -14 LUFS [S28]. The house's `arsenal.media` audio door already
measures I, LRA and TP with ffmpeg's `ebur128` filter and was verified against sine waves at exact levels (the
`arsenal.media.audio` module records 997 Hz sines at -20/-26/-30 dBFS reading back at exactly -20.0/-26.0/-30.0 LUFS
[S16]).

### 2.9 Music: pitch, notes, chords, keys, voicings

- **Pitch tracking** follows f0 over time in a single voice: pYIN (Mauch and Dixon, 2014; in librosa as
  `librosa.pyin` [S3]) or CREPE (a neural tracker, Kim, Salamon, Li and Bello, 2018, MIT licence, monophonic only
  [S15]).
- **Onsets** are where notes start (energy or spectral-flux jumps). **Beats** and **downbeats** give the metric grid
  (librosa, madmom [S35]).
- **Automatic music transcription (AMT)** turns polyphonic audio into notes (MIDI). *Hardware analogy:* a logic
  analyser's protocol decoder turning raw voltage edges into bus transactions. The decoder can be wrong in noisy or
  crowded stretches, and it never knows what the programmer *meant*.
- **Chroma** folds the spectrum into 12 pitch classes (C, C#, ..., B). Matching chroma against chord templates gives
  chord labels; Chordino (Matthias Mauch and Chris Cannam) does this with a cleverer front end, NNLS Chroma, that first
  estimates notes so that harmonics do not pollute the pitch classes [S34]. Our demo shows why that matters: the bass
  note's 5th and 7th harmonics leak into chroma as pitch classes that are not in the chord (E7).
- **Key** is found by correlating pitch-class histograms with key profiles (Krumhansl-Kessler). The house's practice
  engine does this with a 24-key Viterbi path and a leading-tone rule (`arsenal/practice.py` docstring).
- **Voicing** (which octave each note sits in, the spacing, the inversion, what is doubled) is *lost* by chroma.
  Voicing needs note-level evidence: MIDI, or a transcription.

### 2.10 Game audio: middleware, adaptive music and feedback

**Middleware** (FMOD Studio by Firelight Technologies, Wwise by Audiokinetic) sits between the game code and the
sound card. The game does not say "play file X at volume Y"; it says "event *Bow_Fire* happened, and *Intensity* is
0.7". A sound designer, in the middleware's own authoring tool, decides what that means. *Hardware analogy:* the game
raises interrupts and writes control registers; the middleware is a programmable mixer chip whose firmware the sound
designer writes.

Core concepts, with each tool's word for it (FMOD's documentation pages render in a browser only, so FMOD terms here
come from its glossary as quoted by course notes [S38]; Wwise terms from Audiokinetic's blog and learning material
[S40][S41]):

| Concept | FMOD Studio | Wwise | Plain meaning |
|---|---|---|---|
| The thing the game triggers | Event | Event (which runs Actions on objects) | "Something happened" |
| A number the game feeds in | Parameter | RTPC (real-time parameter control) | Health, speed, intensity, distance |
| A category the game sets | Labelled parameter | Switch (per object), State (global) | Surface material, game mode |
| Variation | Multi instrument, scatterer instrument | Random container | Pick one of several takes, randomise pitch and volume |
| A saved mix change | Snapshot | State-driven mixer changes, ducking | "Low health: muffle everything" |
| Routing groups | Buses, mixer | Busses (Master-Mixer hierarchy) | Music, SFX, UI, voice, each with its own fader and effects |
| Build output | Bank (.bank) | SoundBank (.bnk) plus streamed media | The packed, compressed result the game loads |
| Interactive music structure | Timeline plus logic tracks: loop regions, destination markers, transition markers and regions (quantised to bars/beats) | Interactive Music hierarchy: segments, playlist containers, switch containers, transitions, stingers | The rules for moving between pieces of music without a seam |
| Too many sounds at once | Max instances, stealing | Voice limits, priority, virtual voices | Who gets dropped when 40 arrows hit at once |

Both tools have live **profilers** for your *own* project, which is the honest way to learn what a design does.

**Adaptive music techniques** (the classification Audiokinetic's own blog uses [S41], and the literature since
iMUSE):

- **Horizontal re-sequencing:** switch to a different section or piece, but only at a musically safe point (the next
  bar, the next beat, a marked exit cue), optionally through a short bridge. Like a railway switch that only moves
  at junctions.
- **Vertical layering (re-orchestration):** the same piece is written as stacked layers (pads, drums, guitars) and
  layers fade in and out with game state. Darren Korb's score for *Hades* is commonly described this way (a calmer
  layer set while safe, more instruments as a fight builds) in secondary write-ups; we did not read a primary source
  for it.
- **Stingers:** short musical hits laid over the running music on an event (a kill, a level-up), synced to the beat.
- **Transitions:** rules for fades, sync points and bridge segments between any two states.
- **Generative/procedural:** the music is assembled or synthesised by rules at runtime.

The historical root is **iMUSE**, the LucasArts system by composers Michael Land and Peter McConnell, added to the
SCUMM engine in 1991 and patented as US 5,315,057 (filed 1991, granted 24 May 1994 [S43]). The patent has long
expired; the idea is common practice now.

**How game sounds signal feedback.** Two primary sources are worth keeping:

- Blizzard's *Overwatch* audio team (Scott Lawlor and Tomas Neumann, GDC 2016, "The Elusive Goal: Play by Sound"
  [S44]) set the goal that a player should be able to play by sound. Reported techniques: an **importance score**
  (0-120) per sound sorted into buckets so that only one high-priority sound dominates at a time; **different voice
  lines for allies and enemies** for the same ultimate ability (allies hear one line, enemies a different, threatening
  one); per-hero footstep identity; and propagation modelling around obstacles.
- Martin Jonasson and Petri Purho's GDC Europe 2012 talk "Juice It or Lose It" [S45] took a dull Breakout clone and,
  live, layered tweening, particles, screen shake and sound until every hit felt rewarding. Sound is one of the
  layers that turns an interaction into a reward.

Our own working principles for feedback sound, as *inferences* from these sources and common practice (labelled as
ours): every player action answers immediately; each weapon family owns a recognisable timbre; important events
outrank spam through priority, instance limits and ducking; repeated sounds vary (random take, small pitch and level
spread) to avoid the "machine-gun" effect; rewards climb (pickup chains rising in pitch is a widely used convention);
threats are telegraphed by an audible wind-up; and the mix changes with player state (low health muffles).

---

## 3. The method, step by step

This is the general loop. The playbooks in section 4 specialise it.

1. **Route the question.** Sound, space, mix, passage, or game-audio logic? Write the checklist of questions and the
   evidence each one needs (REA rule 1).
2. **Establish identity and provenance.** Hash the file; record container, codec, sample rate, bit depth, channels,
   duration and every audio track (`py -m arsenal.media probe <file>` and `audio <file>`). Note where it came from and
   under what licence (section 10). Keep third-party files out of the repo (section 11).
3. **Overview pass, once.** Integrated loudness and true peak; a whole-file spectrogram; a long-term average spectrum
   (the codec cutoff check of section 7.3 lives here). Write down what you see as observations with an evidence ID.
4. **Form a hypothesis about the generator.** Use the fingerprint table (2.5) for sounds, the LTI test (does twice the
   input give twice the output?) for spaces and boxes, the arrangement and instrumentation for mixes, the texture
   (monophonic or polyphonic, pedalled or dry) for passages.
5. **Zoom where a question remains.** The right window length, the right segment (a held plateau for timbre, an attack
   for transients, a tail for reverb).
6. **Close the loop.** Re-make the thing (resynthesise the sound, convolve with the measured IR, re-sum the stems,
   play the transcription back) and compare with a stated distance plus listening. **Before** trusting the method on
   the unknown target, run it once on a known synthetic target and score recovered-versus-true (section 7).
7. **Keep a finding ledger.** Each conclusion: evidence IDs, confidence, what kind of evidence (measured, inferred,
   heard), the search boundary, the remaining unknowns.
8. **Revisit the checklist.** Mark each question answered, partly answered or unresolved. When rebuilding something,
   list which parts were observed and which are our design choices.

---

## 4. Playbooks

Each playbook carries its own legal note and, where it touches files we did not make, a host-safety note. Section 10
has the full legal map; section 11 the full safety rule.

### 4.1 Reverse-engineering a sound (a synth patch, a sample, a sound effect)

**Use when:** "How was this sound made?", "Can we make one like it?", "Which synth parameters would get close?"

**Steps.**

1. Pick a clean, isolated example (a single note or hit, ideally several at different pitches and velocities). If the
   sound is inside a mix, separate first (4.3) and accept that the stem is an estimate.
2. **Pitch:** pYIN on the held part (`librosa.pyin`), median over voiced frames. Check for vibrato or pitch envelopes
   on the f0 curve.
3. **Harmonic table:** on a steady stretch, a long Hann-windowed FFT; read the level at each multiple of f0. Look at
   even versus odd harmonics, the slope, missing harmonics, and whether partials run sharp (inharmonicity).
4. **Filter:** divide the harmonic levels by the source's expected slope (1/n for a saw) and fit a filter magnitude
   curve (cutoff, order, resonance). Track the cutoff over time on the spectrogram to find a filter envelope.
5. **Envelopes:** RMS with a **pitch-synchronous frame** (a whole number of periods, E2), then fit attack (10-90 %
   rise), decay time constant, sustain level and release time constant.
6. **Noise and modulation:** look for a noise floor under the partials (breath, a noise oscillator), amplitude
   wobble (detune, tremolo), partial smearing (chorus, unison).
7. **Resynthesise** with a declared model (your own simple synth, an open synth, or a commercial one) and compare with
   a multi-resolution STFT distance **and your ears**. Iterate the parameters by search:
   - grid search for a few parameters (what E2 did);
   - evolutionary search (CMA-ES) for tens of parameters: Philipp Bogdan's 2026 *Instrumental* pairs a 28-parameter
     differentiable subtractive synth with CMA-ES and reports that gradient descent stalled where CMA-ES kept improving
     [S10];
   - gradient descent through a differentiable synth (DDSP [S6]);
   - learned inverse models: Yee-King, Fedden and d'Inverno (2018) matched sounds on Dexed (a DX7 emulation); their
     best model, a bidirectional LSTM, matched closely in 25 % of test cases [S8].
8. **Name the loss you used.** Salimi, Hindle and Zaïane (2025) compared four similarity measures over four simple
   synths and found that the best loss depends on the synth: there is no universally right distance [S9].
9. Report "a patch matching to distance D under loss L on synth S", with the recovered values, their likely error
   (from your closed-loop test) and what could not be identified.

**Tools.** librosa (ISC) [S3]; Sonic Visualiser (free, open source, from Queen Mary University of London's Centre
for Digital Music, version 5.2.1 released 21 March 2025) with Vamp plug-ins [S4]; sms-tools (AGPL-3.0, sinusoidal and
harmonic-plus-stochastic models) [S5]; DDSP (Google Magenta) [S6]; DawDreamer (David Braun, GPL-3.0; hosts VST
instruments and effects from Python, renders with automation, supports Faust and JAX) [S11] as the render engine for a
search over a real synth's parameters; Synplant 2's Genopatch (Sonic Charge, commercial, about USD 149; grows synth
patches from up to two seconds of a sample, locally on the CPU) [S12]; Image-Line's Harmor (part of Daniel's FL Studio
world; an additive synth that analyses an audio file into up to 500 partials per voice and resynthesises it, also as
an editable image) [S13]; sfxr (DrPetter, MIT licence, Ludum Dare 10, December 2007) and its ports jsfxr and Bfxr [S14]
for retro game effects.

**Evidence it yields:** f0, harmonic pattern, filter shape, envelope times, noise share, a matching patch.
**Cannot tell you:** the product or preset used, the modulation routing that was not exercised by the example, or
whether a matching patch is the original (non-identifiability). E1 versus E2 shows a decay time off by 56 % with a
spectral distance that barely changed.

**Legal note.** Analysing a sound to learn how it was built is not copying. Re-making a similar sound from scratch
is protected in the US by 17 U.S.C. 114(b), which says a sound recording's rights do not reach an independent
fixation of other sounds even if they imitate the original [S50]. That covers the *recording*; it does not license a
copied *melody or composition*, and imitating a famous singer's voice can violate publicity rights (section 10.3).
Commercial presets are covered by the synth's licence; recreating a preset's *sound* with your own parameter values
is different from copying the preset file. Not legal advice.

**Host safety.** Synths and plug-ins are executable code. Only load plug-ins we bought or that are open source from
their official source; never load a cracked or unknown plug-in. Untrusted audio files are parsed by decoders (C code)
and belong in a VM (section 11).

### 4.2 Reverse-engineering a space or a processor (impulse responses, captures)

**Use when:** "What does this room do?", "What does this reverb or speaker do?", "Can we have this space or box in
the computer?"

**Steps for a room or speaker we own.**

1. Use one audio interface for both playing and recording (one clock; a second clock drifts and smears the result).
2. Set a **low** playback level (distortion biases the result, E4), close windows, silence fans.
3. Play an exponential sweep (20 Hz-20 kHz). Make it long enough that L · ln 2 exceeds the room's expected decay
   time, so the distortion responses do not overlap the linear one (E4). Record. Repeat three or more times and
   average.
4. Deconvolve (REW does it; so does our script, Appendix A). Window out the linear IR.
5. Read: frequency response, RT60 (fit T20 or T30 on the Schroeder backward integral, per ISO 3382-1 practice),
   early-decay time, the first reflections (distance = delay × 343 m/s), and the harmonic distortion responses.
6. **Score the meter on the truth** when you can: we ran our RT60 meter on the known IR first (0.603 s for a true
   0.6 s), which showed the error lived in the measurement, not in the meter (E3, E4).

**Steps for a plug-in or hardware we own.** Render a sweep (or a single-sample click) through it offline. For an
LTI effect (static EQ, non-modulated reverb, a cabinet) the IR captures it. For level-dependent effects (compressors,
saturators, amps), measure a static curve with stepped sine levels and attack/release with tone bursts, or train a
black-box model on input/output pairs (Neural Amp Modeler [S19]).

**Tools.** REW (free) [S18]; our sweep and deconvolution script (Appendix A, numpy/scipy); FL Studio's Fruity
Convolver to play an IR back; Neural Amp Modeler (MIT) [S19].

**Evidence it yields:** IR, RT60/EDT, frequency response, reflection times, harmonic distortion by order.
**Cannot tell you:** anything time-variant or level-dependent beyond mild distortion; the room's geometry beyond
reflection delays; a reverb plug-in's algorithm.

**Legal note.** Measuring a physical space or a device you own is observation, not copying. IRs captured from a
*commercial plug-in* are data derived from licensed software: keep them for study, and read the plug-in's licence
before distributing them. Brand names of measured hardware are trademarks; use them descriptively only. Not legal
advice.

**Host safety.** Nothing here runs untrusted code. A downloaded IR pack is just WAV files, but still keep third-party
IRs out of the repo.

### 4.3 Reverse-engineering a mix (stems, loudness, EQ, stereo)

**Use when:** "How was this mixed and mastered?", "Why does theirs sound bigger?", "Make ours sit like that".

**Steps.**

1. **Identity and history** (section 7.3): is this really lossless? A brick-wall cutoff near 16-20 kHz means it was
   lossy at some point.
2. **Loudness:** `py -m arsenal.media audio <file>` for I, LRA and TP per track. Add the short-term loudness maximum
   and a sample-value histogram (limiting shows as a pile-up just under full scale; clipping as a spike at it).
3. **Tonal balance:** the long-term average spectrum (LTAS), smoothed to one-third or one-sixth of an octave. Compare
   with your mix **section by section** (chorus with chorus), never whole song against whole song when arrangements
   differ.
4. **Stereo:** mid/side energy per band and the left-right correlation per band. Bass usually sits in the middle; wide
   high-frequency content means stereo effects or double-tracking.
5. **Structure:** where the energy and the spectrum change (novelty and self-similarity) shows the sections.
6. **Stems for listening:** separate with Demucs (`htdemucs`, or `htdemucs_ft`, four times slower and slightly better;
   CPU works at roughly 1.5 times the track's length per its README, `-d cpu`, `--segment` for memory [S20]), or
   BS-RoFormer and Mel-RoFormer models through `python-audio-separator` (MIT, Andrew Beveridge; wraps the Ultimate
   Vocal Remover models; CPU install available [S22]). Daniel's FL Studio (Producer Edition and above, since 21.2) has
   built-in stem separation into vocals, music, bass and drums; MusicTech reported it is based on Demucs's hybrid
   model and needs an internet connection [S25]: check what it uploads before using it on anything private.
7. **Match, carefully:** Matchering (Sergei Gribov, GPL-3.0) matches a target's RMS, frequency response, peak level
   and stereo width to a reference [S29]. Use it to learn the *direction* of a difference, then make your own moves.

**Tools.** `arsenal.media` (audio, qc, peaks) [house]; pyloudnorm (Christian Steinmetz, MIT, BS.1770-4) as an
independent cross-check [S27]; Demucs (MIT code) [S20]; python-audio-separator (MIT) [S22]; Open-Unmix (MIT code;
its default `umxl` weights are licensed for non-commercial use only, CC BY-NC-SA 4.0) [S23]; Matchering (GPL-3.0)
[S29]; museval/BSSEval for SDR when you have ground-truth stems [S24].

**Evidence it yields:** loudness targets, dynamics, tonal balance, stereo picture, estimated parts.
**Cannot tell you:** the true multitracks, the plug-ins used, or the order of processing. A separated stem's EQ is
partly the separator's own filtering.

**Legal note.** Analysing a commercial song you lawfully have, privately, to learn from it is the normal practice of
mixing engineers; *publishing* or *distributing* stems or remixes of it is reproduction and adaptation without a
licence. Model weights carry their own licences, separate from the code (umxl NC, madmom models NC-SA, Essentia
models NC-ND, MUSDB18 academic-only) [S23][S35][S36][S24]. Use a copy you own in a DRM-free form; never defeat stream
protection to get one (section 10.5). Not legal advice.

**Host safety.** Decoding untrusted media runs C parsers: keep downloaded or third-party files in a VM or at least
out of the repo, and never execute anything that came with them.

### 4.4 Reverse-engineering a musical passage (transcription, harmony, voicing)

**Use when:** "What is he playing here?", "What chords are these?", "How is that chord voiced?"

**First routing decision: do we have MIDI?** For Daniel's piano, yes: the practice log (`arsenal.performance`) holds
every note, pedal and velocity, and the house engine reads it:

- `py -m arsenal.practice ...` names harmonic windows, key areas and cadences over his sessions (read only; output
  under `state/`, never tracked);
- `py -m arsenal.pianocue voicing ...` prints chord names, Nashville numbers and voicings using the piano page's own
  THEORY code;
- `arsenal.replay_harmony` gives pedal-aware sounding durations for a replay excerpt.

**Without MIDI (a recording):**

1. Is it one line or many? One line: pYIN [S3] or CREPE [S15], or Tony (the Sonic Visualiser family's pitch
   transcriber [S4]) to segment notes with a human in the loop.
2. Polyphonic, one instrument: Basic Pitch (Spotify, Apache-2.0; polyphonic, instrument-agnostic, writes MIDI with
   pitch bends; its authors note it does best on a single instrument; Python 3.7-3.11) [S30].
3. Piano specifically: Qiuqiang Kong et al.'s high-resolution piano transcription (ByteDance, Apache-2.0; notes with
   velocity **and sustain pedal**) [S31], or Transkun (Yujia Yan, Frank Cwitkowitz and Zhiyao Duan, MIT; semi-CRF
   decoding of note intervals) [S32].
4. Several instruments: MT3 (Google Magenta, Apache-2.0, multi-instrument; run in its Colab notebook; training is not
   easily supported) [S33], or separate stems first and transcribe each.
5. **Grid:** beats and downbeats (librosa; madmom, BSD code with CC BY-NC-SA model files [S35]) to quantise notes
   into bars.
6. **Harmony:** from notes (best): feed the transcribed MIDI to the house's chord naming; from audio directly:
   Chordino in Sonic Visualiser [S34] or chroma plus templates (E6, E7).
7. **Voicing:** only from notes. Chroma cannot see octaves.
8. **Score yourself** with mir_eval (Colin Raffel et al., MIT) against any ground truth you have [S37].

**Evidence it yields:** notes, timing, chords, key, voicings (from notes).
**Cannot tell you:** the written score's spelling and notation choices, which hand played which note, the intended
meter where rubato is heavy, and (for most models) the pedal. Dense, pedalled passages produce merged and missing
notes; a house lesson already records that audio-to-MIDI latches the wrong attack in legato and pedal passages.

**Legal note.** Transcribing a copyrighted composition for private study is everyday musicianship; publishing the
transcription, or recording it, needs the composition owner's licence (print rights, mechanical rights). Chord
progressions and other commonplace building blocks are not protected on their own: the Second Circuit held in 2024
that the four-chord progression and harmonic rhythm of "Let's Get It On" were too commonplace to protect [S55], and
the Ninth Circuit in 2022 (Gray v. Hudson) that a simple eight-note ostinato built from common elements was not
protectable [S56]. Melodies and distinctive combinations can be. Not legal advice.

**Host safety.** Daniel's recordings and practice logs are private and stay under `state/` (git-ignored). Third-party
recordings stay out of the repo.

### 4.5 Reverse-engineering game audio (observation first)

**Use when:** "How does this game make its music react?", "Why do its hits feel so good?", "How should our game's
audio be organised?"

**Route 1: observe your own play (always legal, always first).**

1. Record a play session with OBS, with the game audio on its own track (the studio's six-track map puts *Game* on
   OBS track 3, which ffmpeg and `arsenal.media` call audio index 2 [S16]). Log the in-game events you care about with
   timestamps (a hotkey marker or a spoken note on the Voice track).
2. **Use the game's own volume sliders as a stem separator.** Record one run with music only (SFX at 0), another with
   SFX only. Replays or deterministic seeds let you record the same sequence twice.
3. **SFX grammar:** detect onsets, cluster repeated events by spectral similarity, and count: how many distinct takes
   per action (round-robin), how much pitch spread (pYIN over each instance), how loud each category is (short-term
   LUFS), what happens when many fire at once (do instances get cut, does the level cap?), whether music ducks when
   important sounds fire.
4. **Music logic:** beat-track the music-only recording; mark every change of state in the game and check whether the
   music change landed on a bar or beat (quantised horizontal transition), faded layers in or out (vertical layering),
   or laid a stinger on top.
5. Write it up as observations (what changed when) and inferences (what rule probably drives it), never as the
   designer's actual parameter values, which observation cannot see.

**Route 2: read projects published for learning.** The best primary evidence of how professionals structure game
audio is a real project opened in the real tool:

- **Celeste**: Power Up Audio (Kevin Regamey) released the game's complete FMOD Studio project, with its sounds and
  music, on 1 May 2018, via FMOD's download page, with notes inside the events explaining what each does and why
  [S42]. Read the licence text that comes with the download before reusing any asset: treat it as a study project.
- FMOD and Wwise both ship official example and tutorial projects with their free tools (Wwise's learning
  certifications use a sample game). These show transitions, RTPC curves and voice limits with the profiler running.

**Route 3: static study of an owned game's audio files (dual-use; understanding level only).** FMOD games ship
`.bank` files and Wwise games `.bnk` soundbanks with `.wem` media. Community tools exist that *read* these formats:
vgmstream (decode-only playback of hundreds of game audio formats, with player plug-ins) [S46] and wwiser (bnnm; a
Wwise `.bnk` parser that dumps the event and container hierarchy and writes playlists that let vgmstream play the music
as the game would; it states its knowledge came from studying public SDKs, executables and files) [S47]. Reading a
bank's structure shows the authored logic (which events exist, which switch containers, which transitions) that
observation can only infer.

The boundary, plainly: do this only on a game you own, privately, for understanding; never redistribute extracted
audio; obey an enforceable EULA; and **if a bank or package is encrypted, stop** and record "encrypted, not analysed".
Finding or using keys to decrypt protected game content is circumvention under DMCA 1201 (section 10.5), and this
arsenal does not teach it. Prefer routes 1 and 2; they answer most design questions without touching the files.

**Evidence it yields:** route 1, behaviour (what you hear when); route 2, the actual authored structure of a published
project; route 3, a game's structure, at legal and safety cost.
**Cannot tell you:** route 1 cannot see parameter values or rules that never fired during your play; event names in
any route are hints, not behaviour (REA rule).

**Legal note.** Game *mechanics and rules* are ideas and not protected by copyright (17 U.S.C. 102(b) [S67]); the game's
*sounds, music and specific audiovisual expression* are. The Tetris v. Xio decision (D.N.J. 2012) is the standing
warning that copying a game's specific look and feel is infringement even when the rules are free [S66]. EULAs that
forbid reverse engineering can be enforced in the US (Davidson & Associates v. Jung, 8th Cir. 2005, not re-read for
this report). DMCA 1201 forbids circumventing access controls regardless of copying. Not legal advice.

**Host safety.** Game files are untrusted input, and vgmstream and wwiser are parsers of untrusted binary formats:
work in a disposable VM or sandbox, never execute anything from the game folder outside the game itself, keep
extracted material out of the repo, and delete it when the study is done.

### 4.6 Reverse-engineering a file's history (forensics-lite)

**Use when:** "Is this really lossless?", "Was this upsampled?", "Has this been normalised or limited?"

- **Lossy history:** a flat spectrum that drops off a cliff below 22 kHz (E5: 16.7 kHz for 128 kb/s stereo MP3 from
  our ffmpeg build; 17.3 kHz for 128 kb/s AAC; about 20 kHz for Opus, which also always decodes at 48 kHz). Encoders
  differ; it is a fingerprint, not proof, and a mono file at the same bitrate keeps more bandwidth (each channel gets
  more bits; our first run measured a 128 kb/s mono MP3 out to 20.2 kHz).
- **Upsampling:** nothing at all above half of a lower original rate (for example above 11.025 kHz or 22.05 kHz in a
  96 kHz file).
- **Fake bit depth:** a "24-bit" file whose lowest 8 bits are always zero was 16-bit.
- **Limiting and clipping:** the sample-value histogram (section 4.3).
- **Edits:** discontinuities in the noise floor or the reverb tail, sudden phase jumps at a sample.

Tools: our Welch-spectrum check (Appendix A, demo C), Spek or Sonic Visualiser for a picture, `arsenal.media probe`.
The legal and safety notes of 4.3 apply.

---

## 5. Tools catalogue

"Here" means available on this machine on 2026-10-13 (E9). "No" means not installed; installing anything into the
pinned house Python is Daniel's call (the house reserves a separate Python 3.12 venv for ROCm audio work; note that
Basic Pitch supports Python only up to 3.11 [S30]). No GPU was used or needed for anything below.

| Tool | What it is for | Licence / cost | Here? |
|---|---|---|---|
| `arsenal.media` (`probe`, `audio`, `qc`, `peaks`, `avsync`, `words`) | House door: track inventory, LUFS/LRA/TP, silences, demux, waveform peaks, audio-to-event sync | House code | Yes |
| `arsenal.practice`, `arsenal.pianocue voicing`, `arsenal.replay_harmony`, `arsenal.practice_riff` | House harmony engine over MIDI practice logs: chord windows, keys, cadences, voicings, riffs over jam loops | House code | Yes |
| ffmpeg (house build N-124319) | Decode/encode, `ebur128`, `astats`, `showspectrumpic`, `silencedetect` | LGPL/GPL | Yes |
| librosa 0.10.2 | STFT, CQT, chroma, pYIN, onsets, beats, RMS | ISC [S3] | Yes |
| numpy / scipy / soundfile / scikit-learn | The maths, filters, Welch spectra, file I/O, clustering | BSD-family | Yes |
| torch 2.4.1 (CPU build) | Needed by Demucs and most separators/transcribers | BSD | Yes |
| Sonic Visualiser 5.2.1 (+ Vamp plug-ins: NNLS Chroma, Chordino, pYIN, Tony) | Looking, layering and annotating; chords; melody transcription | Free, open source [S4][S34] | No |
| REW (Room EQ Wizard) | Sweeps, IRs, RT60, waterfalls | Free; Pro upgrade optional [S18] | No |
| sms-tools | Sinusoidal, harmonic and harmonic-plus-stochastic analysis/resynthesis, teaching | AGPL-3.0 [S5] | No |
| DDSP | Differentiable synthesis: f0 + loudness + harmonic distribution + filtered noise | Apache-2.0 (Magenta) [S6] | No |
| DawDreamer | Python-driven plug-in host for render-and-compare parameter searches | GPL-3.0 [S11] | No |
| Synplant 2 (Genopatch) | Commercial sample-to-patch matching, local CPU | About USD 149 [S12] | No |
| Harmor (FL Studio) | Additive resynthesis of an imported sample; image synthesis | Commercial, Image-Line [S13] | Daniel's FL install (edition not checked) |
| FL Studio stem separation | Vocals/music/bass/drums inside the DAW | Producer Edition and above [S25] | Daniel's FL install (not checked) |
| sfxr / jsfxr / Bfxr | Parametric retro game sound effects | MIT (sfxr) [S14] | No (jsfxr runs in a browser) |
| Neural Amp Modeler | Learn an amp or pedal from input/output recordings | MIT [S19] | No |
| Demucs (htdemucs, htdemucs_ft, htdemucs_6s) | Stem separation | MIT code [S20] | No |
| python-audio-separator (UVR models incl. BS-RoFormer, Mel-RoFormer, MDX) | Stem separation, many models, CPU option | MIT code; credit UVR [S22] | No |
| Open-Unmix | Reference separator | MIT code; `umxl` weights CC BY-NC-SA [S23] | No |
| Matchering | Reference-based matching of RMS, EQ, peak, width | GPL-3.0 [S29] | No |
| pyloudnorm | Independent BS.1770-4 loudness meter | MIT [S27] | No |
| CREPE / pYIN | Monophonic pitch tracking | MIT [S15] / in librosa [S3] | pYIN yes |
| Basic Pitch | Polyphonic instrument-agnostic audio-to-MIDI | Apache-2.0 [S30] | No |
| Kong piano transcription | Piano notes + sustain pedal | Apache-2.0 [S31] | No |
| Transkun | Piano transcription | MIT [S32] | No |
| MT3 | Multi-instrument transcription (Colab) | Apache-2.0 [S33] | No |
| madmom | Beats, downbeats, onsets, chords, key, piano | BSD code, CC BY-NC-SA models [S35] | No |
| Essentia | Large MIR toolbox | AGPL-3.0 (commercial licence on request); models CC BY-NC-ND [S36] | No |
| mir_eval | Scoring transcription, chords, beats, separation | MIT [S37] | No |
| FMOD Studio | Game audio middleware and authoring | Free for indies under thresholds announced Dec 2020 (revenue under USD 200k a year and budget under USD 500k) [S39]; current terms on fmod.com (page did not render for us) | No |
| Wwise | Game audio middleware and authoring | Free Indie licence for budgets under USD 250k, no asset limit (Audiokinetic blog, via search; pricing page refused the fetcher) [S40] | No |
| vgmstream, wwiser | Read and play game audio formats; parse Wwise banks | Community projects (licences in their repos) [S46][S47] | No; VM only |

---

## 6. Where the house already stands

- **Strong:** loudness and multitrack handling (`arsenal.media`), audio-to-event sync (`avsync`, which measured that on
  the practice log every key sounds twice, the keyboard on the mic and the synth on desktop audio, 70-95 ms apart),
  speech-to-text (`words`), and a deep harmony engine over MIDI (`arsenal.practice`).
- **Missing:** a spectrogram/spectrum verb, a partials-and-envelope profiler, IR measurement, stem separation,
  audio-to-MIDI, chords-from-audio, a sound-matching harness, and a game-audio observation kit. Section 15 lists them as
  gaps with a proposed shape each.

---

## 7. Worked examples (closed loop, synthetic material we made)

All five demos used sound generated by our own script (Appendix A), so the "answer" is known and every number below is
recovered-versus-true. Run on 2026-10-13 with numpy 2.4.4, scipy 1.17.1, librosa 0.10.2, the house ffmpeg build
N-124319 (2026-05-03), CPU only; total run time under 4 s per pass. Results files and audio stayed in the session
scratchpad; nothing was written into the repo except this report.

Evidence IDs used in this report:

| ID | What |
|---|---|
| E1 | Demo A, version 1 (fixed 512-sample envelope frame) |
| E2 | Demo A, version 2 (pitch-synchronous envelope frame, robust note-off) |
| E3 | Demo B, IR by sweep, 6 s sweep with mild symmetric distortion |
| E4 | Demo B follow-up: sweep length and distortion varied to test the RT60 bias |
| E5 | Demo C, codec cutoff fingerprints (stereo noise) |
| E6 | Demo D, chords from audio, mellow piano-like tones |
| E7 | Demo D, chords from audio, bright tones with a heavy bass |
| E8 | Demo E, the house loudness door on the demo-A note |
| E9 | Environment census: installed Python packages, `arsenal.media` verb list |

### 7.1 A synth patch, recovered blind (E1, E2)

**Target recipe (hidden from the analysis):** a band-limited sawtooth at 220 Hz, through a 2-pole Butterworth
low-pass at 1,200 Hz, with an amplitude envelope: 20 ms linear attack, exponential decay with τ = 100 ms to a sustain
of 0.40, note-off at 1.2 s, exponential release with τ = 120 ms. 48 kHz.

**Analysis (audio only):** pYIN for f0; harmonic levels at k × f0 (k = 1..40) on a 0.45 s Hann window in the sustain;
a grid fit of "1/k source × Butterworth magnitude" over cutoff (200-8,000 Hz in 10 Hz steps) and order (1-4);
RMS envelope fits; resynthesis; multi-resolution STFT log-magnitude distance (windows 256, 1,024, 4,096).

| Parameter | True | Recovered, v1 (E1) | Recovered, v2 (E2) |
|---|---|---|---|
| f0 | 220.0 Hz | 220.64 Hz | 220.64 Hz (+5 cents) |
| Filter cutoff | 1,200 Hz | 1,120 Hz | 1,120 Hz (-6.7 %) |
| Filter order | 2 | 2 | 2 (correct; fit residual 0.6 dB RMS) |
| Attack | 20 ms | 23.3 ms | 23.3 ms |
| Decay τ | 100 ms | 155.7 ms (+56 %) | 99.9 ms |
| Sustain | 0.40 | 0.395 | 0.421 |
| Note-off | 1.200 s | 1.003 s (197 ms early) | 1.204 s |
| Release τ | 120 ms | 135 ms | 120 ms |
| Distance to target (lower is closer) | 0 | 0.853 | 0.838 |
| Distance of a naive guess (right pitch, no filter, default envelope) | | 4.98 | 4.98 |

**Observations.** The harmonic table had every integer harmonic, even ones only 3.6 dB under odd ones over the first
ten, consistent with a sawtooth-family source (a square would have shown even harmonics tens of dB down). The extra
roll-off fitted a 2-pole low-pass. Version 1 measured the envelope with a fixed 512-sample frame, which is not a whole
number of the 218-sample period: the RMS rippled on the sustain plateau, the note-off detector fired on a ripple
197 ms early, and the decay fit was dragged out by the ripple floor. Version 2 used a 4-period frame and required
20 ms below 90 % of the plateau before calling a note-off; the envelope came back almost exactly.

**Inferences.** (1) The method recovers the source family, filter order and envelope well on this class of sound; the
cutoff is biased about 7 % low (likely from the small f0 overestimate compounding at high harmonics, plus window
leakage; not tested further). (2) **The distance number hardly noticed a 56 % decay error** (0.853 versus 0.838), so a
low distance does not certify every parameter. Envelope parameters need their own check.

**Unknowns.** How this degrades with noise, reverb, a resonant filter, a filter envelope, or a real synth's
non-ideal oscillators. A real-synth test is the next step (section 15, gap 7).

### 7.2 An impulse response by exponential sweep (E3, E4)

**Target:** a synthetic "room": a direct sound, one reflection at 7 ms (half amplitude), and a diffuse tail of
decaying noise with RT60 = 0.6 s; driven through a mildly saturating "speaker" (a symmetric soft clip, which adds odd
harmonics only); noise at -70 dB. Sweep 20 Hz-20 kHz over 6 s.

**Results (E3):**

- Early reflection found at 7.0 ms (true 7.0 ms).
- Recovered IR versus true IR, correlation 0.91 over the first 300 ms.
- RT60 by T20: **0.661 s** (true 0.6 s). The same meter on the true IR read 0.603 s, so the meter was fine and the
  10 % error came from the measurement.
- Harmonic distortion: the 3rd-harmonic response sat 19.2 dB below the linear one, exactly where theory puts it
  (0.9542 s ahead of the linear IR, predicted 0.9542 s). The 2nd-harmonic window held energy 35 dB down, little, as
  expected from a symmetric clipper; we did not attribute that residue (tails of other orders, or aliasing in our
  digital simulation).

**Follow-up test of the bias (E4):**

| Sweep length | Distortion | RT60 by T20 |
|---|---|---|
| 6 s | none | 0.602 s |
| 6 s | mild | 0.661 s |
| 15 s | mild | 0.636 s |
| 20 s | mild | 0.621 s |

**Inference.** The bias comes from the distortion: the harmonic responses and their room tails land in or near the
linear IR's window when the sweep is short, adding late energy and slowing the apparent decay. Longer sweeps push them
away and shrink the bias; lower drive removes it. A residual 3 % at 20 s remains unexplained; our leading suspect is
aliasing of the digitally simulated distortion, a feature of the simulation rather than of real speakers (bounded
unknown, not tested). **Practical rule:** low drive, long sweeps (L · ln 2 longer than the room's decay), and score the
meter on a known IR.

### 7.3 Codec fingerprints (E5)

**Target:** 8 s of stereo white noise at 44.1 kHz, encoded by the house ffmpeg build and decoded again. Level by band,
relative to the 1-5 kHz median:

| Encoding | 16 kHz | 17 kHz | 18 kHz | 19 kHz | 20 kHz | 21 kHz | Cutoff at -30 dB |
|---|---|---|---|---|---|---|---|
| Original WAV | flat | flat | flat | flat | flat | flat | 22.05 kHz |
| MP3 128 kb/s (libmp3lame) | -0.2 | -61.7 | -81 | -81 | -81 | -81 | 16.7 kHz |
| MP3 192 kb/s | +0.3 | +0.3 | +0.1 | -56.9 | -81 | -81 | 18.8 kHz |
| MP3 320 kb/s | -0.1 | +0.1 | -0.1 | -0.1 | -4.3 | -81 | 20.2 kHz |
| AAC 96 kb/s (ffmpeg aac) | -35.9 | -71.8 | -81 | -81 | -82 | -81 | 15.9 kHz |
| AAC 128 kb/s | +0.9 | +1.2 | -79.9 | -81 | -81 | -81 | 17.3 kHz |
| Opus 96 kb/s (libopus) | +2.7 | +2.5 | +2.2 | +2.0 | -0.1 | -60.9 | 20.4 kHz (decodes at 48 kHz) |

**Observation.** Each lossy encoder leaves a brick wall whose height tracks bitrate. **Inference.** A "lossless" file
with a wall at 16-17 kHz has almost certainly been through a low-bitrate lossy encoder. **Boundary.** These walls
belong to these encoders and this build; other encoders (Apple's AAC, Fraunhofer MP3) place them differently, and a
mono file at the same bitrate keeps more bandwidth (our mono first pass showed MP3 128 kb/s reaching 20.2 kHz).

### 7.4 Chords from audio, and the bass-harmonic trap (E6, E7)

**Target:** I-V-vi-IV in C (C, G, Am, F), two seconds each, a bass note in octave 2 under a close voicing, rendered
with piano-like tones (15 partials with stiff-string inharmonicity B = 0.0004). Analysis: librosa CQT chroma averaged
per chord, cosine similarity against the 24 major and minor triad templates.

| Chord | Mellow tones (E6): detected, score, runner-up | Bright tones, heavy bass (E7): detected, score, runner-up | Strongest non-chord pitch classes in E7 |
|---|---|---|---|
| C | C 0.881, Cm 0.733 | C 0.805, Cm 0.718 | Bb 0.10, D 0.09 |
| G | G 0.891, Em 0.712 | G 0.828, Gm 0.702 | F 0.10, F# 0.09 |
| Am | Am 0.897, F 0.724 | **Am 0.800, A 0.770** | **C# 0.16**, G 0.11 |
| F | F 0.913, Dm 0.712 | F 0.842, Fm 0.708 | Eb 0.10, E 0.09 |

**Observations.** All eight were named correctly. In the bright, bass-heavy version the leaked pitch classes are
exactly the bass note's 7th harmonic (Bb over C, F over G, Eb over F) and, for A minor, the bass A's 5th harmonic, C#,
which is the *major* third: A minor beat A major by only 0.03.

**Inference.** On real pianos (brighter, pedalled, with sympathetic resonance) chroma-template chord naming will
confuse major and minor over a strong bass. That is the reason Chordino's NNLS front end exists [S34], and the reason
the house names chords from MIDI whenever it has MIDI.

### 7.5 The house loudness door (E8)

`arsenal.media.audio.loudness` on the demo-A note (2 s, mono, peak normalised to 0.5, that is -6.02 dBFS) returned
I = -19.3 LUFS, LRA = 0.0 LU, TP = -6.0 dBTP. The true peak agrees with the sample peak, as it should for a smooth
220 Hz tone. The door wrote its receipt into a scratch state directory (we set `ARSENAL_MEDIA_STATE`), not the repo.

### 7.6 Proposed examples on our own material (not run; Daniel picks)

These are the natural next worked examples. Per the REA rule, no session, project or room is chosen here on Daniel's
behalf.

1. **Calibrate audio transcription against the practice log.** Pick one session (Daniel's choice) that has both the
   MIDI log and an OBS recording with the Piano track. Align with `py -m arsenal.media avsync` (watch for the two
   correlation lobes about 93 ms apart that the `arsenal.media` README names as an open ruling [S16]), transcribe the audio with Basic
   Pitch or a piano model, and score onsets, offsets and pedal with mir_eval against the MIDI. This gives the house an
   honest error profile for audio-only transcription on Daniel's own instrument and room. All outputs under `state/`.
   Note that the desktop-audio piano is the piano page's own synth voice, whose loudness curve the house already
   documents (`replay_harmony.py`: peak = level × (0.06 + 0.94 × (velocity/127)^1.6)), so it is a *known* synth too.
2. **Resynthesise one of Daniel's own FL Studio sounds** with a different synth (for example Harmor's resynthesis, or
   our numpy synth), score it with the distance from 7.1, and listen. His own render is the target; his own project is
   the ground truth for the parameters.
3. **Measure his room** with REW or our sweep script, at low level, with his own interface and microphone.
4. **Study the Celeste FMOD project** in FMOD Studio for one adaptive-music question (for example, how a chapter's music
   moves between sections) and write it up as authored structure, credited to its authors.

---

## 8. Mistakes that waste time

1. **Measuring an envelope with a frame that beats against the pitch period.** Ripple masquerades as decay and
   triggers false note-offs (E1: note-off 197 ms early, decay +56 %). Use a whole number of periods or smooth the
   envelope, and report the frame length.
2. **Trusting a low spectral distance as proof of the parameters.** E1 and E2 differ by a 56 % decay error and 0.015
   in distance. Check envelopes and pitch separately.
3. **Skipping the closed-loop test.** Every pipeline here had a bias that only a known target exposed (the cutoff 7 %
   low, RT60 10 % high).
4. **Driving a sweep too hard, or too short.** Distortion responses overlap the linear IR and inflate RT60 (E4).
5. **Using two clocks** (playing from one device, recording on another). The sweep smears; the IR is garbage.
6. **Treating separated stems as multitracks.** Measuring a stem's EQ measures the separator. Listening to stems is
   the use; measuring them needs a caveat.
7. **Matching EQ against a reference with a different arrangement.** A song without a bass guitar "needs" a bass cut
   that your song does not.
8. **Naming major or minor from chroma over a strong bass** (E7). Check the bass's 5th harmonic; prefer notes.
9. **Expecting chroma to show voicing.** It folds octaves away. Voicing needs notes.
10. **Assuming "lossless" files are lossless.** Check the spectrum before using a file as a reference (E5).
11. **Comparing loudness by peak level or by ear.** Use LUFS and true peak; match loudness before judging tone (louder
    sounds "better" by default).
12. **Reading a game's or a preset's names as behaviour.** `Music_Combat_High` may never fire. Observe it.
13. **Installing an ML model without reading the weights' licence.** Code MIT, weights non-commercial is common.
14. **Analysing a commercial game's files before observing it.** Most design questions are answered by playing with
    the volume sliders and a recorder, at no legal or safety cost.
15. **Letting third-party audio into the repo** (or Daniel's private recordings out of `state/`).

---

## 9. Ideas for the future Archero-style game (design notes, not decisions)

Daniel's goal is a game with a viable upgrade path and free releases of new weapons and effects. Audio implications,
as options for him to choose among (none chosen here):

- **Weapons as data, sounds as data.** If each weapon's sound is a *preset of a parametric generator* (sfxr-style
  [S14], or a small layered synth) plus a few short samples, then a free weapon release can ship a new sound as a few
  bytes of parameters, and stays stylistically consistent. Middleware supports the same idea with parameterised events
  (FMOD parameters, Wwise RTPCs and switches).
- **A per-weapon sound kit:** fire or launch, travel loop, impact, critical hit, kill confirm, plus shared pickup,
  level-up, hurt and low-health sounds. Each gets a priority, a maximum number of simultaneous instances, a variation
  rule and a loudness target. The Overwatch importance buckets [S44] are a good model for "crits and hurt sounds must
  cut through arrow spam".
- **Adaptive music options:** room loops with intensity layers (vertical), a horizontal switch for boss rooms, a
  filtered or ducked mix during the upgrade-choice screen, a low-health snapshot.
- **Release QC:** every new weapon's sounds pass a loudness check per category (`arsenal.media qc` already reads LUFS
  and true peak) so a new release is never jarringly loud.
- **Middleware choice** (FMOD, Wwise, an engine's built-in mixer, or Web Audio for a browser build) is Daniel's
  decision; both FMOD and Wwise have free indie tiers (section 5), each with conditions to read in full.
- **Legal:** the Archero-style *mechanics* (auto-fire while standing, dodge by moving, choose an ability on level-up)
  are ideas; the original game's sounds, music, art and specific screen layouts are not ours to copy, even as
  placeholders in a public build. App stores also police copycats (Apple's App Review Guidelines have a section on
  them). Not legal advice.

---

## 10. Legal notes (not legal advice; dated 2026-10-13)

This section maps where the lines are so that the house knows when to stop and ask a lawyer. Laws differ by country,
change over time, and depend on facts. Nothing here is advice for a specific situation.

### 10.1 Two copyrights in every song

A recorded song carries (1) the **musical work** (composition: melody, harmony as written, lyrics), usually owned by a
songwriter and publisher, and (2) the **sound recording** (the actual fixed sounds), usually owned by a label or the
artist. Using a recording needs both licences; re-recording a song needs the composition's licence (in the US a
compulsory mechanical licence is available for covers of released songs). Newton v. Diamond (9th Cir. 2004) shows the
split: the Beastie Boys had licensed the recording of a flute sample; the court held that their use of three notes of
the underlying composition was de minimis and needed no composition licence [S68].

### 10.2 Sampling

- **United States.** The Sixth Circuit in Bridgeport Music v. Dimension Films (2005) rejected a de minimis defence for
  sound recordings: "Get a license or do not sample." [S51] The Ninth Circuit disagreed in VMG Salsoul v. Ciccone
  (2016), applying de minimis to a 0.23-second horn hit in "Vogue" [S52]. The circuit split is unresolved; in practice
  the industry clears samples.
- **European Union.** The Court of Justice in Pelham (C-476/17, 29 July 2019) held that taking even a very short
  sample from a phonogram is a reproduction "in part" if it is recognisable to the ear; a sample modified until
  unrecognisable does not infringe the phonogram producer's right [S53]. In Pelham II (C-590/23, judgment 14 April
  2026) the Grand Chamber defined the "pastiche" exception for the first time: roughly, a creation that evokes an
  existing work, is noticeably different from it, and is recognisable as engaging with it, judged objectively rather
  than by the user's intent. Whether the Kraftwerk sample itself qualifies is left to the German court [S54]. We read
  Pelham II through two secondary summaries that phrase the test slightly differently; read the judgment itself before
  relying on it.
- **Practical rule for the house:** we do not sample recordings we do not own or hold a licence for. We re-make sounds
  instead (10.3), or use our own recordings, public-domain recordings (10.7), or sounds licensed for the use (Freesound
  sounds carry CC0, CC BY, CC BY-NC or the retiring Sampling+ licence; only CC0 and CC BY suit a commercial game, CC BY
  with credit [S48]).

### 10.3 Re-making a sound; imitating a voice

- 17 U.S.C. 114(b): the recording owner's rights do not extend to an independent recording of other sounds, even
  sounds that imitate or simulate the original [S50]. So resynthesising a timbre from scratch, or re-playing a part,
  does not copy the *recording*. It may still copy the *composition* if the notes are the song's.
- **Voices are different.** Imitating a famous singer's distinctive voice for commercial use was held actionable under
  California law in Midler v. Ford (9th Cir. 1988) [S57] and Waits v. Frito-Lay (9th Cir. 1992) [S58]. Tennessee's
  Ensuring Likeness, Voice, and Image Security Act (Public Chapter 588, effective 1 July 2024) adds voice, including
  simulated voice, to the right of publicity and also reaches tools whose primary purpose is producing a particular
  person's voice without authorisation [S59]. The house does not clone or imitate identifiable people's voices.

### 10.4 Musical similarity: what is free to use

Ideas, styles, genres and commonplace building blocks are free. Recent appellate decisions keep confirming that:
Skidmore v. Led Zeppelin (9th Cir. en banc 2020) abolished the "inverse ratio" rule and confined a 1909-Act song's
protection to its deposit copy [S69]; Gray v. Hudson (9th Cir. 2022) held a common eight-note ostinato unprotectable
[S56]; Structured Asset Sales v. Sheeran (2d Cir. 2024) held a common chord progression with its harmonic rhythm
unprotectable [S55]. But Williams v. Gaye (9th Cir. 2018, "Blurred Lines"; not re-read here) is the reminder that a
jury can find infringement in a strongly evocative pastiche. Learning harmony and voicing from recordings is fine;
re-using a specific melody or a distinctive combination is not.

### 10.5 Anti-circumvention (DMCA 1201) and contracts

- 17 U.S.C. 1201 forbids circumventing a technological measure that controls access to a copyrighted work, and
  trafficking in tools to do so, *independently* of whether any copying follows [S62]. For audio this covers streaming
  DRM and encrypted game banks. The house never circumvents; "encrypted, not analysed" is a valid finding.
- Exemptions are narrow and temporary. The 2024 rulemaking (effective 28 October 2024, for three years) renewed
  exemptions including good-faith security research on computer programs and preservation and continued play of video
  games whose server support has ended [S61]. None of them covers ripping music or game audio for reuse. Section
  1201(f) has a statutory interoperability exception for software, not for media.
- **Contracts:** streaming services' terms forbid ripping. A game's EULA may forbid reverse engineering; US courts have
  enforced such clauses (Davidson & Associates v. Jung, 8th Cir. 2005; not re-read for this report). In the EU,
  Article 8 of the Software Directive voids contract terms that override the decompilation and observe-study-test
  rights (2009/24/EC, arts. 5(3), 6 and 8 [S65]); those rights concern *programs*, not the game's audio assets.

### 10.6 Software reverse engineering versus assets

US fair-use cases protect intermediate copying of *code* done to reach unprotected functional elements and
interoperability: Sega v. Accolade (9th Cir. 1992) [S63] and Sony v. Connectix (9th Cir. 2000) [S64]. The EU Software
Directive allows observing, studying and testing a program one is entitled to run (art. 5(3)) and decompiling it where
indispensable for interoperability of an independently created program (art. 6) [S65]. Neither line of authority
licenses copying a game's **sounds, music or art**: those are ordinary copyrighted works. Trade-secret law treats
reverse engineering of a lawfully obtained product as a proper means (US Defend Trade Secrets Act, 18 U.S.C. 1839(6)
[S70]; EU Trade Secrets Directive 2016/943 art. 3, not re-read here), but that does not cancel copyright, contract or
1201. Game rules and mechanics are not copyrightable (17 U.S.C. 102(b) [S67]); specific look and feel can be (Tetris
Holding v. Xio Interactive, D.N.J. 2012, protecting the board dimensions, block colours, piece shadow and next-piece
display while leaving the mechanics free [S66]).
[Corrected 2026-10-13 after review: "game rules are not copyrightable" is too broad. The US Copyright Office's games
page (copyright.gov/register/tx-games.html) says a game's method of play is not protected, but the text of its rules
can be registered. The method of play is free; the rule text is protectable. The corrected text is in the skill's
`method-legal-cleanroom.md`.]

### 10.7 Public-domain recordings (US)

Under the Music Modernization Act's Classics Protection and Access Act, US sound recordings published before 1923
entered the public domain on 1 January 2022; recordings published 1923-1946 enter it 100 years after publication (so
1925 recordings entered on 1 January 2026); 1947-1956 recordings get 110 years; 1957 to 15 February 1972 recordings
are protected until 2067 [S60]. The underlying compositions have their own terms, and other countries differ.

### 10.8 Datasets, models and middleware licences

MUSDB18 is for academic use only [S24]. Model weights often carry non-commercial licences separate from MIT or BSD
code (umxl, madmom, Essentia) [S23][S35][S36]. Demucs's README states an MIT licence for the code and does not state a
separate licence for its pretrained weights [S20]: treat their commercial use as unverified. FMOD and Wwise indie
tiers have revenue and budget conditions that must be re-read at the time of use [S39][S40]. Published learning
projects (Celeste's FMOD project) come with their own terms in the download [S42].

---

## 11. Host safety

This machine runs with Windows Defender off and updates blocked, by the owner's choice. So, for every playbook that
touches files we did not make:

- **Analyse untrusted audio, game files, plug-ins and project files inside a disposable VM or sandbox.** Media
  decoders and format parsers (ffmpeg, vgmstream, wwiser, plug-in loaders) are C code reading attacker-controllable
  bytes; a crafted file is a real attack path.
- **Never execute untrusted code on the host**: no unknown plug-ins (VST/CLAP), no executables or scripts bundled with
  sample packs, mods or game folders, no "cracked" tools.
- **Keep samples out of the repo.** Third-party audio, extracted game assets, captured IRs of commercial products and
  downloaded datasets live outside `E:\AI-Setup` (or at most under git-ignored scratch), and are deleted when a study
  ends. Daniel's own recordings and practice data stay under `state/` and never enter tracked files (the
  `story_corpus` and `performance` modules already state this rule).
- Model downloads (separation and transcription weights) come only from the projects' official sources.

---

## 12. Finding ledger and checklist revisited

| # | Question from the brief | Status | Evidence | Confidence and boundary | Remaining unknowns |
|---|---|---|---|---|---|
| 1 | Spectrograms: how to read and set them | Answered | 2.2, [S2], E1-E7 | High; standard theory | none material |
| 2 | Envelopes | Answered, with a measured pitfall | E1, E2 | High on synthetic tones | Behaviour with noise, reverb, polyphony |
| 3 | Partials and synthesis fingerprints | Answered | 2.5, [S7], E2 | High as observations; product identity stays unknown | |
| 4 | Resynthesis to recover synth parameters | Partly answered | E2, [S8][S9][S10][S12] | Closed loop on our own numpy synth only | No real synth tested (gap 7) |
| 5 | Convolution and impulse responses | Answered, with a measured bias | E3, E4, [S17] | High; synthetic room | 3 % residual bias at 20 s (aliasing suspected, untested) |
| 6 | Stem separation | Answered from sources; not run | [S20]-[S24] | Medium; vendor numbers are averages | Our own SDR on our material (needs install) |
| 7 | Loudness | Answered and run | E8, [S26][S28] | High; house meter verified by its own tests | |
| 8 | EQ matching | Answered from sources; not run | [S29] | Medium | |
| 9 | Transcription | Answered from sources; not run | [S30]-[S33][S37] | Medium | Error profile on Daniel's piano (7.6 example 1) |
| 10 | Harmony and voicing | Answered; demo run; house tools mapped | E6, E7, house modules | High for MIDI path; medium for audio path | |
| 11 | Middleware concepts (FMOD, Wwise) | Answered at concept level | [S38]-[S41] | Medium: FMOD docs did not render, Wwise pricing and docs refused the fetcher; terms from course notes and Audiokinetic blog summaries | Current licence terms (re-read at use) |
| 12 | Adaptive music | Answered | [S41][S43], Hades (secondary) | Medium-high | |
| 13 | How game sounds signal feedback | Answered | [S44][S45] plus labelled inferences | Medium-high | |
| 14 | Copyright boundary on samples and recordings | Answered | [S50]-[S60][S68][S69] | Dated 2026-10-13; Pelham II via secondary sources | Not legal advice |
| 15 | Shared legal set (1201, Sega, Connectix, EU arts. 5-6, EULAs, trade secrets, mechanics vs assets, Tetris) | Answered at summary level | [S61]-[S67][S70] | Davidson v. Jung and EU TSD not re-read | |
| 16 | Routing table, lessons, gaps | Delivered | sections 13-15 | | |

**Process note.** The session's shared web-search budget ran out (200 calls) near the end of this research; the
remaining verifications used direct page fetches. Items marked "not re-read" were not re-verified for this report.

---

## 13. (a) Routing table: audio and music

| Artifact or question | First tool | Evidence it yields | What it cannot tell you |
|---|---|---|---|
| An unknown audio file: what is it, what happened to it? | `py -m arsenal.media probe` then `audio` (loudness) | Container, codec, rate, tracks, duration, LUFS/LRA/TP | Where it came from; its encoding history (next row) |
| "Is this really lossless / high-res?" | Long-term spectrum (Welch) or a spectrogram (Sonic Visualiser, Spek) | Brick-wall cutoff, empty bands, bit-depth use (E5) | Which encoder exactly; a fingerprint, not proof |
| A single synth or instrument note: how was it made? | pYIN + harmonic table + RMS envelope (librosa; Appendix A) | f0, harmonic pattern, filter shape, ADSR, noise share (E2) | The product, preset or routing; uniqueness of the recipe |
| "Give me synth parameters for this sound" | Render-and-compare search on a declared synth (DawDreamer + an open synth, Synplant Genopatch, Harmor resynthesis) | A patch at a stated distance under a stated loss | That it is the original patch (non-identifiable; E1 vs E2) |
| A retro game sound effect | sfxr/jsfxr parameter match by ear or search | A small parameter set that reproduces it | The original tool used |
| A room, speaker or static effect we own | Exponential sweep + deconvolution (REW, or Appendix A) | IR, RT60/EDT, frequency response, reflections, harmonic distortion (E3) | Time-variant or level-dependent behaviour |
| An amp, pedal or saturator we own | Input/output capture + Neural Amp Modeler | A model that imitates it | Behaviour outside the training signal's range |
| Reverb on a finished recording | Spectrogram tail after stops | Approximate decay time, pre-delay (inference) | The true IR (blind problem) |
| A finished mix: what are the parts? | Demucs `htdemucs` or BS-RoFormer via audio-separator, CPU | Estimated stems for listening | The real multitracks; parts' true EQ and levels |
| How loud and how mastered? | `py -m arsenal.media audio` (ebur128) + sample histogram | I, LRA, TP, limiting or clipping signs | The processing chain |
| "Make ours sit like theirs" | LTAS at 1/3-octave, section by section; Matchering | Tonal-balance difference, width, level | Arrangement differences masquerading as EQ |
| A melody (one voice) | pYIN (librosa) or CREPE; Tony for editing | f0 contour, note segments | Polyphony; intended spelling |
| A polyphonic passage | Basic Pitch; piano: Kong (with pedal) or Transkun; ensemble: MT3 | MIDI notes with timing and velocity | Hands, notation, pedal (most models), meter under rubato |
| Chords and key of a recording | Notes first (transcribe, then house chord naming); else Chordino or chroma templates | Chord labels, key areas | Inversions, extensions, major/minor over strong bass (E7) |
| Daniel's own playing | `py -m arsenal.practice`, `py -m arsenal.pianocue voicing` (MIDI truth) | Windows, chord names, keys, cadences, voicings | Tone, touch-to-sound, room (audio-only facts) |
| A game's adaptive music | Own play recorded with music-only via the game's sliders + beat tracking + event log | Which states change the music, layers vs switches, quantised transitions | Authored rules and parameter values; branches never triggered |
| A game's feedback SFX design | Own play, SFX-only; onset clustering, pitch spread, short-term LUFS | Variation count, randomisation, priority and ducking behaviour | Voice-limit settings, intent |
| How professionals author game audio | Celeste FMOD project; official FMOD/Wwise sample projects with the profiler | The actual authored structure | That it generalises beyond that team's choices |
| An owned game's packed audio files | (VM only) vgmstream / wwiser, at understanding level | Structure: events, containers, transitions | Anything encrypted (stop: 1201); reuse rights (none) |
| "Can we use this sample / this voice / this melody?" | Section 10, then a human with legal advice | The map of the lines | An answer for the specific facts |

---

## 14. (b) Lessons the house should keep (trigger-phrased)

1. Use when extracting an amplitude envelope from a pitched sound, before fitting attack, decay or release times:
   make the RMS frame a whole number of pitch periods (or smooth the envelope) and require a sustained drop before
   calling a note-off; a fixed 512-sample frame on a 220 Hz tone put ripple on the plateau that fired the note-off
   197 ms early and inflated decay by 56 % (E1 vs E2). Don't when the sound is unpitched noise; then use a long
   smoothing window and report its length.
2. Use when proposing any analysis pipeline for an unknown sound, room or mix, before trusting its numbers: run it
   first on a synthetic target whose recipe you know and report recovered-versus-true per parameter; every pipeline in
   this report had a bias only the known target exposed. Don't when the measurement is already pinned by a house test
   (for example `arsenal.media` loudness on sines).
3. Use when a resynthesis reaches a low spectral distance, before reporting the recovered parameters as right: check
   envelopes and pitch separately and say "a patch at distance D under loss L on synth S", not "the patch"; a 56 %
   decay error moved the distance by only 0.015 (E1 vs E2), and the best loss depends on the synth (Salimi et al.
   2025). Don't when the goal is only "a usable similar sound", which is fine to claim as such.
4. Use when measuring an impulse response with a sine sweep, before reading RT60: play at low level from the same
   interface that records, make the sweep long enough that L · ln 2 exceeds the room's decay, and score the RT60 meter
   on a known IR; mild distortion with a 6 s sweep inflated RT60 by 10 % (E3, E4). Don't when the device is strongly
   nonlinear or time-variant; capture it with input/output learning (Neural Amp Modeler) instead.
5. Use when a file is offered as lossless or high-resolution, before using it as a reference: check its long-term
   spectrum for a brick wall (house ffmpeg: MP3 128 kb/s at 16.7 kHz, AAC 128 kb/s at 17.3 kHz, Opus near 20 kHz and
   decoded at 48 kHz; E5). Don't when the source is band-limited by nature (old or lo-fi recordings), where a low top
   end proves nothing.
6. Use when naming chords from audio chroma, before calling a chord major or minor: check whether the bass note's 5th
   harmonic lands on the other third (A bass puts C# into A minor; it beat A major by only 0.03 in E7) and prefer
   notes (MIDI or a transcription) over chroma. Don't when MIDI exists; use `arsenal.practice` and the piano page's
   THEORY naming.
7. Use when separating stems from a mix, before measuring any part's EQ, level or arrangement detail: treat stems as
   estimates for listening, expect bleed (Demucs's own README warns the six-stem piano has heavy artefacts), and
   label any measurement taken from a stem as the separator's. Don't when the real multitracks exist (Daniel's own FL
   projects).
8. Use when matching a mix's tonal balance to a reference, before applying a match EQ: compare the same section with
   the same instrumentation, smooth to at least one-third octave, cap the gains, and treat Matchering's result as a
   direction, not a setting. Don't when the arrangements differ; the "EQ difference" is then the arrangement.
9. Use when studying how a game's music or feedback sounds work, before opening any game file: record your own play
   with music-only and SFX-only via the game's own volume sliders, log events, beat-track the transitions, and read a
   published learning project (Celeste's FMOD project) for authored structure. Don't when the question truly needs
   authored values; then follow the legal and VM rules of section 4.5 route 3.
10. Use when a game bank, package or stream turns out to be encrypted or DRM-protected, before any further step: stop,
    record "encrypted, not analysed" as a bounded unknown, and never look for or use keys; circumvention is DMCA 1201
    territory whatever the purpose. Don't when the bank is our own project's build, where we hold the key legitimately.
11. Use when any recording, sample or voice might go into our music or game, before release: assume a recognisable
    fragment needs a licence (Bridgeport, Pelham), re-make sounds instead of sampling (17 U.S.C. 114(b)), never imitate
    an identifiable voice (Midler, Waits, the Tennessee ELVIS Act), and use our own, CC0, CC BY (credited) or verified
    public-domain material. Don't when the material is our own work.
12. Use when about to install an audio ML package (Demucs, Basic Pitch, madmom, Essentia, Open-Unmix), before pip:
    read the model-weights licence separately from the code licence, check the Python version (Basic Pitch stops at
    3.11), and remember the house Python is pinned, so installs are Daniel's call and may belong in a separate venv.
    Don't when the tool is pure Python already present (librosa, scipy).
13. Use when analysing Daniel's piano audio, before running audio transcription: use the practice log's MIDI as ground
    truth, align with `arsenal.media avsync`, remember every key sounds twice (keyboard on the microphone, synth on
    desktop audio, 70-95 ms apart), and keep every output under `state/`. Don't when no MIDI exists for that recording;
    then report transcription confidence without a ground-truth score.
14. Use when designing feedback sounds for the future Archero-style game, before making assets: write the event
    inventory first (fire, travel, impact, crit, kill, pickup, level-up, hurt, low health), give each a priority, an
    instance limit, a variation rule and a loudness target, and plan a per-release loudness QC. Don't when making a
    throwaway jam prototype, where placeholder sounds we made ourselves are fine.

---

## 15. (c) Gaps: where the house needs a new tool or verb

1. **`media spectrum` (spectrogram and long-term spectrum verb).** PNG spectrogram at chosen window lengths, LTAS at
   1/3 or 1/6 octave, the codec-cutoff fingerprint of E5, a sample-value histogram, in the house result shape with a
   receipt and a `blind` list. ffmpeg's `showspectrumpic` covers the picture; the rest is Appendix A.
2. **`audio profile` (partials and envelope profiler).** f0 by pYIN, the harmonic table, even/odd balance,
   inharmonicity B, a filter fit, a pitch-synchronous ADSR fit and noise share: Demo A promoted to a primitive with its
   closed-loop test as the oracle.
3. **`audio ir` (sweep and deconvolution).** Generate an exponential sweep and its inverse, deconvolve a recording,
   report IR, RT60 (T20/T30), EDT, harmonic-distortion orders, and warn when the sweep is too short for the measured
   decay (the E4 rule).
4. **`audio stems` (separation wrapper).** Demucs or BS-RoFormer on CPU with segment control, the model name and its
   weights licence recorded in the receipt, outputs outside the repo. Needs Daniel's approval to install, probably in
   a separate venv.
5. **`audio transcribe` (audio-to-MIDI) with a calibration harness.** Basic Pitch, Transkun or Kong behind one verb,
   plus a scorer (mir_eval) that runs against the practice log's MIDI; the honest error profile becomes the verb's
   `blind` list.
6. **`audio chords` (chords from audio, sharing names with MIDI).** Chroma or NNLS chroma in, then the same chord
   naming as `practice_theory.mjs`, so that audio and MIDI paths speak one vocabulary; with the bass-harmonic check of
   lesson 6.
7. **`audio match` (sound-matching harness).** A render-and-compare loop over a declared synth (our numpy synth first,
   then an open synth through DawDreamer, or Surge XT through its Python binding), a declared loss (multi-resolution
   STFT plus envelope terms), CMA-ES or grid search, and a receipt with the loss curve and per-parameter
   recovered-versus-true when the target is synthetic.
8. **`audio eqmatch` / reference compare.** LTAS difference with smoothing, gain caps and a section selector.
9. **Game-audio observation kit.** A recording protocol (OBS Game track, music-only and SFX-only passes), an event
   logger, onset clustering for round-robin counts, pitch-spread and short-term-LUFS reports per sound class, and a
   music-state timeline with bar alignment.
10. **Sound-kit generator for the future game.** An sfxr-style parametric generator (MIT ancestry) whose presets are
    data, with per-category loudness targets checked by `arsenal.media qc`, so that free weapon releases ship as
    parameters plus QC receipts.
11. **A disposable VM profile for untrusted media and game files.** The house has no standard sandbox recipe for
    running parsers like vgmstream or wwiser on files we did not make; other reports in this set may propose the
    general one, and audio should reuse it.
12. **A licence register for audio models and datasets.** One table, kept current, separating code licence from
    weights licence (umxl, madmom, Essentia, Demucs weights unverified, MUSDB academic-only), consulted by gaps 4 and 5
    before any install.

---

## 16. Sources

Each line: ID, URL, one line on what it is. "Not fetched" marks items cited from knowledge or secondary summaries that
we did not re-read on 2026-10-13.

**Method**
- S1 https://github.com/morluto/rea : the REA skill (morluto/rea), whose discipline this report adopts.
- S2 https://ccrma.stanford.edu/~jos/sasp/ : Julius O. Smith III, *Spectral Audio Signal Processing* (CCRMA, 2011),
  the free primary text on STFT, windows and sinusoidal modelling.

**Analysis and synthesis**
- S3 https://github.com/librosa/librosa : librosa (McFee et al., SciPy 2015), ISC; STFT, CQT, chroma, pYIN.
- S4 https://www.sonicvisualiser.org/ : Sonic Visualiser (C4DM, Queen Mary University of London), free and open
  source; 5.2.1 released 21 March 2025; family includes Tony and Sonic Annotator.
- S5 https://github.com/MTG/sms-tools : sms-tools (Music Technology Group, UPF), AGPL-3.0, nine analysis/synthesis
  models including harmonic-plus-stochastic.
- S6 https://arxiv.org/abs/2001.04643 : Engel, Hantrakul, Gu and Roberts, *DDSP: Differentiable Digital Signal
  Processing* (2020).
- S7 https://ccrma.stanford.edu/sites/default/files/user/jc/fm_synthesis_paper.pdf : John Chowning, *The Synthesis of
  Complex Audio Spectra by Means of Frequency Modulation*, JAES 21(7), 1973.
- S8 https://research.gold.ac.uk/22516/ : Yee-King, Fedden and d'Inverno, *Automatic Programming of VST Sound
  Synthesizers using Deep Networks and Other Techniques*, IEEE TETCI 2018.
- S9 https://arxiv.org/html/2506.22628v1 : Salimi, Hindle and Zaïane, *Evaluating Sound Similarity Metrics for
  Differentiable, Iterative Sound-Matching* (2025).
- S10 https://arxiv.org/html/2603.15905 : Philipp Bogdan, *Instrumental: Automatic Synthesizer Parameter Recovery from
  Audio via Evolutionary Optimization* (March 2026).
- S11 https://github.com/DBraun/DawDreamer : DawDreamer (David Braun), GPL-3.0, Python DAW engine for plug-in rendering
  and automation (ISMIR 2021 late-breaking demo).
- S12 https://rekkerd.org/sonic-charge-releases-synplant-2-with-genopatch-technology/ and
  https://www.synthtopia.com/content/2023/10/04/synplant-2-lets-you-create-synth-patches-from-samples-using-artificial-intelligence/
  : Synplant 2 and Genopatch (Sonic Charge), sample-to-patch on the local CPU.
- S13 https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Harmor.htm : Harmor manual
  (Image-Line), additive resynthesis and image synthesis (feature summary read via search results).
- S14 https://www.drpetter.se/project_sfxr.html and https://sfxr.me/ : sfxr by Tomas Pettersson (DrPetter), MIT,
  Ludum Dare 10 (December 2007); jsfxr browser port.
- S15 https://github.com/marl/crepe : CREPE (Kim, Salamon, Li and Bello, ICASSP 2018), MIT, monophonic pitch.
- S16 `E:\AI-Setup\arsenal\media\README.md`, `arsenal/media/audio.py` and `arsenal/media/avsync.py` docstrings (house
  files, read 2026-10-13): the OBS six-track map, loudness verified on sines, the practice log's two-lobe sync seam.

**Spaces and processors**
- S17 https://www.listeninc.com/simultaneous-measurement-of-impulse-response-and-distortion-with-a-swept-sine-technique/
  : Angelo Farina, AES 110th Convention (February 2000), the exponential-sweep method.
- S18 https://www.roomeqwizard.com/ : REW by John Mulcahy, free acoustic measurement software (IR, RT60, waterfalls).
- S19 https://github.com/sdatkinson/neural-amp-modeler : Neural Amp Modeler (Steven Atkinson), MIT, amp and pedal
  capture by learning.

**Mixes, separation and loudness**
- S20 https://github.com/adefossez/demucs : Demucs v4 (Alexandre Défossez), MIT code; htdemucs_ft 9.00 dB SDR; CPU about
  1.5 × track length; six-stem piano warning; maintained fork, low activity.
- S21 https://arxiv.org/abs/2309.02612 : Lu, Wang, Kong and Hung, *Music Source Separation with Band-Split RoPE
  Transformer* (ICASSP 2024; SDX23 winner; 9.80 dB without extra data).
- S22 https://github.com/nomadkaraoke/python-audio-separator : python-audio-separator (Andrew Beveridge), MIT, UVR model
  wrapper (MDX-Net, VR, Demucs, RoFormer), CPU option.
- S23 https://github.com/sigsep/open-unmix-pytorch : Open-Unmix (Stöter, Uhlich, Liutkus, Mitsufuji), MIT code;
  `umxl` weights CC BY-NC-SA 4.0.
- S24 https://sigsep.github.io/datasets/musdb.html : MUSDB18 and MUSDB18-HQ, 150 tracks, academic use only; museval.
- S25 https://musictech.com/news/gear/fl-studio-21-2-stem-separation-daw/ and
  https://www.image-line.com/fl-studio-news/fl-studio-21-2-whats-new : FL Studio 21.2 stem separation (Producer
  Edition and above; reported Demucs-based and online).
- S26 https://tech.ebu.ch/publications/r128 : EBU R 128 v5.0 (November 2023), -23 LUFS, with Tech 3341 and 3342.
- S27 https://github.com/csteinmetz1/pyloudnorm : pyloudnorm (Christian Steinmetz), MIT, ITU-R BS.1770-4 meter.
- S28 https://support.spotify.com/us/artists/article/loudness-normalization/ : Spotify loudness normalisation (-14
  LUFS default; true-peak advice for masters).
- S29 https://github.com/sergree/matchering : Matchering 2.0 (Sergei Gribov), GPL-3.0, reference matching.

**Transcription and harmony**
- S30 https://github.com/spotify/basic-pitch : Basic Pitch (Spotify Audio Intelligence Lab; Bittner et al., ICASSP
  2022), Apache-2.0, Python 3.7-3.11.
- S31 https://github.com/bytedance/piano_transcription : Kong et al., high-resolution piano transcription with pedals,
  Apache-2.0.
- S32 https://github.com/Yujia-Yan/Transkun : Transkun (Yujia Yan, Frank Cwitkowitz, Zhiyao Duan), MIT, semi-CRF piano
  transcription.
- S33 https://github.com/magenta/mt3 : MT3 multi-instrument transcription (Google Magenta, ICLR 2022), Apache-2.0.
- S34 https://www.isophonics.net/nnls-chroma : NNLS Chroma and Chordino (Matthias Mauch and Chris Cannam), Vamp
  plug-ins; Mauch and Dixon, ISMIR 2010.
- S35 https://github.com/CPJKU/madmom : madmom (CP JKU Linz), BSD code, CC BY-NC-SA 4.0 model files.
- S36 https://essentia.upf.edu/licensing_information.html : Essentia, AGPL-3.0 or commercial; models CC BY-NC-ND 4.0.
- S37 https://github.com/craffel/mir_eval : mir_eval (Raffel et al., ISMIR 2014), MIT, MIR scoring.

**Game audio**
- S38 https://www.fmod.com/docs/2.03/studio/ and https://limulo.github.io/game-sound-sae2017/fmod.html : FMOD Studio
  documentation (renders in a browser only; not readable by our fetcher) and course notes quoting its logic-track
  terms.
- S39 https://www.gamedeveloper.com/audio/small-developers-and-creators-can-now-use-fmod-studio-for-free : FMOD Studio
  free for small developers (3 December 2020; revenue and budget conditions).
- S40 https://www.audiokinetic.com/en/community/blog/free-wwise-indie-license/ : Wwise free Indie licence (budget under
  USD 250k; read via search summary, the pricing page refused our fetcher).
- S41 https://www.audiokinetic.com/en/community/blog/about-dynamic-music-design-part-1-design-classification/ :
  Audiokinetic blog on classifying dynamic music designs (refused our fetcher; read via search summary).
- S42 https://www.gamedeveloper.com/audio/-i-celeste-s-i-audio-files-are-now-publicly-available-for-devs : Celeste's
  complete FMOD project made public by Power Up Audio, 1 May 2018.
- S43 https://patents.google.com/patent/US5315057A/en : US 5,315,057 (iMUSE), Michael Land and Peter McConnell,
  LucasArts, granted 24 May 1994.
- S44 https://gdcvault.com/play/1023317/Overwatch-The-Elusive-Goal-Play and
  https://awesomegameaudio.wordpress.com/2017/02/06/overwatch-play-by-sound/ : Scott Lawlor and Tomas Neumann, GDC 2016,
  "Overwatch: The Elusive Goal: Play by Sound", with a written summary.
- S45 https://www.gdcvault.com/play/1016487/Juice-It-or-Lose : Martin Jonasson and Petri Purho, "Juice It or Lose It",
  GDC Europe 2012.
- S46 https://github.com/vgmstream/vgmstream : vgmstream, decode-only playback library for game audio formats.
- S47 https://github.com/bnnm/wwiser : wwiser (bnnm), Wwise .bnk parser and TXTP generator.
- S48 https://freesound.org/help/faq/ : Freesound licence types and attribution for commercial use.

**Law**
- S50 https://www.law.cornell.edu/uscode/text/17/114 : 17 U.S.C. 114(b), limits of sound-recording rights
  (independent fixation of imitative sounds).
- S51 https://en.wikipedia.org/wiki/Bridgeport_Music,_Inc._v._Dimension_Films : Bridgeport Music v. Dimension Films,
  410 F.3d 792 (6th Cir. 2005).
- S52 https://en.wikipedia.org/wiki/VMG_Salsoul_v_Ciccone : VMG Salsoul v. Ciccone, 824 F.3d 871 (9th Cir. 2016).
- S53 https://curia.europa.eu/site/upload/docs/application/pdf/2019-07/cp190098en.pdf : CJEU press release, Pelham
  (C-476/17), 29 July 2019.
- S54 https://ipkitten.blogspot.com/2026/04/cjeu-delivers-pastiche-style-judgment.html and
  https://www.ipcuria.eu/case?reference=C-590%2F23 : Pelham II (C-590/23), 14 April 2026, pastiche (secondary
  summaries).
- S55 https://law.justia.com/cases/federal/appellate-courts/ca2/23-905/23-905-2024-11-01.html : Structured Asset
  Sales v. Sheeran (2d Cir., 1 November 2024).
- S56 https://cdn.ca9.uscourts.gov/datastore/opinions/2022/03/10/20-55401.pdf : Gray v. Hudson, 28 F.4th 87 (9th Cir.
  2022).
- S57 https://en.wikipedia.org/wiki/Midler_v._Ford_Motor_Co. : Midler v. Ford Motor Co., 849 F.2d 460 (9th Cir. 1988).
- S58 https://law.justia.com/cases/federal/appellate-courts/F2/978/1093/183202/ : Waits v. Frito-Lay, 978 F.2d 1093
  (9th Cir. 1992).
- S59 https://wapp.capitol.tn.gov/apps/BillInfo/Default.aspx?BillNumber=HB2091&GA=113 : Tennessee HB 2091, Ensuring
  Likeness, Voice, and Image Security Act of 2024 (Public Chapter 588, effective 1 July 2024).
- S60 https://www.congress.gov/crs-product/LSB10181 and
  https://publicdomainreview.org/blog/2021/12/all-sound-recordings-prior-to-1923-will-enter-the-us-public-domain-in-2022
  : the Music Modernization Act's pre-1972 recording terms and public-domain schedule.
- S61 https://www.copyright.gov/1201/2024/ : Ninth Triennial Section 1201 Proceeding (final rule effective 28 October
  2024).
- S62 https://www.law.cornell.edu/uscode/text/17/1201 : 17 U.S.C. 1201, anti-circumvention (not re-read today; text
  well known).
- S63 https://en.wikipedia.org/wiki/Sega_v._Accolade : Sega v. Accolade, 977 F.2d 1510 (9th Cir. 1992).
- S64 https://en.wikipedia.org/wiki/Sony_Computer_Entertainment,_Inc._v._Connectix_Corp. : Sony v. Connectix,
  203 F.3d 596 (9th Cir. 2000).
- S65 https://eur-lex.europa.eu/eli/dir/2009/24/oj : Directive 2009/24/EC (Software Directive), arts. 5(3), 6, 8 (page
  did not render for our fetcher; content from knowledge of the text).
- S66 https://en.wikipedia.org/wiki/Tetris_Holding,_LLC_v._Xio_Interactive,_Inc. : Tetris Holding v. Xio Interactive,
  863 F. Supp. 2d 394 (D.N.J. 2012).
- S67 https://www.law.cornell.edu/uscode/text/17/102 : 17 U.S.C. 102(b), no copyright in ideas, procedures, systems
  (not re-read today).
- S68 https://en.wikipedia.org/wiki/Newton_v._Diamond : Newton v. Diamond, 388 F.3d 1189 (9th Cir. 2004).
- S69 https://en.wikipedia.org/wiki/Skidmore_v._Led_Zeppelin : Skidmore v. Led Zeppelin, en banc (9th Cir., 9 March
  2020).
- S70 https://www.law.cornell.edu/uscode/text/18/1839 : 18 U.S.C. 1839(6), reverse engineering is not "improper means".
- Not fetched, cited from knowledge: Davidson & Associates v. Jung, 422 F.3d 630 (8th Cir. 2005); Williams v. Gaye,
  895 F.3d 1106 (9th Cir. 2018); EU Trade Secrets Directive 2016/943 art. 3; ITU-R BS.1770 (current revision);
  ISO 3382-1 (room acoustics measurement); Harvey Fletcher's 1962 piano-string inharmonicity paper (JASA); Karen
  Collins, *Game Sound* (MIT Press, 2008); Andy Farnell, *Designing Sound* (MIT Press, 2010), a book-length guide to
  procedural game sound in Pure Data; pYIN, Mauch and Dixon, ICASSP 2014 (implementation verified by running
  `librosa.pyin`).

---

## Appendix A. The closed-loop demonstration script (our code)

Run with the house Python (`py demo.py`); writes WAVs and `results.json` next to itself. It was run from the session
scratchpad, never inside the repo. This condensed listing was itself extracted from this file and re-run on
2026-10-13: it reproduced the E2, E3, E6 and E8 numbers and the three codec rows it covers from E5 exactly. Demo E imports `arsenal.media`; set `ARSENAL_MEDIA_STATE` to a scratch folder so
its receipt does not land in `state/`. The E4 follow-up varied `T` (6, 15, 20 s) and the drive (0 or 1.4) in
`demo_b`'s setup and is summarised in section 7.2.

```python
"""Closed-loop demonstrations for the audio reverse-engineering report (2026-10-13).
Every target is SYNTHETIC: we make a sound whose recipe we know, hand only the audio to the analysis,
and score how much of the recipe comes back. Nothing third-party is analysed. CPU only."""
import json, math, os, sys, time
from pathlib import Path
import numpy as np
import scipy.signal as sg
import soundfile as sf
import librosa

OUT = Path(__file__).resolve().parent
RESULTS = {}
rng = np.random.default_rng(20261013)
SR = 48000

# ---------- A. synth patch: band-limited saw -> 2-pole low-pass -> ADSR; blind analysis; resynthesis ----------
def saw(f0, dur, sr=SR):
    t = np.arange(int(dur * sr)) / sr
    y, n = np.zeros_like(t), 1
    while n * f0 < sr / 2 * 0.95:
        y += np.sin(2 * np.pi * n * f0 * t) / n
        n += 1
    return y * (2 / np.pi)

def adsr(n, sr, a, tau_d, s, note_off, tau_r):
    t = np.arange(n) / sr
    env = np.empty(n)
    att = t < a
    env[att] = t[att] / a
    held = (t >= a) & (t < note_off)
    env[held] = s + (1 - s) * np.exp(-(t[held] - a) / tau_d)
    lvl_off = s + (1 - s) * math.exp(-(note_off - a) / tau_d)
    rel = t >= note_off
    env[rel] = lvl_off * np.exp(-(t[rel] - note_off) / tau_r)
    return env

def render(f0, fc, order, a, tau_d, s, tau_r, dur=2.0, note_off=1.2):
    y = saw(f0, dur)
    if fc is not None:
        y = sg.sosfilt(sg.butter(order, fc, "low", fs=SR, output="sos"), y)
    y = y * adsr(len(y), SR, a, tau_d, s, note_off, tau_r)
    return 0.5 * y / np.max(np.abs(y))

def mrstft(x, y):
    """Multi-resolution STFT log-magnitude L1 distance (lower = closer)."""
    d = 0.0
    for nfft in (256, 1024, 4096):
        X = np.abs(librosa.stft(x, n_fft=nfft, hop_length=nfft // 4))
        Y = np.abs(librosa.stft(y, n_fft=nfft, hop_length=nfft // 4))
        d += np.mean(np.abs(np.log(X + 1e-5) - np.log(Y + 1e-5)))
    return d / 3

def demo_a():
    true = dict(f0=220.0, fc=1200.0, order=2, a=0.020, tau_d=0.100, s=0.40, tau_r=0.120)
    y = render(**true)
    # 1. pitch (pYIN) on the held part
    f0s, voiced, _ = librosa.pyin(y[: int(1.2 * SR)], fmin=50, fmax=2000, sr=SR, frame_length=4096)
    f0_est = float(np.nanmedian(f0s[voiced]))
    # 2. harmonic levels on the sustain plateau
    seg = y[int(0.7 * SR): int(1.15 * SR)]
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freqs = np.fft.rfftfreq(len(seg), 1 / SR)
    ks = np.arange(1, 41)
    levels = np.array([20 * np.log10(spec[(freqs > k * f0_est - 0.3 * f0_est) &
                                          (freqs < k * f0_est + 0.3 * f0_est)].max() + 1e-12) for k in ks])
    # 3. fit "1/k source x Butterworth magnitude" over cutoff and order
    best = None
    for order in (1, 2, 3, 4):
        for fc in np.arange(200, 8000, 10):
            model = -20 * np.log10(ks) - 10 * np.log10(1 + (ks * f0_est / fc) ** (2 * order))
            g = np.mean(levels - model)
            err = np.mean((levels - model - g) ** 2)
            if best is None or err < best[0]:
                best = (err, fc, order)
    _, fc_est, order_est = best
    # 4. envelope: pitch-synchronous RMS frame (v1 used a fixed 512-sample frame: ripple, see E1)
    hop, frame = 64, int(round(4 * SR / f0_est))
    rms = librosa.feature.rms(y=y, frame_length=frame, hop_length=hop, center=True)[0]
    t = np.arange(len(rms)) * hop / SR
    rms = rms / rms.max()
    i_pk = int(np.argmax(rms))
    a_est = (t[np.argmax(rms >= 0.9)] - t[np.argmax(rms >= 0.1)]) / 0.8
    s_est = float(np.median(rms[(t > 0.9) & (t < 1.15)]))
    below = (t > 0.6) & (rms < s_est * 0.90)          # note-off: 20 ms below 90 % of the plateau
    run = int(0.020 * SR / hop)
    idx = [i for i in range(len(below) - run) if below[i: i + run].all()]
    t_off = (t[idx[0]] if idx else 1.2) - 0.5 * frame / SR
    dec = (t > t[i_pk] + 0.01) & (t < t_off - 0.05)
    resid = rms[dec] - s_est
    ok = resid > 0.05
    tau_d_est = -1 / np.polyfit(t[dec][ok], np.log(resid[ok]), 1)[0]
    rel = (t > t_off + 0.01) & (rms > 1e-3)
    tau_r_est = -1 / np.polyfit(t[rel], np.log(rms[rel]), 1)[0]
    est = dict(f0=f0_est, fc=float(fc_est), order=int(order_est), a=float(a_est),
               tau_d=float(tau_d_est), s=s_est, tau_r=float(tau_r_est))
    naive = dict(f0=f0_est, fc=None, order=2, a=0.005, tau_d=0.2, s=0.7, tau_r=0.3)
    RESULTS["A"] = {"true": true, "estimated": est, "note_off_s": float(t_off),
                    "dist_resynth": mrstft(y, render(**est)), "dist_naive": mrstft(y, render(**naive))}

# ---------- B. impulse response by exponential sine sweep (Farina 2000) ----------
def demo_b(T=6.0, drive=1.4):
    sr, f1, f2 = 48000, 20.0, 20000.0
    t = np.arange(int(T * sr)) / sr
    L = T / math.log(f2 / f1)
    sweep = np.sin(2 * np.pi * f1 * L * (np.exp(t / L) - 1))
    inv = sweep[::-1] * np.exp(-t / L)                    # time-reversed, tilted -6 dB/octave
    rt60, n_ir = 0.6, int(1.5 * sr)
    h = np.zeros(n_ir); h[0] = 1.0; h[int(0.007 * sr)] += 0.5
    tt = np.arange(n_ir) / sr
    tail = rng.standard_normal(n_ir) * np.exp(-6.9078 * tt / rt60) * 0.08
    tail[: int(0.010 * sr)] = 0
    h += tail
    x = np.tanh(drive * sweep) / np.tanh(drive) if drive else sweep   # symmetric soft clip: odd harmonics
    y = sg.fftconvolve(x, h)
    y += rng.standard_normal(len(y)) * 10 ** (-70 / 20)
    ir_full = sg.fftconvolve(y, inv)
    peak = int(np.argmax(np.abs(ir_full)))
    ir_lin = ir_full[peak: peak + n_ir] / ir_full[peak]
    def t20(ir):                                          # Schroeder backward integral, -5..-25 dB fit, x3
        edc = np.cumsum(ir[::-1] ** 2)[::-1]
        db = 10 * np.log10(edc / edc[0] + 1e-30)
        tt_ = np.arange(len(db)) / sr
        sel = (db <= -5) & (db >= -25)
        return -60 / np.polyfit(tt_[sel], db[sel], 1)[0]
    RESULTS["B"] = {"rt60_est": t20(ir_lin), "rt60_meter_on_truth": t20(h),
                    "3rd_harmonic_lead_predicted_s": L * math.log(3)}

# ---------- C. lossy-history fingerprint: encode, decode, read the cutoff ----------
def demo_c():
    sys.path.insert(0, r"E:\AI-Setup")
    os.environ.setdefault("ARSENAL_MEDIA_STATE", str(OUT / "media-state"))
    from arsenal.media import ff
    sr = 44100
    x = rng.standard_normal((sr * 8, 2)) * 0.1            # stereo: bitrate shared by two channels
    sf.write(OUT / "c_noise.wav", x, sr, subtype="PCM_16")
    for name, args, ext in (("mp3_128k", ["-c:a", "libmp3lame", "-b:a", "128k"], "mp3"),
                            ("aac_128k", ["-c:a", "aac", "-b:a", "128k"], "m4a"),
                            ("opus_96k", ["-c:a", "libopus", "-b:a", "96k"], "ogg")):
        enc, dec = OUT / f"c_{name}.{ext}", OUT / f"c_{name}_dec.wav"
        ff.run(["-y", "-i", str(OUT / "c_noise.wav")] + args + [str(enc)])
        ff.run(["-y", "-i", str(enc), "-c:a", "pcm_s16le", str(dec)])
        y, sr_dec = sf.read(dec)
        f, p = sg.welch(y.mean(axis=1), fs=sr_dec, nperseg=8192)
        db = 10 * np.log10(p + 1e-30) - np.median(10 * np.log10(p[(f > 1000) & (f < 5000)]))
        RESULTS.setdefault("C", {})[name] = {"cutoff_hz_at_-30dB": int(f[db > -30].max()), "decoded_sr": sr_dec}

# ---------- D. chords from audio: CQT chroma + triad templates ----------
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

def piano_note(midi, dur, sr, B=0.0004, tilt=1.1, damp=0.35):
    f0 = 440 * 2 ** ((midi - 69) / 12)
    t = np.arange(int(dur * sr)) / sr
    y = np.zeros_like(t)
    for n in range(1, 16):
        fn = n * f0 * math.sqrt(1 + B * n * n)            # stiff-string inharmonicity
        if fn > sr / 2 * 0.9:
            break
        y += (1 / n ** tilt) * np.sin(2 * np.pi * fn * t) * np.exp(-t * (0.8 + damp * n))
    return y

def demo_d(tilt=1.1, damp=0.35, bass_gain=1.0):           # E7 used tilt=0.4, damp=0.05, bass_gain=3.0
    sr = 22050
    prog = [("C", [36, 55, 60, 64]), ("G", [43, 55, 59, 62]), ("Am", [45, 57, 60, 64]), ("F", [41, 57, 60, 65])]
    y = np.concatenate([sum(piano_note(m, 2.0, sr, tilt=tilt, damp=damp) * (bass_gain if j == 0 else 1.0)
                            for j, m in enumerate(notes)) for _, notes in prog])
    chroma = librosa.feature.chroma_cqt(y=0.5 * y / np.max(np.abs(y)), sr=sr, hop_length=512)
    fps = sr / 512
    tpl = {}
    for r in range(12):
        # (Vandor, 2026-10-13: the two 12-slot literals were rewritten as interval sets, same arrays, so this file
        # clears the shader licence line, which saw a coincidental 12-token run of 0s and 1s)
        tpl[NAMES[r]] = np.roll(np.isin(np.arange(12), [0, 4, 7]), r).astype(float)      # major: root, M3, P5
        tpl[NAMES[r] + "m"] = np.roll(np.isin(np.arange(12), [0, 3, 7]), r).astype(float)  # minor: root, m3, P5
    rows = []
    for i, (label, _) in enumerate(prog):
        c = chroma[:, int((2 * i + 0.2) * fps): int((2 * i + 1.8) * fps)].mean(axis=1)
        sims = sorted(((k, float(c @ v / (np.linalg.norm(c) * np.linalg.norm(v)))) for k, v in tpl.items()),
                      key=lambda kv: -kv[1])
        rows.append({"played": label, "detected": sims[0], "runner_up": sims[1]})
    RESULTS.setdefault("D", []).append(rows)

# ---------- E. the house loudness door on the demo-A note ----------
def demo_e():
    sys.path.insert(0, r"E:\AI-Setup")
    os.environ.setdefault("ARSENAL_MEDIA_STATE", str(OUT / "media-state"))
    from arsenal.media import audio
    sf.write(OUT / "a_target.wav", render(220.0, 1200.0, 2, 0.02, 0.1, 0.4, 0.12), SR, subtype="PCM_24")
    RESULTS["E"] = audio.loudness(str(OUT / "a_target.wav")).get("tracks")

if __name__ == "__main__":
    for fn in (demo_a, demo_b, demo_c, demo_d, demo_e):
        fn()
    (OUT / "results.json").write_text(json.dumps(RESULTS, indent=2, default=str), encoding="utf-8")
    print(json.dumps(RESULTS, indent=2, default=str))
```
