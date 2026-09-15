# Live sheet music, lane T: performance MIDI to readable notation

| | |
|---|---|
| Status | Research and design, 2026-09-14. Nothing under `arsenal/` edited (the jam build owns `arsenal/web/piano.js` tonight). No server, browser, download, install or login. |
| Asked for | Daniel, verbatim: "what if we keep a rough estimate of bpm and make it possible to save the notes i am playing into something that can render into sheet music with correct notation in real time, I wonder if we can make that happen!" |
| This lane | The steps from timed notes to a correct score: beat and rough BPM, rhythm quantization, bars and ties, hands and voices, chords against rolls and arpeggios, pedal, pitch spelling and key signature, dynamics, grace notes, and a live score that settles without rewriting itself. Survey of prior art. |
| Not this lane | How and where the score is drawn in the frame (display lane), the song listener's beat (`practice-along-2026-09-14/live-key-bpm.md`), the chord reader (`piano-theory-nextgen-2026-09-14/theory-nextgen-spec.md`). This file names the interfaces it needs from them. |
| Measured | Four read-only scratch scripts (`scratchpad/sheet/stats.py`, `stats2.py`, `stats3.py`, `stats4.py`, not tracked) over the 12 practice sessions on disk. S8 has 11 notes and is skipped. |
| Privacy | Counts, intervals, shares and short rhythmic statistics only. Sessions are **S1-S12 in folder order (this lane's numbering; the theory lane's S1-S6 are a different set)**. No session ids, clock times, pitches in sequence or transcriptions. |
| Labels | Stages **T0-T10**, slices **SM0-SM9**, receipts **SR1-SR14**, questions **Q1-Q6**. Other docs' labels (J, TN, AL, LIVE) are cited as sources only. |

---

## 0. In one screen

**Yes, it can be made, and most of the parts already exist.** The practice log already saves everything a score needs:
every key down and up with its velocity, every pedal move and the moment each note stopped sounding, to the
millisecond. So "save the notes" is done today, and every past session can be turned into sheet music too. What is
missing is the transcriber: the steps that decide *which rhythm he meant*.

**The hard part is the beat, not the notes.** Measured on his own playing:

- His rough tempo is easy. The commonest gap between onsets is his eighth note, and doubling it gives a quarter of
  **74-102 bpm** across sessions, inside the 60-110 feel. A "rough BPM" readout is a one-evening job.
- A **steady grid is rare**. Even letting the tempo and phase be chosen afresh for every 4-second stretch (a best
  case no live system gets), a 16th-note grid explains 80% of the onsets within 20 ms in only **34%** of stretches,
  against 8% for random notes. Over 8-second stretches that drops to **9%** (2% random). The tempo breathes inside
  a bar or two.
- Snapping each note to the nearest 16th under one running tempo gives errors **no better than random notes**
  (median residual 18-24 ms against a chance level of 20-25 ms). Per-note snapping is meaningless without a beat model.

**So the design has three ideas.**

1. **A beat-source ladder.** Use the exact beat when one exists, and infer it only as a last resort:
   - the jam tempo map while a loop runs (exact, 2 ms alignment);
   - the song listener's beat while playing along;
   - his taps and a "This is 1" press;
   - then a beat inferred from his own playing;
   - otherwise **free time**, shown honestly as unmetered notation, never a forced wrong rhythm.
2. **Rhythm decided per beat, not per note.** Each beat picks one division (whole, halves, 16ths, triplets) by cost:
   timing fit against simplicity and against what the previous beat and the same beat of the previous bar did. His
   loops repeat, which the repetition prior uses.
3. **Bars settle and then never move.** The bar being played is provisional. A bar that ended waits **4 beats**
   (about 3 s at 80 bpm), then freezes. Measured on the logs with a simple tracker, freezing after 4 beats leaves
   **5.7%** of onsets labelled differently from what 8 beats of hindsight would say, against 20.4% if frozen at once.
   Later corrections apply only forward. A full **clean copy** is re-engraved from the log when the session ends.

**Notation choices that fit his playing** (each measured in section 1):

- **Staves and voices.** Hands are split by the largest gap in each chord plus continuity over time, never at a
  fixed middle C: 37-73% of his chords touch G3-E4.
- **Pedal and duration.** Pedalled notes are written as played, with pedal marks, not as their ringing length. The
  pedal ends 28-50% of his notes, and ringing lengths would bury the page in ties.
- **Rolls and grace notes.** A chord rolled over 50-120 ms gets a wavy arpeggio line. A short step-wise note just
  before a main note becomes a grace note (0.5-3 a minute).
- **Spelling.** Pitches are spelled by the same `spellInKey` the chips and numbers use, so the staff never disagrees
  with the label. Key signatures come from the key tracker, with hysteresis.
- **Dynamics.** Marks come from velocity in 4 s windows with hysteresis, 0.5-2.8 marks a minute.

**Nobody ships this live for rubato piano.**

- ScoreCloud, Dorico and Sibelius record live but want a click. ScoreCloud's own FAQ says it "does not know what your
  foot is tapping" ([FAQ](https://scorecloud.com/support/)), though its 2026 marketing claims rubato handling.
- MuseScore's import quantizes against one tempo for the whole piece.
- The research systems are much better but offline and PyTorch-based:
  - PM2S, ISMIR 2022, MIT licence;
  - MIDI2ScoreTransformer, ISMIR 2024;
  - a 2026 T5 quantizer that needs the beats given to it.

  They are yardsticks for the clean copy, not live parts.

**Decisions for Daniel** (section 10): what free time looks like (Q1), pedalled notes as played or as sounding (Q2),
whether any notation library is vendored (Q5, needs his OK), and whether the score strip enters the recording (Q4,
display lane).

---

## 1. What his playing looks like to a transcriber (measured)

Onset groups merge note-ons within 40 ms, as `arsenal/performance.py` `ONSET_MERGE_MS` does. Ranges are across the 11
usable sessions unless noted.

| Measure | Value | What it means for notation |
|---|---|---|
| Notes per minute | 74-406 (median session about 250) | A 4/4 bar at 80 bpm holds about 12 notes on average: dense but engravable. |
| Onset groups with 2+ notes | 26-40% | Chords are frequent; per-beat quantization must treat a chord as one event. |
| Spread of a 3+ note group (first to last onset inside 40 ms) | median 14-28 ms, p90 31-38 ms | 40 ms catches his block chords; a wider spread is a roll or two events. |
| 3+ note clusters within 120 ms that are monotonic in pitch and spread 50 ms or more | 3-16% of such clusters | Rolled chords exist but are the minority: an arpeggio line, not the default. |
| Two-hand groups (span 12+, gap 7+): top onset minus bass onset | median 0-16 ms (bass first), p90 36-98 ms | Bass leads slightly. Under about 60 ms, write simultaneous. Above that, either two positions or a roll. |
| Monotonic runs of 4+ onsets 60-300 ms apart | 0.3-4.5 per minute | Broken-chord figures are real rhythm (16ths, triplets), not rolls. |
| Gap between onsets (group to group) | median 182-294 ms, p90 412-1030 ms | His eighth sits near 180-300 ms. |
| Most common gap cluster, as bpm | 148-192, so the quarter is **74-102 bpm** | The rough BPM, octave-corrected to his 60-110 feel (T2). |
| Spread of gaps near that cluster (CV) | 0.10-0.14 | About 35-55 ms of timing spread per gap at his eighth. A 16th (187 ms at 80 bpm) against a triplet eighth (250 ms) differs by 63 ms, under 2 sigma per note, so decide per beat (T3). |
| Pauses of 2 s or more | 1-73 per session | Phrase ends: re-anchor the beat, close or free the bar. |
| 8 s windows with no clear pulse (under 4 gaps within ±25 ms of the modal gap) | 7% (S4) to 87% (S11); S12 74%, S3 46% | Much of his playing has no countable pulse. This includes windows with pauses, so it overstates a little. Free time must be a first-class mode (T2.5, Q1). |
| Pulse change between consecutive 8 s windows (where both have one) | median 1.1-5.7%, p90 7.7-30% | Tempo drifts within phrases; a tempo fixed per bar or longer fails. |
| Best-case grid fit, tempo and phase searched per window, 20 ms tolerance: share of windows where 80%+ of onsets fit | 4 s windows: 16th grid **34%** (random 8%), triplet grid 27% (random 2%), eighth grid 2% (random 2%). 8 s windows: 16th 9% (2%), triplet 6% (0.6%) | Metrical evidence is local and weak. Inferring rhythm must track beat by beat and admit defeat. |
| Nearest-16th residual under a naive running tempo | median 18-24 ms against chance 20-25 ms | Grid snapping without a beat model is noise. |
| Successive gap ratios within ±7% of 1:1, 2:1, 3:1, 3:2 and their inverses | 32-48% real against 34-41% shuffled | A ratio-only quantizer (Desain-Honing style) has little to hold on his playing; beat-relative quantization is needed. |
| Key held (on to off) | median 166-266 ms | What his hands wrote. |
| Sounding (on to sound end) | median 296-958 ms | About 2-4.5 times the held length, because of the pedal. |
| Notes ended by the pedal | 28-50% of notes (S6 28%, S10 50%) | Written duration comes from the keys; the pedal marks carry the ring (T6, Q2). |
| Time with the pedal down | 22-95% | Pedal marks are needed on most pages. |
| Pedal presses per minute | 6.7-22.5 | That is a lot of "Ped." marks: use bracket notation with change notches. |
| Pedal-down lag after the latest onset | median 110-190 ms | Legato pedalling: a change notch belongs at the chord it follows. |
| Pedal up to down (a change) | median 124-200 ms | Up then down within about 300 ms is one change, not a stop and a start. |
| Groups touching G3-E4 (near middle C) | 37-73% of multi-note groups | A fixed split at C4 would cut his chords in half. |
| Largest pitch gap inside a multi-note group | median 11-24 semitones | The largest gap is a strong hand-split cue. |
| Groups containing a 10th above their bass | 3-26% | His bass-plus-10th texture; S11 is the 26%. |
| Lowest held key at C2 or below, at an onset | 9-32% in S1-S7, S9, S12 | Ledger lines under the bass staff or 8vb are routine. S10 and S11 read higher, probably a count artifact from re-strikes without a logged release. |
| Highest held key at C6 or above | 0-26% | 8va brackets or ledger lines above the treble staff are routine. |
| Velocity | median 46-86; p10-p90 about 30-108 | Sessions differ a lot, from instrument, curve or mood. Dynamics must hold steady against that (T8). |
| Dynamic band changes (4 s windows, 2-window hysteresis) | 0.5-2.8 per minute | About one mark every 20-120 s: readable. |
| Staccato-like (held under 120 ms, ended by release) | 0.4-19% | Mostly few; S6 is the exception. |
| Grace-note candidates (held under 110 ms, a step to the next onset, 30-120 ms before it) | 0.5-3.1 per minute | Worth supporting; worth a guard against false positives. |

**Settle churn** (stats4). A causal tracker labels each onset (beat, subdivision in {0, 1/4, 1/3, 1/2, 2/3, 3/4});
a fixed-lag smoother re-fits beat times from on-beat onsets in [j-4, j+k]. The measure is the share of onsets whose
label at lag k differs from the label at lag 8 beats.

| Lag before freezing | 0 beats | 1 beat | 2 beats | 4 beats |
|---|---|---|---|---|
| All sessions | 20.4% | 14.6% | 10.7% | **5.7%** |
| Range by session | 13.9-28.5% | 8.6-21.3% | 6.1-14.9% | 3.3-7.2% |

Caveats:

- The reference (lag 8) is self-consistency, not truth.
- The tracker is deliberately simple (phase gain 0.3, period gain 0.1) and starts from the session's pulse, a mild
  oracle.
- The numbers bound *stability*, not correctness.

The first quarter tempo it chose per session was 74-102 bpm.

---

## 2. The pipeline

```
Daniel's note events only (on, off, pedal, sound_end; t_ms; vel)      <- the same stream log.js appends (H2: his sources only)
  T1 onset events      chords (40 ms), rolls, grace notes, broken-chord runs, trills
  T2 beat and tempo    beat-source ladder -> beats {t, index, conf}, bar phase, meter, rough BPM, free-time flag
  T3 rhythm            per-beat division by cost -> positions in 1/12 of a quarter; durations; rests
  T4 bars              bar lines, ties across bars and beat 3, dotted values, beaming groups, pickups, fermatas
  T5 hands and voices  staff per note (gap + continuity DP), up to 2 voices per staff, clef and 8va
  T6 chords and pedal  arpeggio lines, pedal brackets and change notches, held-bass option
  T7 spelling and key  spellInKey via the chord reader, key signature with hysteresis, accidentals and courtesy
  T8 dynamics, marks   velocity bands, hairpins, accents, staccato; tempo words (rit., a tempo, freely)
  T9 settle            bar states open -> settling -> settled; revisions; forward-only corrections
  T10 output           score JSON (live and clean copy), MusicXML 4.0 export; linked to performance notes
```

Each stage is a pure function of event time, not timer time (the harmony window's rule H4), so a hidden tab, a replay
and an offline run all give the same score. All stages run in the page and under node from one code base: the "one
engine" rule of theory-nextgen D1, and the practice_theory.mjs pattern.

---

## 3. The stages in detail

### T1. Onset events

| Event | Rule (v1 parameters, tuned on fixtures in SM1) | Notation |
|---|---|---|
| **Chord** | Note-ons within 40 ms of the group's first. | One chord event at one position. |
| **Near-chord across hands** | A two-hand group whose bass leads by 40-80 ms, not monotonic across 3+ notes. | Still one position when the lead is under a third of the current 16th (about 60 ms at 80 bpm); otherwise two positions. |
| **Rolled chord** | 3+ notes chained within 120 ms, monotonic in pitch, total spread 50 ms or more, and every note still held or pedalled when the last arrives. | One chord with an arpeggio line (up, or down with an arrow when descending), at the first onset's position. MusicXML `<arpeggiate>` ([W3C reference](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/arpeggiate)). |
| **Broken-chord run** | 4+ onsets 60-300 ms apart, monotonic, whether pedalled or not. | Real rhythm, quantized in T3 (never collapsed into a roll). |
| **Grace note** | Held under 110 ms, 30-120 ms before an onset 1-2 semitones away in the same hand, and the main note sits on a grid position while the short one does not (checked after T3's first pass). | Slashed grace note attached to the main note; it takes no time in T3. EngravingGNN removes grace notes before engraving for the same reason ([arXiv 2509.19412](https://arxiv.org/abs/2509.19412)). |
| **Trill or tremolo** (v2) | 4+ strict alternations between two pitches at gaps under 100 ms. | Trill (a 2nd apart) or tremolo (wider). MIDI2ScoreTransformer predicts trills directly ([arXiv 2410.00210](https://arxiv.org/abs/2410.00210)). Unmeasured on his logs. |

### T2. Beat, rough BPM, bars and free time

#### T2.1 The beat-source ladder

The first source available wins. The source is written into every measure, so the page and the clean copy can say
where the rhythm came from.

| Rung | Source | Accuracy | Available |
|---|---|---|---|
| 1 | **Jam tempo map** while a run plays: `barAt`/`tEpoch` in `arsenal/web/piano/tempomap.js`, session time by the jam spec 11.2 ladder (L1/L2 at 2 ms or better) | Exact bars and beats | After J9 |
| 2 | **Song listener** while following a track: `state().beat {periodMs, nextBeatPerf, phaseConf, barPhase}` (practice-along plan 2.2) | ±30 ms phase; bar phase only after "This is 1" | After AL phases |
| 3 | **His taps**: four taps set period and phase; "This is 1" sets the bar phase (the same controls as practice-along) | ±40 ms | SM2 |
| 4 | **Inferred from his playing** (T2.2) | Loose; confidence-gated | SM2 |
| 5 | **None: free time** (T2.5) | No rhythm claimed | SM2 |

#### T2.2 Inferring the beat from his notes

- **Initial period.** The modal gap between onset groups in 250-1000 ms, over the last 8 s of playing. It is doubled
  until the quarter lies in **55-110 bpm**; measured, this lands at 74-102 bpm on every session. A tap or a stored
  choice overrides the octave. The half and double confusion is the main failure of every tempo system: PM2S names it
  among its typical errors (paper cited in 4.2), and `live-key-bpm.md` 5.3 has the audio side.
- **Running update** (onset-driven, a Large-Kolen style phase and period correction, as in stats4):
  1. Each onset is labelled with its nearest subdivision.
  2. On-beat onsets correct the phase by 0.3 of their error and the period by 0.1.
  3. A chord's weight counts its notes and its velocity; a new bass note counts double (bass notes land on beats
     more often in his style; to be measured in SM2).
  4. The period is clamped to 400-1200 ms.
- **v2 alternative.** A small particle filter over (period, phase) with a quantization prior, as in Cemgil and Kappen,
  whose model they describe as suitable for real-time tracking
  ([NeurIPS 1999](http://papers.neurips.cc/paper/1999-tempo-tracking-and-rhythm-quantization-by-sequential-monte-carlo.pdf)).
  It keeps a runner-up tempo alive instead of committing.
- **Confidence** is the share of the last 8 beats' onsets within 12% of a beat of their division grid, weighted by
  velocity.

#### T2.3 Rough BPM readout (the first thing Daniel asked for)

- Show the median period of the last 8 confident beats as `♩ ≈ 80`, with a steadiness word shared with practice-along:
  `steady`, `loose` (confidence under 0.7) or `free` (T2.5).
- It updates at most once a bar, and only by 3 bpm or more.
- In the score it becomes a metronome mark at each phrase start, and a tempo word when the tempo moves (T8).

#### T2.4 Bars, meter and pickups

- **Meter.** 4/4 by default. Choose 3/4 when chord windows from `harmony.js` change every 3 beats for 4+ changes. Use
  12/8 instead of 4/4-with-triplets when 75%+ of divided beats over 2 bars are triple (Q6).
- **Bar phase.** In priority order:
  1. the jam or song bar;
  2. "This is 1";
  3. inferred: the beat carrying a new bass note and a new harmony window, with a velocity accent. Harmonic change on
     bar lines is the practice-along v2 cue too. It is scored over the phrase's first 8 beats, and the first bar
     until then is a pickup candidate.
- **Pickups.** Onsets before the chosen downbeat become a pickup bar only while that bar is still unsettled.
  Otherwise the phrase starts with a partial bar of rests (forward-only, T9).
- **Phrase ends.** A pause of 2 s or more, or of more than 2 beats with the pedal up, ends the phrase. The last bar is
  completed with rests, or with a fermata when the last chord was held more than twice its expected beat. The beat
  re-anchors on the next onset.

#### T2.5 Free time

Free time is entered when confidence stays under 0.5 for 2 beats, or when a phrase starts with no pulse after 4
onset groups. It is left after 4 consecutive confident beats, at the next harmony-window start.

The honest options (Q1):

- **(a) Unmetered, recommended.** No time signature and no rhythm claimed:
  - dashed bar lines at harmony-window boundaries;
  - noteheads without stems, placed proportionally to time;
  - note heads held by key or pedal drawn with a thin duration line, like a piano roll inside the staff;
  - a small `freely` word.

  Spelling, hands, pedal and dynamics all still apply.
- **(b) Forced.** Quantize to the rough BPM anyway, marked `rubato`. It reads like music but claims rhythms he did not
  count; measured, most 8 s stretches do not fit any grid.
- **(c) Both.** (a) live, (b) in the clean copy only.

### T3. Rhythm quantization

- **Unit.** Positions and durations are integers in **1/12 of a quarter**, which holds 16ths (3) and triplet eighths
  (4); sextuplets (2) are v2. It is also MusicXML's `divisions` = 12. The 2026 beat-conditioned quantizer uses the same
  twelve sub-beats per beat ([arXiv 2604.22290](https://arxiv.org/abs/2604.22290)). MIDI2ScoreTransformer uses 1/24.
- **Per-beat division.** For beat b with period P, a timing spread σ (starting at 40 ms, then learned from on-beat
  residuals) and onset fractions f_i, the cost of each division d in {1, 2, 4, 3} is:

  ```
  C(d) = Σ_i min_k ((f_i − k/d)·P)² / (2σ²)                       timing fit
       + λ[d]                                                     simplicity: 1 → 0, 2 → 0.5, 4 → 1.5, 3 → 2.0
       + λ_prev · [d ≠ division of beat b−1]                      continuity, 0.8
       + λ_bar · [d ≠ division of the same beat one bar back]     repetition (his loops), 0.8
       + ∞ if two onset groups land on one slot                   (a roll, a grace note, or the wrong division)
  ```

  - Onsets with f above 0.875 belong to the next beat.
  - A beat with no onsets inherits nothing (d = 1).
  - This is the MAP view of quantization shared by Cemgil's and Nakamura's HMM work
    ([arXiv 1701.08343](https://arxiv.org/abs/1701.08343)), cut to one beat so it can run live.
  - Why per beat: at 80 bpm, a 16th against a triplet position is 63 ms apart, and his per-gap spread is 35-55 ms. One
    note cannot tell them apart; two or three notes in the same beat usually can.
- **Swing.** When straight-eighth beats keep a long-short ratio of 1.6-2.4 for 2+ bars (steady confidence), write
  straight eighths with a `swing` word instead of triplets. Swing research finds ratios near 2 at slow tempi
  ([swingogram, JNMR 2017](https://www.tandfonline.com/doi/full/10.1080/09298215.2017.1367405)). Off by default (Q6).
- **Durations.**
  - **Written end** is the key release (`off`), snapped to the next slot at or after the release in the same division.
    If the gap to the next onset in the same voice is under one 16th, the note extends to that onset. This is legato
    fill, what Dorico's "Fill gaps" option does
    ([Dorico blog](https://blog.dorico.com/2019/02/tip-how-to-get-great-results-with-midi-recording/)).
  - The shortest written value is a 16th (a triplet 16th in v2).
  - A key held under 40% of its slot with the pedal up gets a staccato dot and keeps its slot value.
  - **Pedalled notes** keep the written end from the keys, and the pedal marks carry the ring (Q2 option A). Option B
    extends each note to its `sound_end`, capped at the next onset of the same pitch or of its voice.
  - The **held-bass option** extends only the lowest voice to its sound end. This is the pop-piano-book look: a
    whole-note bass under moving right-hand figures. It is recommended as the default for his bass-plus-line texture.
- **Rests** fill each voice. Voice 2 hides rests where it is silent for a whole bar, a common piano convention.
- **Churn guard.** A beat already quantized is re-decided only while its bar is open or settling (T9).

### T4. Bars, ties, dotted values, beaming

Conventional engraving practice (Gould's *Behind Bars* style rules; no single web source):

- A duration crossing a bar line is split and tied, always.
- In 4/4, a note starting off the beat that crosses beat 3 is split there. A note starting on beat 1 or beat 3, or on
  beat 2 when it ends by beat 4, may stay whole: a half on beat 2 is allowed, and syncopated quarters show beat 3.
- A dotted value is allowed when it starts on a beat or on the half-beat and does not hide a beat group the reader
  needs. Otherwise use a tie.
- Beaming follows beats in simple meters and dotted quarters in 12/8. A tuplet is bracketed per beat, and two adjacent
  identical tuplets still get separate brackets.
- An accidental is not repeated on the tied-to note, even across a bar line (T7).
- Readability receipts (SR8) cap tuplet brackets, ties and voices per bar, and are checked on real sessions.

### T5. Hands, staves, voices, clefs

- **Split per onset group.** Candidate splits are every gap between adjacent pitches, plus "all left" and "all right".
- **Dynamic programming over time** (a Viterbi over the split of successive groups). Costs:
  - **Hand span.** A hand spanning more than 12 semitones costs 1; more than 16 costs 4. His 10ths (15-16) are
    possible but must be earned.
  - **Continuity.** The distance from each hand's recent centre, averaged over the last 2 s of key-held notes.
    Pedal-held notes do not count, since hands are not on them.
  - **Crossing.** The left hand above the right costs 3.
  - **Gap preference.** The largest gap costs 0; any other costs 0.5.
  - **Single-hand stretch.** When nothing is held in one region for a bar, the other hand may take the middle notes
    at no cost.
- **Prior art.** MuseScore offers a constant or "floating" split
  ([handbook](https://musescore.org/en/handbook/2/midi-import)), and Sibelius Flexi-time a moving split point
  ([Sibelius](https://www.sibelius.com/products/sibelius/acorninfo.html)). The learned version is Cluster and Separate:
  a GNN over quantized notes, MIT licence, 96.6 voice F1 on J-Pop against 89.9 on romantic repertoire
  ([arXiv 2407.21030](https://arxiv.org/abs/2407.21030), [code](https://github.com/CPJKU/piano_svsep)).
- **Staff from hand.** Left hand to the bass staff, right hand to the treble staff. A right-hand line down to F3 stays
  on the treble staff (3 ledger lines). Lower than that, it moves to the bass staff as voice 1 with stems up. No
  cross-staff beams in v1.
- **Voices.** At most 2 per staff:
  - When notes in one staff overlap with different onsets and different written ends (a held bass under a moving
    line), the sustained lower notes become voice 2 (stems down) and the moving upper line voice 1 (stems up).
  - Otherwise, simultaneous notes form one chord in voice 1.
  - This matches his texture: a bass plus a line a 3rd or 10th above, often split across the hands.
- **Clefs and octave lines.**
  - Allow 3 ledger lines. For 1+ bar beyond that, use `8va` above the treble staff or `8vb` below the bass staff:
    routine here (lowest key at C2 or below in 9-32% of onsets, highest at C6 or above in up to 26%).
  - A bass staff whose notes stay at or above C4 for 2+ bars switches to treble clef at a bar line, and back with the
    same hysteresis.
  - EngravingGNN predicts octave shifts and clefs at 99.9% and 96.2% on J-Pop, so these are learnable but also rare
    events.

### T6. Chords, arpeggios and the pedal

- **Chord against roll against run**: T1 decides; T6 only draws.
- **Pedal marks**, in bracket style under the bass staff: a start hook, a notch at each change, an end hook. LilyPond's
  text, bracket and mixed styles are the reference set, and it keeps marks matched to the physical pedal movement
  ([LilyPond](https://lilypond.org/doc/v2.24/Documentation/notation/piano)).
  - A pedal down within 250 ms after an onset group is notated at that group's position. That is the legato change
    notch; measured median lag 110-190 ms.
  - Up then down within 300 ms is one change notch. A longer up is an end, then a new start.
  - Half-pedal values are ignored in v1 (the log keeps 0..127; v2 can print `½ Ped.`).
  - Clutter option: when the pedal is down 80%+ of a phrase with a change on most harmony windows, print `con Ped.`
    once instead of notches (Q2).
- **Ring against held.** The held-bass option (T3) and the pedal marks together show the ring without long ties on
  every note. `l.v.` ties are v2, for a final chord left ringing after the hands lift.
- **Chord symbols** (optional line above the treble staff): at each settled harmony window from `harmony.js`, placed on
  the beat position of the window start and spelled in key by the reader. For an ear player this is the most readable
  layer of all. The reader owns the name and this lane only places it.

### T7. Pitch spelling, key signature, accidentals

- **Spelling** follows the rule the rest of the page follows. The theory spec's A7 already requires every printed root
  to go through `spellInKey`:
  - **Chord tones.** The reader's chord spelling in the shown key, the path `spellForKey` in `piano.js` takes for the
    chips, so the staff, the chips and the Nashville row never disagree.
  - **Passing and chromatic tones.** The key's spelling by `spellInKey`, then melodic direction breaks ties: a rising
    chromatic step takes the sharp or natural, a falling one the flat. This is the ps13 idea (Meredith), used by
    partitura's `estimate_spelling`
    ([partitura docs](https://partitura.readthedocs.io/en/latest/modules/partitura.html)).
  - **Measured references.** Dynamic-programming spelling with local keys reaches 98.2% on classical data, 99.5% on
    Bach ([arXiv 2402.10247](https://arxiv.org/abs/2402.10247)). EngravingGNN's integrated spelling reaches 96.3%
    (J-Pop) and 93.5% (romantic).
- **Key signature.**
  - It comes from the tracker (`createKeyTracker`: key, confidence `unsure`/`fair`/`sure`, `locked`, provisional
    picks). A minor key uses its relative major's signature, named as in `performance.py` `MAJOR_KEY_NAMES`
    (D♭, not C♯).
  - **Change rule.** A new signature is placed at the first unsettled bar line after the tracker has held a non-provisional
    key for 2 bars. It is never placed on a settled bar, which keeps its accidentals.
  - The clean copy uses `performance.py` `key_areas` (30 s minimum area) for signatures, so a 19 s excursion stays
    accidentals rather than two signature changes.
  - Key signature estimation is hard even offline: EngravingGNN reaches 80.6% on J-Pop and 50.5% on romantic music,
    which argues for hysteresis and for accidentals over signature churn.
- **Accidentals.**
  - The common-practice rule: an accidental holds for that pitch and octave to the end of the bar
    ([Dorico reference](https://archive.steinberg.help/dorico_se/v3.5/en/dorico/topics/notation_reference/notation_reference_accidentals/notation_reference_accidentals_duration_rules_r.html)).
  - **Courtesy accidentals**, in parentheses: in the bar after an altered pitch, and for the same letter in another
    octave within the bar.
  - A tie carries its accidental without reprinting it. At a new system, a tied note does not reprint it either.
  - Double sharps and flats appear only where the chord spelling needs them (the theory spec keeps F𝄪 dim in G♯
    minor).

### T8. Dynamics, articulation, tempo words

- **Dynamics.**
  - The median velocity of onsets in 4 s windows maps to bands: pp under 36, p under 50, mp under 64, mf under 80,
    f under 96, ff from 96. These are absolute; the KeyLab curve is the same every night.
  - A new band must hold for 2 windows before its mark prints. Measured: 0.5-2.8 marks a minute.
  - **Per-session offset** (option): sessions differ (median velocity 46-86), so a toggle can centre the bands on the
    session's running median. Absolute bands are recommended, because a loud night should read louder.
  - Marks use the melody voice when voices differ by 12+ velocity (an idea to measure in SM6).
- **Hairpins.** A monotonic velocity trend over 4+ onsets spanning 1+ bar, with a change of 12 or more: a crescendo or
  diminuendo hairpin ending at the next band mark.
- **Accent.** A note 20+ above the running median of its hand.
- **Staccato**: T3.
- **Slurs**: v2 (phrase slurs from pauses and pedal lifts).
- **Tempo words.**
  - `rit.` when the period grows 10%+ over 2+ bars ending a phrase.
  - `accel.` for the mirror case.
  - `a tempo` when it returns within 4%.
  - `freely` at free-time entries.
  - A fermata by T2.4.

### T9. Keeping a live score stable

**Bar states.**

| State | When | Live view | May change |
|---|---|---|---|
| **open** | The playhead is inside the bar | Noteheads appear at their provisional position within their beat. Stems, beams and tuplets are drawn only for beats that have closed. | Everything |
| **settling** | The bar has ended; fewer than 4 beats have passed since | Full notation in lighter ink | Rhythm, voices, staff, spelling, marks |
| **settled** | 4 beats past its end, a phrase end (a 2 s pause), a source switch, or session end | Full ink | **Never**, in the live view |

- **Why 4 beats.** Measured churn is 20.4%, 14.6%, 10.7% and 5.7% at 0, 1, 2 and 4 beats (section 1). Four beats is
  about 2.4-3.2 s at his tempos, and it is also one 4/4 bar: the live strip trails by one bar. A pause settles
  everything at once, so at phrase ends the page catches up.
- **Revisions.** Each measure carries `rev`. The renderer redraws only measures whose `rev` changed, and a settled
  measure's `rev` is final.
- **Forward-only corrections.** When something learned late would change a settled bar (a tempo octave flip, a "This
  is 1" press, a key change recognized late), the correction applies from the first unsettled bar:
  - a new metronome mark;
  - a partial bar;
  - a new key signature with a double bar.

  The settled bars keep their mistake in the live view. The clean copy fixes it.
- **Layout stability** (a recommendation to the display lane). In the live strip, each beat gets a fixed width at the
  current tempo, and notes sit at their position within the beat. Settling then never moves a notehead sideways, only
  adds stems and beams. Engraved spacing (wider for dense beats) is for the clean copy.
- **Clean copy.** At session end, or on demand for any old session, the whole log is re-run with full lookahead:
  - a smoothed beat grid (fixed-lag becomes a full backward pass);
  - key areas from `performance.py`;
  - the pickup found in hindsight.

  The live and clean scores are stored side by side, so neither overwrites the other. An optional offline reference
  (PM2S or MIDI2ScoreTransformer, both PyTorch) could run on the clean copy's MIDI, but needs Daniel's OK to install
  (Q5).
- **Flicker receipt** (SR10): count notehead and label changes per minute in open and settling bars on replays,
  calibrated as theory-nextgen D14 requires. Settled bars must show zero changes.

### T10. Output: what gets saved

- **The log stays the source of truth.** It already holds on, off, pedal, sound end and velocity to the millisecond.
  So every session on disk can become sheet music, not only future ones.
- **Score JSON** (`arsenal.piano.score/v0`, a proposal). Every score note keeps the performance note it came from (its
  `t_ms` and MIDI note), which enables:
  - replay highlighting;
  - re-engraving;
  - "what did I actually play here".

  ```
  { api, session, transcriber: {version, params}, kind: "live" | "clean",
    measures: [{ n, state, rev, start_ms, end_ms, meter: [4, 4] | null /* free */, tempo: {bpm, source, steady},
                 key: {name, fifths, mode, conf}, staves: [{ staff: 1 | 2, clef, ottava, voices: [{ voice, events: [
                   { kind: "chord" | "rest", pos: 0..(12 × beats − 1), dur, dots, tuplet: {actual, normal} | null,
                     notes: [{ midi, step, alter, octave, accidental, courtesy, tie: {start, stop}, grace,
                               perf: {t_ms, note} }],
                     arpeggiate, staccato, accent } ] }] }],
                 pedal: [{ pos, type: "start" | "change" | "stop" }], dynamics: [{ pos, mark }],
                 words: [{ pos, text }], chords: [{ pos, name }] }] }
  ```

- **MusicXML 4.0 export** of the clean copy, with `divisions` 12, two staves, voices, `<arpeggiate>`, `<pedal>`,
  `<dynamics>`, grace notes and `<words>`. It opens in MuseScore, Dorico and Sibelius, so a TikTok caption can say
  "sheet music in the comments". Writing a file stays inside the repo's state folder; how Daniel receives it belongs
  to the integration lane.

---

## 4. Prior art

### 4.1 Products

| System | What it does well | Where it fails on expressive, pedalled piano | Use for us |
|---|---|---|---|
| **ScoreCloud** (DoReMIR) | Notation from MIDI or audio as you play; a rule-based "music cognition" model infers meter, key and voices ([learn page, 2026](https://scorecloud.com/learn/best-music-transcription-software/)) | Its marketing claims rubato handling without a click, but its FAQ recommends a click track for MIDI and says it struggles with heavy sustain and accompaniment ([FAQ](https://scorecloud.com/support/)). Not tested here: an install. | The closest product to the ask. Confirms that "live" in practice means click-assisted. |
| **MuseScore** MIDI import | Beat tracking for human performances, tuplet detection, constant or floating hand split ([handbook](https://musescore.org/en/handbook/2/midi-import)) | Quantizes against one tempo for the whole piece. PM2S found this shifts notes and scored its metrical alignment Fme at 15.3. Import options were dropped in MuseScore 4; restoring them is an open request from June 2025 ([issue 28402](https://github.com/musescore/MuseScore/issues/28402)). | A floor to beat; the target app for MusicXML export. |
| **Dorico** real-time recording | Notated durations follow quantization while played durations are kept for playback; Requantize later; retrospective record ([Steinberg docs](https://www.steinberg.help/r/dorico-se/5.1/en/dorico/topics/write_mode/write_mode_midi_recording/write_mode_midi_recording_notes_t.html)); Fill gaps and tuplet detection ([blog](https://blog.dorico.com/2019/02/tip-how-to-get-great-results-with-midi-recording/)) | Records to a click. No smart split point, so staves are fixed by hand ([Scoring Notes, 2019](https://www.scoringnotes.com/tips/real-time-midi-recording-in-dorico/)). | **Keep notation and performance separate.** Copy the requantize idea (our clean copy). |
| **Sibelius Flexi-time** | Follows tempo (rubato settings), a moving split point, tuplets, 1-2 voices per staff ([Sibelius](https://www.sibelius.com/products/sibelius/acorninfo.html)) | Expert advice is to turn rubato following *off* for competent players and to record one voice ([Scoring Notes](https://www.scoringnotes.com/tips/results-flexitime/)). A telling admission. | Moving split point; minimum note value; "adjust rhythms". |
| **Logic Pro** Score Editor | Display quantize and interpretation separate from the MIDI data ([Apple](https://support.apple.com/guide/logicpro/change-note-syncopation-and-interpretation-lgcp8535f288/10.5/mac/10.14.6), [display quantize](https://logicpro.skydocu.com/en/view-and-edit-music-notation/edit-notes-in-the-score-editor/quantize-the-timing-of-notes/)) | Recorded to the project tempo; no tempo inference from rubato playing. | The principle again: the score is a view, never an edit of the take. |
| **Klangio** (Piano2Notes, Transcription Studio) | Audio or video in; PDF, MusicXML and quantized or unquantized MIDI out; in-browser edits ([Klangio](https://klang.io/transcription-studio/)) | Audio only, no MIDI input, upload and wait. | Not applicable live; a cross-check for TikTok audio at most. |
| Live grand-staff viewers (Tonality Grand Staff AU, Midiano) | Incoming notes on a grand staff ([Loopy Pro forum, 2022-2024](https://forum.loopypro.com/discussion/51680/an-app-that-converts-midi-to-sheet-music-notes-in-realtime)) | No rhythm, no bars: what `piano.js` draws today. | Shows the gap this lane fills. |

### 4.2 Research and libraries

| Work | What it does | Numbers | Limits | Use for us |
|---|---|---|---|---|
| **PM2S**, Liu et al., ISMIR 2022 ([paper](https://www.turing.ac.uk/sites/default/files/2022-09/midi_quantisation_paper_ismir_2022_0.pdf), [code, MIT](https://github.com/cheriell/PM2S)) | A CRNN predicts per note whether it is on a beat and on a downbeat, plus tempo, quantized onsets, note values, key and time signatures, and hand part | MV2H total 87.9 against Finale 65.0 and MuseScore 54.0; metrical alignment Fme 61.7 against 9.9 and 15.3 | The authors call Fme still unsatisfactory; typical errors are half or double tempo and missing or extra beats. Offline; PyTorch. | Offline yardstick for the clean copy (Q5). The note-level "on a beat?" framing fits T2.2. |
| **MIDI2ScoreTransformer**, Beyer and Dai, ISMIR 2024 ([arXiv 2410.00210](https://arxiv.org/abs/2410.00210), [code](https://github.com/TimFelixBeyer/MIDI2ScoreTransformer)) | Seq2seq from performance MIDI to MusicXML: rhythm, staff, voice, stems, spelling, grace notes, trills | MUSTER average error 11.30 against an HMM pipeline 13.95, MuseScore 23.35 and Finale 20.64 | 512-note context in overlapping chunks; offline; trained on classical ASAP; repo licence not stated on its page | The quality ceiling; a reference only. |
| **Beat-conditioned T5 quantizer**, Wachter, Murgul and Heizmann, 2026 ([arXiv 2604.22290](https://arxiv.org/abs/2604.22290)) | Given beats, pre-quantizes to 12 sub-beats per beat, then a transformer writes onsets and values per measure | Onset F1 97.3%; note values 83.3% (ASAP) | Needs beat annotations; runtime and code not stated | **Validates our split**: get beats first (the ladder), then quantize per beat on a 12-per-beat grid. |
| **Beat and downbeat tracking in performance MIDI**, Murgul and Heizmann, SMC 2025 ([arXiv 2507.00466](https://arxiv.org/abs/2507.00466)) | Transformer from MIDI to beats and downbeats | Beats the HMM and deep baselines on A-MAPS, ASAP and others | Offline; no code stated | A v2 rung-4 idea; offline beats for the clean copy. |
| **Merged-output HMM**, Nakamura, Yoshii and Sagayama, 2017 ([arXiv 1701.08343](https://arxiv.org/abs/1701.08343)) | Rhythm transcription modelling loosely synchronized voices | 12+ points better on polyrhythmic performances | Offline Viterbi | Voices may drift apart in time: quantize per voice after T5 when hands disagree (v2). |
| **Cemgil and Kappen**, 1999-2003 ([NeurIPS](http://papers.neurips.cc/paper/1999-tempo-tracking-and-rhythm-quantization-by-sequential-monte-carlo.pdf)) | Tempo tracking and quantization as filtering and MAP estimation | n/a | Older, but the right shape for live use | T2.2 v2 particle filter; T3 cost form. |
| **Desain and Honing** connectionist quantizer ([paper](https://repository.ubn.ru.nl/bitstream/handle/2066/74817/1/74817.pdf)) | Nudges adjacent intervals toward integer ratios | n/a | Measured weak on his playing (real 32-48% against shuffled 34-41% near simple ratios) | Not used. |
| **Cluster and Separate**, Foscarin et al., ISMIR 2024 ([arXiv 2407.21030](https://arxiv.org/abs/2407.21030), [MIT](https://github.com/CPJKU/piano_svsep)) | GNN: chords, voices and staves, including cross-staff and homophonic voices | Voice F1 96.6 (J-Pop), 89.9 (romantic) | Needs quantized input; offline | Clean-copy reference for T5. |
| **EngravingGNN**, Karystinaios, Foscarin and Widmer, 2025 ([arXiv 2509.19412](https://arxiv.org/abs/2509.19412)) | Multi-task: voice, staff, spelling, key signature, stems, 8va, clef, durations | J-Pop: staff 97.6%, spelling 96.3%, key 80.6%, clef 96.2%. Romantic: staff 91.9%, key 50.5% | Quantized input; no ties across noteheads; removes grace notes | Target numbers for T5 and T7; key signatures are hard for everyone. |
| **Pitch spelling with local keys**, Bouquillard and Jacquemard, TENOR 2024 ([arXiv 2402.10247](https://arxiv.org/abs/2402.10247)); **PKSpell** 2021 ([arXiv 2107.14009](https://arxiv.org/abs/2107.14009)) | DP spelling with global and local keys; an RNN speller | 98.2% overall, 99.5% Bach; global key 93.0% | Measure boundaries given; classical corpora | T7 yardstick. Our chord-aware `spellInKey` should be compared on fixtures. |
| **partitura** ([docs](https://partitura.readthedocs.io/en/latest/modules/partitura.html)) | ps13 spelling, voice estimation, Krumhansl key, simple quantization, MusicXML and MIDI I/O. Apache-2.0, 1.9.0 (per `ultimate-practice-tool-2026-09-14/open-source.md`) | n/a | Python; offline | An offline spelling and voice yardstick; MusicXML round-trip check. |
| **music21** ([MIDI translate](https://music21.org/music21docs/moduleReference/moduleMidiTranslate.html)) | Quantizes MIDI to 16ths or triplet eighths by default | n/a | Nearest-grid under a known tempo | A MusicXML validity check only. |
| **Rubato**, Tamer et al., May 2026 ([arXiv 2605.24291](https://arxiv.org/abs/2605.24291)) | Audio to timestamped score in one pass | Lower notation error than cascades, including oracle-MIDI variants | Audio in; CC BY-NC-ND; offline | Confirms that end-to-end timestamped scores are the frontier; not usable here. |
| **A Dual Evaluation for Music Transcription**, Aug 2026 ([arXiv 2608.04511](https://arxiv.org/abs/2608.04511)) | Scores notation similarity and playback similarity separately | MIDI2ScoreTransformer leads on notation, MuseScore on playback; MUSTER onset error tracks playback preference better than notation | No human readability study | Our receipts keep both sides: notation proxies (SR8) and faithfulness (SR5). |
| **MV2H** ([code](https://github.com/apmcleod/MV2H)) | Joint metric: pitch, voice, meter, value, harmony | n/a | Needs a ground-truth score | Scores the fixture corpus (SR5). |
| **Real-time transcription with symbol-level score following**, Peter, Hu and Widmer, SMC 2025 ([arXiv 2505.05078](https://arxiv.org/abs/2505.05078)) | Tracks a performance against a known score live | Better precision and robustness than audio-only following | Needs a score | Later: follow along a *saved* clean copy of his own piece. |

**Reading of the survey.**

1. Live notation that works needs the beat handed to it (a click, or given annotations). The best systems infer beats
   offline with learned models and still miss often.
2. No surveyed system is pedal-aware in how it writes durations, beyond "fill gaps".
3. We have beat sources the others lack: the jam tempo map, the song listener, and a tap and "This is 1" on the same
   page. We also keep the full log, which allows a clean copy any time.

So the live transcriber can stay small, classical and explainable, while the clean copy aims at the research numbers.

---

## 5. Module shape (proposal; nothing written)

| File (new, pure, node-testable) | Does | Depends on |
|---|---|---|
| `arsenal/web/piano/score/onsets.js` | T1 groups, rolls, grace notes, runs | none |
| `arsenal/web/piano/score/beat.js` | T2 ladder, tracker, confidence, free time, rough BPM | `tempomap.js` (read-only import); song-listener state as input |
| `arsenal/web/piano/score/quantize.js` | T3 per-beat division, durations, rests | `beat.js` output |
| `arsenal/web/piano/score/measures.js` | T4 bars, ties, dots, beams, tuplets, pickups | `quantize.js` |
| `arsenal/web/piano/score/hands.js` | T5 DP split, voices, clef, 8va | none |
| `arsenal/web/piano/score/spell.js` | T7 spelling, key signature, accidentals | `nashville.js` (`spellInKey`, key tracker state), the reader (`chordread.js` once TN lands) |
| `arsenal/web/piano/score/marks.js` | T6 and T8 pedal, dynamics, accents, words, chord symbols | `harmony.js` windows |
| `arsenal/web/piano/score/settle.js` | T9 bar states, revisions, forward-only corrections | all of the above |
| `arsenal/web/piano/score/musicxml.js` | T10 export | score JSON |
| `arsenal/web/piano/score/index.js` | `createTranscriber({ spell, harmony, beatSources })` | the modules above |

```js
export const SCORE_API = "arsenal.piano.score/v0";
createTranscriber({ keyView, reader, harmony, beatSources, options }) -> {
  noteOn(midi, vel, t, source), noteOff(midi, t), soundEnd(midi, t, by), pedal(down, value, t),  // Daniel's sources only
  tap(t), thisIsOne(t), setMeter([n, d]), setOptions({ pedalled: "played" | "sounding", heldBass, freeTime, swing }),
  tick(t) -> { bpm: { value, steady, source }, changed: [measureN...], measures /* view */ },
  clean(events) -> Score   // offline, full lookahead, same code under node
}
```

- **Integration into `piano.js`** (feeding events, drawing the strip) waits until the jam build releases the file. It
  is the display lane's slice.
- **Offline runs** use a node CLI beside `practice_theory.mjs` (`arsenal/score_cli.mjs`, a proposal) over
  `state/arsenal/performance/<session>/events.jsonl`.

---

## 6. Build slices (proposal)

| Slice | Content | Receipts | Needs |
|---|---|---|---|
| **SM0** | Fixture corpus: about 30 short scores in his idioms (bass plus a 10th line; pedalled broken 8ths; a rolled chord; a triplet fill; dotted rhythm; a tie over the bar; syncopation; a half-step key change; the left hand above C4; a grace note; free-time phrases), each rendered to performance events with tempo curves (±10%, rit., fermata), onset jitter σ 15-45 ms, chord spread 0-35 ms, bass lead 0-60 ms, rolls 50-120 ms, pedal lag 150 ms | SR1: generator deterministic by seed; SR2: fixtures frozen after SM0 (changes go through the conductor) | none |
| **SM1** | `onsets.js` | SR3: roll, grace and run precision and recall of at least 0.9 on fixtures | SM0 |
| **SM2** | `beat.js`: ladder rungs 3-5, rough BPM, free time | SR4: BPM within 4% of the fixture tempo (octave included) on 95% of steady fixtures; free time entered on every free fixture; no free time on steady fixtures | SM0 |
| **SM3** | `quantize.js` and `measures.js` | SR5: onset and duration error per note (MUSTER-like) and MV2H meter and value on fixtures, reported with the beat given (oracle) and inferred; SR6: settle churn at 4 beats of at most 6% on S1-S12 (measured today 5.7% with a simpler tracker) | SM2 |
| **SM4** | `hands.js` | SR7: staff accuracy of at least 95% and voice F1 of at least 0.9 on fixtures | SM0 |
| **SM5** | `spell.js` | SR9: spelling identical to `spellForKey` chips on every chord tone of the S1-S12 chord events; key signature changes at most 1 per 30 s of key area | TN reader, or `Theory.detect` today |
| **SM6** | `marks.js` | SR8 readability proxies on S1-S12: median at most 1 tuplet bracket, at most 2 ties and at most 2 voices per staff per bar; pedal marks at most 1 per beat; dynamics at most 3 per minute | SM3, SM4 |
| **SM7** | `settle.js` plus the node CLI for clean copies of all sessions | SR10: settled measures never change across a full replay; flicker per minute reported, calibrated per D14; SR11: clean and live copies of the same session stored side by side | SM3-SM6 |
| **SM8** | `musicxml.js` | SR12: every clean copy passes a MusicXML 4.0 schema check (offline XSD, if vendoring is OK) and round-trips through music21 or partitura where installed | Q5 |
| **SM9** | Rung 1 (jam tempo map) and rung 2 (song beat) | SR13: during a jam run, bar lines within 2 ms of `tempomap.js` bars; SR14 (drill with Daniel present, dated receipt): three clips, his verdict on readability per bar | J9, AL phases, display lane |

---

## 7. Risks and unmeasured facts

- **Free-time share is estimated, not measured.** "No pulse in 46-87% of 8 s windows" counts windows with pauses. The
  real share of *playing* time in free time needs SM2's detector on the logs.
- **Downbeat inference is unmeasured.** Bass-plus-harmony-change as a bar cue is a hypothesis for his style. Without
  "This is 1", pickups and bar phase will be wrong often; forward-only correction keeps that from flickering.
- **The churn simulation's reference is not ground truth**, and its tracker started from the session's pulse. Real
  churn from a cold start will be higher in the first bars of each phrase.
- **Velocity bands are absolute.** A different keyboard or velocity curve moves every mark.
- **Grace-note and roll rules** can mislabel fast ornaments and hand asynchrony; both need fixture recall and a look
  by Daniel.
- **The lowest-key share** in S10 and S11 is likely a counting artifact (re-strikes without a logged release in my
  pairing), and is excluded from the ranges above.
- **The hand DP costs are guesses** until SR7. His 10ths make hand span ambiguous.
- **Compute is not a risk.** Every stage is per onset over a window of at most a bar or two, far under a frame. The
  clean copy of a 30-minute session is a node batch.

---

## 8. What composes with other lanes

- **Chord reader and harmony window** (theory-nextgen TN). T7 spells through the reader; T2.4 and T6 use window
  boundaries; chord symbols above the staff are the reader's names. No second chord engine.
- **Key tracker.** Key signatures follow the tracker's non-provisional key, with the jam key and song key precedence
  as in the practice-along plan 2.4.
- **Jam tempo map and log timebase** (jam spec 11.2). Rung 1 is exact, and the log's `meta.t0_perf_ms` and `page_id`
  already give the alignment.
- **Song listener** (practice-along). Rung 2 consumes `state().beat`, and the `steady`/`loose`/`lost` words are shared.
- **Display lane.** It draws measures from the score JSON view. This lane recommends fixed beat widths live (T9) and
  keeping the current sounding-notes staff as the instant layer. The existing overlay already has Bravura SMuFL
  glyphs, ledger lines and accidental stacking in `drawStaff`, and a Canvas2D layer inside the WebGL canvas is what
  REC captures.

---

## 9. Validation without Daniel present, and with him

- **Offline, no installs:** fixtures (SM0) against ground truth; S1-S12 for churn, flicker, free-time share and
  readability proxies; spelling agreement with the page's chips.
- **Optional, needs installs (Q5):**
  - run PM2S or MIDI2ScoreTransformer on the clean copy's MIDI and on fixture performances for a third opinion;
  - use MV2H (Java) or pyMV2H for fixture scoring.
- **Drill (SR14):** Daniel plays three short takes: one with a jam loop, one tapped, one free. He sees the live strip
  and then the clean copy, and marks each bar readable or not. Dated receipt, or presume it broken.

---

## 10. Questions and decisions for Daniel

| # | Question | Options | Recommended default |
|---|---|---|---|
| **Q1** | When there is no steady beat, what should the page write? | (a) free-time notation: no rhythm claimed, notes placed by time, bar lines at chord changes, `freely`; (b) force a rhythm at the rough BPM, marked `rubato`; (c) (a) live and (b) in the clean copy | **(c)** |
| **Q2** | Pedalled notes: as your hands played them, or as long as they rang? | A: as played, plus pedal marks; B: as sounding (long notes, many ties); plus the held-bass option (bass written long, the line above as played) | **A plus held bass** |
| **Q3** | Which beat counts as the BPM? | His felt quarter in 55-110, measured at 74-102 on his sessions; tap to correct; stored per song when following one | **55-110 quarter** |
| **Q4** | Does the score strip go into the TikTok recording? | Display lane's call; this lane only notes the strip trails one bar behind | (display lane) |
| **Q5** | Vendoring and installs | A notation renderer for a full-page score view: **VexFlow 5.0.0** (MIT, March 2025, Canvas or SVG, draws per measure; [repo](https://github.com/vexflow/vexflow), [releases](https://github.com/vexflow/vexflow/releases)), **Verovio** (LGPL, about 1.2 MB WebAssembly build, best engraving, full re-layout; [book](https://book.verovio.org/installing-or-building-from-sources/javascript-and-webassembly.html)), **OpenSheetMusicDisplay** (BSD-3, VexFlow-based MusicXML, full renders only; [repo](https://github.com/opensheetmusicdisplay/opensheetmusicdisplay)), **abcjs** (MIT, ABC text; [repo](https://github.com/paulrosen/abcjs)); or **none**: extend the page's own Canvas2D engraver for the live strip and export MusicXML for MuseScore. Offline references: PM2S (MIT) and MIDI2ScoreTransformer (PyTorch installs). | **No vendoring for the live strip** (own engraver, REC-safe, matches the overlay). Decide on VexFlow for a later full-page view. Installs only if the clean copy's receipts need a third opinion. |
| **Q6** | Meter and swing | 4/4 default, auto 3/4 and 12/8; swing written as straight eighths plus `swing`, or as triplets | **Auto meter on; swing off until asked** |

---

## Sources

Products and documentation:

- ScoreCloud [FAQ](https://scorecloud.com/support/) and [learn page](https://scorecloud.com/learn/best-music-transcription-software/)
- MuseScore [MIDI import handbook](https://musescore.org/en/handbook/2/midi-import) and [issue 28402](https://github.com/musescore/MuseScore/issues/28402)
- Dorico: [MIDI recording docs](https://www.steinberg.help/r/dorico-se/5.1/en/dorico/topics/write_mode/write_mode_midi_recording/write_mode_midi_recording_notes_t.html), [recording tips](https://blog.dorico.com/2019/02/tip-how-to-get-great-results-with-midi-recording/), [Scoring Notes article](https://www.scoringnotes.com/tips/real-time-midi-recording-in-dorico/), [accidental duration rules](https://archive.steinberg.help/dorico_se/v3.5/en/dorico/topics/notation_reference/notation_reference_accidentals/notation_reference_accidentals_duration_rules_r.html)
- Sibelius: [product page](https://www.sibelius.com/products/sibelius/acorninfo.html), [Flexi-time tips](https://www.scoringnotes.com/tips/results-flexitime/)
- Logic Pro: [interpretation](https://support.apple.com/guide/logicpro/change-note-syncopation-and-interpretation-lgcp8535f288/10.5/mac/10.14.6), [display quantize](https://logicpro.skydocu.com/en/view-and-edit-music-notation/edit-notes-in-the-score-editor/quantize-the-timing-of-notes/)
- [Klangio Transcription Studio](https://klang.io/transcription-studio/)
- [Loopy Pro forum thread](https://forum.loopypro.com/discussion/51680/an-app-that-converts-midi-to-sheet-music-notes-in-realtime)
- [LilyPond piano notation](https://lilypond.org/doc/v2.24/Documentation/notation/piano)
- [MusicXML `<arpeggiate>`](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/arpeggiate)

Research:

- [PM2S paper](https://www.turing.ac.uk/sites/default/files/2022-09/midi_quantisation_paper_ismir_2022_0.pdf) and [code](https://github.com/cheriell/PM2S)
- [MIDI2ScoreTransformer](https://arxiv.org/abs/2410.00210) and [code](https://github.com/TimFelixBeyer/MIDI2ScoreTransformer)
- [Beat-conditioned T5 quantizer, arXiv 2604.22290](https://arxiv.org/abs/2604.22290)
- [Beat and downbeat tracking in MIDI, arXiv 2507.00466](https://arxiv.org/abs/2507.00466)
- [Merged-output HMM, arXiv 1701.08343](https://arxiv.org/abs/1701.08343)
- [Cemgil and Kappen, NeurIPS 1999](http://papers.neurips.cc/paper/1999-tempo-tracking-and-rhythm-quantization-by-sequential-monte-carlo.pdf)
- [Desain and Honing quantizer](https://repository.ubn.ru.nl/bitstream/handle/2066/74817/1/74817.pdf)
- [Cluster and Separate](https://arxiv.org/abs/2407.21030) and [code](https://github.com/CPJKU/piano_svsep)
- [EngravingGNN, arXiv 2509.19412](https://arxiv.org/abs/2509.19412)
- [Pitch spelling with local keys, arXiv 2402.10247](https://arxiv.org/abs/2402.10247)
- [PKSpell, arXiv 2107.14009](https://arxiv.org/abs/2107.14009)
- [partitura docs](https://partitura.readthedocs.io/en/latest/modules/partitura.html)
- [music21 MIDI translate](https://music21.org/music21docs/moduleReference/moduleMidiTranslate.html)
- [Rubato, arXiv 2605.24291](https://arxiv.org/abs/2605.24291)
- [A Dual Evaluation for Music Transcription, arXiv 2608.04511](https://arxiv.org/abs/2608.04511)
- [MV2H](https://github.com/apmcleod/MV2H)
- [Real-time score following, arXiv 2505.05078](https://arxiv.org/abs/2505.05078)
- [Swingogram, JNMR 2017](https://www.tandfonline.com/doi/full/10.1080/09298215.2017.1367405)

Renderers: [VexFlow](https://github.com/vexflow/vexflow), [Verovio](https://book.verovio.org/installing-or-building-from-sources/javascript-and-webassembly.html), [OpenSheetMusicDisplay](https://github.com/opensheetmusicdisplay/opensheetmusicdisplay), [abcjs](https://github.com/paulrosen/abcjs).

Repository: `arsenal/web/piano.js` (`drawStaff`, SMuFL glyphs, `spellForKey`), `arsenal/web/piano/nashville.js`
(`spellInKey`, `createKeyTracker`), `arsenal/web/piano/tempomap.js`, `arsenal/performance.py` (event kinds,
`ONSET_MERGE_MS`, `key_areas`), `research/in-flight/practice-along-2026-09-14/`,
`research/in-flight/piano-theory-nextgen-2026-09-14/theory-nextgen-spec.md`,
`research/in-flight/piano-jam-2026-09-14/jam-spec.md` (11.2).
