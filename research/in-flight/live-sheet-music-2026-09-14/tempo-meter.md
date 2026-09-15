# Lane: tempo, beat and meter from expressive MIDI

| | |
|---|---|
| Date | 2026-09-14 |
| Status | Research and design only. No arsenal code edited, no servers, no browsers, nothing installed or downloaded, no logins. |
| Question (Daniel, verbatim) | "what if we keep a rough estimate of bpm and make it possible to save the notes i am playing into something that can render into sheet music with correct notation in real time, I wonder if we can make that happen!" |
| This lane | Estimating a rough, steady-enough BPM, a beat grid, bar lines, a meter (2/4, 3/4, 4/4, 6/8, 12/8), pickups, pauses, and when to say "free time", live, from his rubato, pedalled two-hand MIDI with no click. It also covers using the jam tempo map or the song listener's beat when either exists. |
| Sibling lanes | `transcription.md` (T2 beat-source ladder, T3 quantization, settle rule) consumes this lane's output. `rendering-formats.md` 5.1 (`Take.tempo`, `Take.time`) renders it. This file refines their T2 with measurements, and flags two places where the data disagrees with them (sections 6.4 and 6.7). |
| Grounded in | `arsenal/web/piano/tempomap.js` and `arsenal/jam/tempomap.py` (exact bar clock), `arsenal/web/piano/deck.js` (tap: 4 taps, median, 40-200 bpm), `arsenal/web/piano/groove.js` (`DEFAULT_BPM` 66), `arsenal/web/piano.js` (`onMidiMessage`, `noteOn` logs `clock()` at handler time), `arsenal/performance.py` (event schema), `research/in-flight/practice-along-2026-09-14/live-key-bpm.md` and `practice-along-plan.md` (listener `beat {periodMs, nextBeatPerf, phaseConf, barPhase}`), `research/in-flight/piano-theory-nextgen-2026-09-14/theory-nextgen-spec.md` (harmony windows). |
| Prototype | Scratch only, untracked: `C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/sheet/` (`tracker.mjs`, `sweep3.mjs`, `sessions2.mjs`). Node, causal, run on synthetic performances with ground truth and read-only on the practice log. Only counts, intervals and rhythmic statistics are reported here. Sessions are named S1..S13 in directory order as of the run; S13 (0.5 min) was being recorded during it, and S8 (3 s) is too short. |

---

## 1. Short answer

1. **A rough BPM is easy. A trustworthy bar grid from his notes alone is not.**
   - On the sessions, the tracker's locked tempo has medians of **70-94 bpm** (p25-p75 inside 52-102). That matches his 60-110 feel and the transcription lane's 74-102.
   - But his beat-to-beat tempo wobble while locked is a median of **3.2-6.7%**, p90 **13-31%**.
   - The prototype measures **4.1% / 20.5%** on synthetic "strong rubato" (ritardandos, fermatas, ±10% phrase swell). There its beat F-measure is 0.46 and its downbeat F-measure **0.17**, against 0.86 / 0.91 on metronomic synthetic playing.
   - So bar lines inferred from his playing alone will often be wrong. Notation must use a real beat whenever one exists, and must say "free time" honestly.
2. **The beat-source ladder is right** (`transcription.md` T2.1), in this order:
   1. the jam tempo map;
   2. the song listener's beat;
   3. his taps plus "This is 1";
   4. the inferred beat;
   5. free time.

   This lane adds the inferred rung's algorithm, its confidence, and the numbers that justify putting it that low.
3. **The inferred rung: IOI induction plus a small set of competing beat hypotheses**, not a single oscillator.
   - It is the Dixon BeatRoot architecture, run causally.
   - The main failure on his playing is the **beat level**:
     - ×1.5 flips (quarter against dotted quarter) run at 0.2-3.4 per minute across sessions;
     - ×2 flips run at 0-0.4 per minute.
   - Only a tracker that keeps runner-up hypotheses can offer cheap ÷2 / ×2 / "in 2 or in 3" fixes.
   - Tuned on held-out synthetic seeds, the prototype gets:
     - tempo within 8% on **71%** of readouts (Acc1);
     - a related tempo on **82%** (Acc2, which also accepts ×2, ½, ×3, ⅓, ×1.5 and ⅔);
     - octave or level errors on **10.5%**;
     - beat F **0.64** at a 70 ms tolerance.
4. **Meter: suggest it, do not impose it.**
   - Default 4/4. One tap sets 3/4, 6/8, 12/8 or free.
   - An automatic suggestion appears only after a large, stable margin.
   - On synthetic playing, the tatum-level meter picks the right meter **81%** of the time (89% metronomic, 93% mild rubato, 63% strong rubato).
   - On his sessions the label follows whatever tie-break prior is set:
     - a small 6/8 preference makes **6/8 win 58-100%** of locked time;
     - without it, 4/4 and 12/8 split the time and the label changes 3-14 times a minute.
   - The evidence for meter in his notes is too weak to act on without him.
5. **Confidence must come from periodicity strength, not from grid fit.**
   - On random onsets, the share of notes landing on the tracker's grid has a median of 0.62, the same as strong rubato (0.60). The tracker bends to fit random notes.
   - The peak ratio of the IOI histogram does separate them: random onsets have p90 3.2; mild rubato has p10 4.1; metronomic has p10 6.9.
   - This contradicts the confidence rule in `transcription.md` T2.2/T2.5, and needs reconciling (section 6.7).
   - By this measure his sessions are steady **0-12%**, loose **13-69%** and free **19-85%** of the time.
6. **Bars must lag.**
   - Live beats drive a cursor at lag 0.
   - Notation uses beats settled after 2-4 more beats. Misses are interpolated between onset-anchored beats. Bars freeze after 4 beats, as `transcription.md` T2 measured (5.7% relabel churn).
   - A non-causal "tidy" pass after the take can redo the whole tempo map.
7. **Log the MIDI event's own timestamp.**
   - `noteOn` stamps `clock()` inside the handler, so a busy render frame adds delay to every note.
   - Web MIDI gives each message a `timeStamp`: the time the message "was received by the system" ([W3C Web MIDI](https://www.w3.org/TR/webmidi/)).
   - It is a small change for a later slice, not tonight. Measure the difference in a drill first (section 8).
8. **No library is needed for v1.**
   - The strong symbolic models are all **offline**, trained on classical piano, and still weak on downbeats:
     - PM2S (MIT, PyTorch);
     - the SMC 2025 MIDI transformer;
     - MIDI2ScoreTransformer;
     - met-align (MIT, Java).
   - On ASAP, downbeat F is 14% for PM2S and 28% for the SMC 2025 transformer.
   - As references for an offline tidy pass they need Daniel's OK, because installing them is a download (D4).

---

## 2. What exists today

| Where | What it does | What it means here |
|---|---|---|
| `tempomap.js` / `tempomap.py` (twins) | Segments `{from_bar, bpm, epoch_ms, def_version, def_from_bar}`. `barAt`, `tEpoch`, `sessionTms` (jam spec 11.2). The meter is an integer `beats_per_bar`. | Rung 1 is exact. There is no notion of beat unit or compound meter: a 6/8 jam loop would be `beats_per_bar` 6 at the eighth or 2 at the dotted quarter (open question 3). |
| `deck.js` tap | 4 taps, median gap, 40-200 bpm, reset after 2 s | Rung 3 reuses this. A tap within about 8% of a live hypothesis should select that hypothesis rather than replace it. |
| `groove.js` | `DEFAULT_BPM` 66, ballad under 80 | His loops live at these tempi, which supports a prior centred near 80. |
| Song listener (`live-key-bpm.md` 5, plan 2.2) | `beat {periodMs, nextBeatPerf, phaseConf, barPhase}`. A bar phase exists only after "This is 1". Latency-corrected. | Rung 2. Map `nextBeatPerf` into session `t_ms` with the log's `t0_perf_ms`. |
| `piano.js` `onMidiMessage` → `noteOn` → `clock()` | The log time is the page clock read inside the handler, not `ev.timeStamp` | Adds main-thread dispatch delay to every onset (section 1.7). The prototype shows the beat level is sensitive to ±25 ms of jitter (section 4.3). |
| `performance.py` | Event kinds `on`, `off`, `pedal`, `chord`, `sound_end`; integer `t_ms` | Everything this lane needs: onsets, velocities and pedal changes. |
| `transcription.md` T2 | Ladder; Large-Kolen update (phase 0.3, period 0.1); 4/4 default; 3/4 from harmony windows; 12/8 at 75% triple; settle 4 beats; free time when confidence < 0.5 | Section 6 keeps the ladder, the default and the settle rule. It proposes a multi-hypothesis tracker and a periodicity-based confidence instead, with the evidence. |
| `rendering-formats.md` 5.1 | `Take { tempo: {bpm, confidence, map?}, time: {beats, beatType} \| "free", ... }`; tape (proportional) and ribbon (metric) views | Section 6.1 fills these fields. |

---

## 3. Survey

### 3.1 Research on symbolic (performance-MIDI) beat, meter and score

| Work | Input and method | Online? | What it reports | Licence and state | Use here |
|---|---|---|---|---|---|
| **PM2S**, Liu, Kong, Morfi, Benetos, ISMIR 2022 ([paper](https://www.turing.ac.uk/sites/default/files/2022-09/midi_quantisation_paper_ismir_2022_0.pdf), [code](https://github.com/cheriell/PM2S)) | Note sequence → CRNN (3 conv, 2 bi-GRU) predicts "in-note" beats, then dynamic programming fills beats with no onset. Also predicts time-signature numerator (classes 0, 2, 3, 4, 6), key signature, hand, note values. | No (bidirectional) | Beat F 86.2, downbeat F 69.8 with a tempo output, against 66.9 / 57.6 for a pianoroll CRNN + DBN baseline (their Table 4). MV2H metrical score 61.7, against **9.9 for Finale and 15.3 for MuseScore**; they attribute MuseScore's low score to one constant tempo for the whole piece. | MIT; PyTorch 1.12 | Offline reference for a tidy pass, only after an install decision. Its in-note beat idea ("which onsets are beats?") matches our agents' hit test. |
| **Murgul & Heizmann**, SMC 2025 ([arXiv 2507.00466](https://arxiv.org/abs/2507.00466)) | MIDI tokens → T5 encoder-decoder → beat and downbeat tokens; beam search | No | On ASAP, beat F **78.1** and downbeat F **27.8**. PM2S on the same split: 83.0 / **14.1**. The Nakamura HMM: 47.7 / 13.4. Audio Beat This!: 76.3 / 61.2. On A-MAPS: 98.0 / 76.6. Segment length trades off: 10 s is best for beats (96.0), 5 s for downbeats (65.5). 70 ms tolerance, first 5 s skipped. | Paper | **Even the best offline MIDI models find downbeats hard on real expressive piano.** Shorter context helps downbeats; long context helps beats. |
| **MIDI2ScoreTransformer**, Beyer & Dai, ISMIR 2024 ([arXiv 2410.00210](https://arxiv.org/abs/2410.00210), [code](https://github.com/TimFelixBeyer/MIDI2ScoreTransformer)) | End-to-end performance MIDI → score tokens; the beat is implicit | No | Beats HMM pipelines and earlier deep models on MUSTER metrics | Code on GitHub | Offline reference only. |
| **Wachter, Murgul, Heizmann**, April 2026 ([arXiv 2604.22290](https://arxiv.org/abs/2604.22290)) | Quantization **given** beat and downbeat annotations | No | On ASAP, onset F1 97.3% and note-value accuracy 83.3%; handles unseen 6/8 and 12/16 | Paper | **Once the beats are known, notation is largely solved. The beat is the bottleneck,** which is why the ladder puts known beats first. |
| **met-align**, McLeod & Steedman, ISMIR 2018 ([paper](https://apmcleod.github.io/pdf/ISMIR_Meter.pdf), [code](https://github.com/apmcleod/met-align)) | HMM whose state is one bar of tatums. Meters with 2, 3, 4, 6, 9, 12 as numerator. Anacrusis as a count of tatums (a whole number of sub-beats). Tempo change is a Gaussian on the **proportional** change (Weber's law). Rhythm grammar (LPCFG). Beam Viterbi, beam 200 by default. | Incremental | Metrical F-measure: **metronomic 80.5, against 67.7 for Temperley; live performance 56.5, against 47.6** (13 live pieces). It cannot handle time-signature changes. | MIT; Java | Its structure is the model for section 6.4: tatum → sub-beat → beat → bar, a proportional tempo penalty, and a whole-sub-beat anacrusis. Their live score of about 57 is the honest ceiling to expect for automatic meter. |
| **Temperley**, unified probabilistic model, JNMR 2009 ([pdf](https://davidtemperley.com/wp-content/uploads/2015/11/temperley-jnmr09.pdf)); *Music and Probability* ([MIT Press](https://direct.mit.edu/books/monograph/2326/Music-and-Probability)) | Joint meter, harmony and stream segregation | Offline | McLeod notes its harmony component rescues isochronous passages where onsets carry no metrical cue | Book and paper | **Harmony is a meter cue.** Use harmony-window starts as the accent (6.4). |
| **Nakamura et al.**, merged-output HMM rhythm transcription, 2017 ([arXiv 1701.08343](https://arxiv.org/abs/1701.08343)) | HMM with separate voices; tempo variation | Offline | The HMM baseline in the SMC 2025 table (above) | Paper | Background; confirms voice-aware rhythm is needed for two hands. |
| **Dixon, BeatRoot**, JNMR 2001 / 2007 ([2007 evaluation](http://www.eecs.qmul.ac.uk/~simond/pub/2007/jnmr07.pdf)) | Clusters inter-onset intervals into tempo hypotheses, then runs multiple agents, each a (tempo, phase) hypothesis, scored by the salience of the onsets it explains | Causal in spirit | Designed for expressive performance and used for years in performance-timing studies | Paper | **The prototype's architecture** (section 4). |
| **Cemgil, Kappen, Desain, Honing**, JNMR 2001 ([pdf](https://www.mcg.uva.nl/mcg-2023/papers/mmm-27.pdf)) | Tempo as a hidden state estimated from performance MIDI by a Kalman filter over a "tempogram" | Filter plus smoother | Background | Paper | The offline tidy pass is a smoother of this kind. `transcription.md` T2.2 already cites the SMC particle filter as v2. |
| **Large & Kolen** adaptive oscillators (review: [Frontiers 2023](https://www.frontiersin.org/journals/computational-neuroscience/articles/10.3389/fncom.2023.1151895/full)) | Phase and period coupling to onsets | Yes | Cognitive model | Paper | This is the single-oscillator update in `transcription.md` T2.2. It cannot hold a runner-up tempo (6.2). |
| **Real-time PLP**, Meier, Chiu, Müller, TISMIR 2024 ([article](https://transactions.ismir.net/articles/10.5334/tismir.189), [code](https://github.com/groupmm/real_time_plp)) | Predominant local pulse from an onset novelty curve, with lookahead to zero latency and explicit confidence controls | Yes | Audio (microphone or WAV) | MIT; Python 3.12 | An idea to test in v2: PLP runs on any novelty curve, and a velocity-weighted MIDI onset train is one. |
| **Carnovalini & Rodà**, Audio Mostly 2019 ([arXiv 2208.14717](https://arxiv.org/abs/2208.14717)) | Real-time tempo and meter tracking for rhythmic improvisation | Yes | Reports detection "under certain settings" | Paper | Confirms the task is open for free input. |
| **Moelants**, preferred tempo ([Semantic Scholar](https://www.semanticscholar.org/paper/Preferred-tempo-reconsidered.-Moelants/b0db06a5a8b2c1942afff5c317c5f6da55a7dcf7)) | Population tapping resonance near 120 bpm | n/a | n/a | Paper | A generic prior would push his 60-80 bpm ballads to double time. Centre **his** prior on his feel (80) instead, and let one tap or stored choice override it. |

### 3.2 Practical tools

| Tool | What it does with unclicked MIDI | Lesson |
|---|---|---|
| Logic Pro Smart Tempo (10.4.2+) ([Apple](https://support.apple.com/en-us/102165), [Sound On Sound](https://www.soundonsound.com/techniques/logic-pro-using-smart-tempo)) | Records MIDI or audio without a metronome. "Adapt" builds the project tempo map from the free performance, so later parts quantize to his grid. | The product shape is right: **a tempo map follows the player, rather than the player following a grid.** It is offline and editable afterwards. |
| MuseScore 3 MIDI import, "human performance" ([handbook](https://musescore.org/en/handbook/3/midi-import)) | Automatic beat tracking to find bars in unaligned MIDI, plus a checkbox to halve the measure count when tracking finds bars twice too often. MuseScore 4 dropped the import panel ([forum](https://musescore.org/en/node/363436)). | **Even a shipping product exposes the ×2 error as a user button.** Forum users describe click-free takes as close to unusable after import ([forum](https://musescore.org/en/node/321251)). |
| Dorico real-time MIDI recording (since 2.2) ([Scoring Notes](https://www.scoringnotes.com/tips/real-time-midi-recording-in-dorico/)) | Records MIDI in real time into notation, with a tempo track (per the review; whether it infers tempo from a click-free take was not checked here) | Notation apps lean on a known tempo. That is our rungs 1-3. |

---

## 4. The prototype and what it measured

### 4.1 The tracker (causal, 250 ms clock)

1. **Onset groups.**
   - Notes within 40 ms of a group's first note join it.
   - Salience = √Σ(0.4 + vel/127), plus 0.5 if the lowest note is at or below G3.
   - A group is usable 40 ms after its first note.
   - His rolls fit easily: within a multi-note group the spread is a median of 12-20 ms and p90 30-38 ms on every session, and 26-40% of groups have 2+ notes.
   - Group windows of 25, 40 and 60 ms gave the same synthetic results.
2. **Tempo induction, every tick with new onsets.**
   - Take every pair of groups in the last 12 s with a gap of 0.15-3 s. Weight each pair by salience product × 0.8^(groups between).
   - Accumulate into a log-period histogram: 1/60 octave bins, Gaussian σ 3.5%.
   - Score each period P as H(P) + ½H(2P) + ⅓H(3P) + ¼H(4P).
   - Multiply by a log-normal prior centred at **80 bpm**, σ 0.7 octave.
   - **Periodicity strength** = best score ÷ mean score (section 6.7).
3. **Agents: hypotheses of period and next beat.**
   - A group within max(60 ms, 0.18·P) of a predicted beat is a hit:
     - the phase moves by 0.8 of the error;
     - the period moves by 0.35 of it, clamped to 0.7-1.4 of the birth period;
     - the score gains salience, and decays with τ 10 s.
   - A missed beat costs 0.15 × mean salience.
   - An off-window salient onset spawns a child that accepts it (BeatRoot).
   - The top 3 induction candidates spawn agents. Each is anchored at the most salient early onsets and retro-scored over the window, so a newcomer competes fairly.
   - Near-duplicates are pruned and at most 24 agents are kept.
   - The shown agent changes only when a rival ranks 1.5× higher (rank = score × prior).
4. **Readout.**
   - BPM = median of the last 4 inter-beat intervals.
   - `hold` when the gap exceeds max(2 s, 2.5 beats). The next onset re-anchors the phase, keeps the period, and halves scores.
5. **Settled beats (lag 2).**
   - A beat is finalised once two more beats exist.
   - A hit beat takes its onset time. A missed beat is interpolated between the neighbouring hits.
6. **Meter (tatum level, once a second).** Detailed in section 6.4:
   - subdivision grid first;
   - then the R² of the accent sequence against grouping templates;
   - hysteresis of 4 decisions;
   - displayed tempo converted to the tactus (for example ×2/3 for 6/8 heard at the quarter).

### 4.2 Synthetic performances with ground truth

- **Generator.**
  - 3 meters (4/4, 3/4, 6/8) × 3 textures:
    - ballad: bass, rolled chord, melody a tenth above;
    - arpeggio: broken bass-5th-10th under melody;
    - block chords.
  - × 3 rubato levels, 32 bars each.
  - Tempo 60-110 bpm; the 6/8 dotted quarter is 45-75.
  - A one-beat pickup in half the pieces, and legato pedal changes after each bar's chord.
- **Rubato levels:**
  - **rub0:** 10 ms note jitter.
  - **rub1:** ±4% phrase swell, a ±6% random drift, a phrase-end beat ×1.15, 20 ms jitter.
  - **rub2:** ±10% swell, a ±12% drift, a ritardando ×1.2 then ×1.5 into each phrase end, a fermata (+1 to 2.5 beats) at 40% of phrase ends, 30 ms jitter.
  - True beat-to-beat wobble, as median / p90 of |ln(IBI_k/IBI_k−1)|: rub1 **1.4% / 12.5%**, rub2 **3.8% / 27%**.
- **Protocol.**
  - Parameters were tuned on seeds 11 and 23 (54 pieces). All numbers below are from **held-out seeds 37, 41, 53 (81 pieces)**.
  - Beat F-measure uses ±70 ms, the MIREX and mir_eval window, and skips the first 5 s as the SMC 2025 paper does.
  - Acc1 is the displayed BPM within 8% of the local true tempo (also reported at 4%). Acc2 also accepts ×2, ½, ×3, ⅓, ×1.5 and ⅔.
  - Fermata beats are excluded from tempo accuracy.

**Held-out results by configuration**

| Configuration | Beat F | Beat F, any level | Acc1 8% | Acc1 4% | Acc2 | Level errors | Tempo flips/min | Meter right | Downbeat F |
|---|---|---|---|---|---|---|---|---|---|
| Base (inner window 0.12·P, phase gain 0.5, period gain 0.2, switch 1.2, beat-level meter) | 0.559 | 0.624 | 0.562 | 0.433 | 0.836 | 0.274 | 1.80 | 0.531 | 0.516 |
| Tuned agents (inner 0.18·P, phase 0.8, period 0.35, switch 1.5) | 0.642 | 0.732 | 0.578 | 0.464 | 0.815 | 0.237 | 0.68 | 0.679 | 0.577 |
| + tatum-level meter and tactus conversion | 0.642 | 0.732 | 0.708 | 0.574 | 0.815 | 0.107 | 2.54 | 0.593 | 0.535 |
| **+ meter hysteresis (4 s) and 6/8 bias (+0.05, 12-tatum penalty 0.03)** | **0.642** | **0.732** | **0.710** | **0.577** | **0.815** | **0.105** | **1.60** | **0.815** | **0.578** |

**The recommended configuration (last row), by rubato level**

| Level | Beat F | Acc1 8% | Acc2 | Meter right | Downbeat F |
|---|---|---|---|---|---|
| rub0 (metronomic + jitter) | 0.855 | 0.891 | 0.983 | 0.889 | 0.905 |
| rub1 (mild rubato) | 0.614 | 0.848 | 0.943 | 0.926 | 0.655 |
| rub2 (strong rubato) | 0.455 | 0.392 | 0.520 | 0.630 | **0.173** |

**Meter confusion** (the recommended configuration, 27 pieces per meter):
- 4/4 → 4/4 24, 6/8 2, 12/8 1.
- 3/4 → 3/4 18, **6/8 8**, 4/4 1.
- 6/8 → 6/8 24, 12/8 3.
- Before the 6/8 bias it was 6/8 → 6/8 4, 12/8 22, and 3/4 → 3/4 20. **The bias buys 6/8 at the cost of 3/4.** That is a prior choice, which argues for letting Daniel choose (D1).

**Other synthetic receipts**

| Test | Result |
|---|---|
| Time until the shown tempo is within 8% for 2 s | mean **9.4 s**; 4 of 81 pieces never (recommended configuration). Readouts start at 4 s. |
| Tempo step 70 → 95 bpm at bar 16 (base agents) | recovered in 4.9, 5.2, 7.6 and 10.3 s |
| Lag-2 settled beats against causal beats | F 0.640 against 0.642: no gain on hits, the value is in interpolated misses |
| Induction only, with no agents (tuning seeds) | Acc1 0.65 against 0.61 with agents, but no phase and no beats. Agents are for the grid and the runner-ups, not for a better BPM number. |
| Parameter ablations (tuning seeds, base agents) | inner window 0.12 → 0.18·P: beat F 0.569 → 0.658, flips 1.36 → 0.77 per min. Switch 1.2 → 1.5: flips 1.36 → 0.70. Score τ 6 s: flips 2.44 (worse). Prior 75 bpm / σ 0.5: Acc1 0.609 against 0.605 (no gain). |
| Meter accent ablation (base, 54 pieces) | onsets only 0.537; + new bass 0.519; + harmony change 0.556; + pedal change 0.556; all 0.574. Within noise here, because the synthetic downbeats carry a velocity accent. Real labelled takes are needed to test this (TM5). |
| Beat-to-beat wobble read back by the tracker | rub0 1.6% / 4.4% (tracker noise floor); rub1 3.5% / 10.9%; rub2 4.1% / 20.5% (median / p90) |

**Free time on synthetic unmetered playing** (9 pieces: random gaps with a log-normal median of 0.5 s, chords of 1-4 notes):

| Measure | rub0 | rub1 | rub2 | Random |
|---|---|---|---|---|
| Periodicity strength p10 / p50 / p90 | 6.9 / 8.4 / 11.3 | 4.1 / 5.3 / 7.5 | 2.5 / 3.2 / 5.5 | 2.2 / 2.7 / 3.2 |
| Grid fit (salience share within 5% of a beat, ½ or ⅓) p10 / p50 / p90 | 0.80 / 0.94 / 1.00 | 0.49 / 0.78 / 0.93 | 0.43 / 0.61 / 0.79 | 0.41 / 0.62 / 0.80 |
| Tracker state "lock" (hit share ≥ 0.6 and IBI CV < 0.15) on random playing | | | | **62% of the time** |

Periodicity bands on random playing are free 79%, loose 21%, steady 0%. The hit-share rule calls the same playing locked 62% of the time. **A tracker that adapts to every onset will always look confident on its own grid.**

### 4.3 On Daniel's sessions (read-only; recommended configuration unless noted)

| Session | Min | Lock / hold / free share | Periodicity steady / loose / free | Locked BPM p25 / med / p75 | Wobble med / p90 | Tempo flips/min (×1.5, ×2) | Meter label changes/min | Same tempo with ±25 ms added jitter |
|---|---|---|---|---|---|---|---|---|
| S1 | 5.4 | .38 / .13 / .31 | .11 / .40 / .49 | 71 / 85 / 93 | 5.7% / 25.7% | 2.03 (0.74, 0) | 1.29 | 47% |
| S2 | 5.0 | .83 / .09 / .02 | .08 / .66 / .26 | 55 / 73 / 100 | 3.6% / 15.4% | 2.19 (1.99, 0) | 2.58 | 42% |
| S3 | 22.2 | .52 / .33 / .06 | .03 / .30 / .67 | 57 / 70 / 94 | 4.0% / 17.7% | 2.07 (1.71, 0.05) | 1.44 | 39% |
| S4 | 3.9 | .79 / .00 / .03 | .00 / .15 / .85 | 57 / 72 / 80 | 6.7% / 22.3% | 3.89 (3.37, 0) | 1.82 | 31% |
| S5 | 7.8 | .65 / .18 / .12 | .06 / .58 / .36 | 52 / 76 / 85 | 4.2% / 18.0% | 2.05 (1.28, 0.38) | 1.41 | 31% |
| S6 | 6.9 | .53 / .31 / .11 | .03 / .69 / .27 | 83 / 93 / 102 | 4.4% / 17.3% | 2.17 (1.74, 0) | 1.01 | 41% |
| S7 | 8.4 | .90 / .01 / .04 | .12 / .69 / .19 | 79 / 94 / 98 | 3.8% / 14.6% | 1.31 (1.19, 0) | 1.43 | 69% |
| S9 | 5.5 | .66 / .15 / .11 | .08 / .62 / .30 | 86 / 91 / 96 | 3.2% / 13.2% | 0.54 (0.18, 0) | 0 | 81% |
| S10 | 1.2 | .67 / .08 / .10 | .00 / .35 / .65 | 64 / 77 / 94 | 5.0% / 20.8% | 2.45 (2.45, 0) | 1.63 | 55% |
| S11 | 7.6 | .14 / .49 / .09 | .07 / .13 / .80 | 76 / 87 / 95 | 5.1% / 30.9% | 1.58 (1.06, 0) | 0.92 | 61% |
| S12 | 31.2 | .39 / .37 / .19 | .05 / .34 / .61 | 62 / 83 / 98 | 5.3% / 22.2% | 2.53 (1.47, 0.10) | 1.47 | 36% |

Other counts:
- **Gaps between onset groups:** a median of 182-293 ms. There are 0.4-3.1 pauses over 2 s per minute.
- **Base configuration for comparison.** It has no tatum meter and no hysteresis.
  - Meter label changes: 3.0-13.5 per minute.
  - Same tempo under jitter: 42-75%.
  - ×1.5 flips: 0.1-1.6 per minute.
  - Label shares while locked: 4/4 22-63%, 12/8 15-53%, 3/4 8-28%, 9/8 2-55%.
  - With the recommended configuration: 6/8 58-100%.

**What the table says:**

- **His tempo is where he feels it,** but **his wobble matches the strong-rubato synthetic set.** The same tracker reads 4.1% / 20.5% on rub2 and 3.2-6.7% / 13-31% on him. Expect rub2-like grid quality, with downbeat F near 0.17, from his notes alone.
- **The level is fragile.** Adding ±25 ms of random jitter to his onsets changes the shown tempo family member on 19-69% of readouts. The ×1.5 relation (in 2 or in 3) dominates. Octave (×2) flips are rare.
- **The tatum meter's tempo conversion is the source of the extra ×1.5 flips** (up to 3.4 per minute on S4). With a **user-set meter** the conversion is fixed and those flips disappear, which is one more reason for D1.
- **The "lock" share is not confidence.** Random onsets also read "lock" 62% of the time. The periodicity bands are the honest steadiness: mostly loose or free, steady at most 12%.
- **The meter label follows the prior.** Change a 0.05 tie-break and his playing goes from mostly 4/4-or-12/8 to mostly 6/8. There is no ground truth, so no claim of correctness is possible. What is shown is that the evidence is not decisive.

---

## 5. What this means for "correct notation in real time"

- **Pitch, hands, pedal, dynamics:** other lanes; not beat-dependent.
- **Rough BPM:** yes, live, from his playing.
  - Show `♩ ≈ 85`, with the steadiness word from periodicity strength.
  - Offer ÷2 / ×2 / "in 2 ↔ in 3" buttons fed by the hypothesis family.
- **Metric notation (bars, beats, rhythms):** correct when the beat comes from the jam map, the song, or his taps plus "This is 1".
  - From inference alone it is reliable only in stretches that read **steady**, and even then only with his meter choice.
  - Everything else is **tape** (proportional, unmetered) notation, as `transcription.md` T2.5 (a) and `rendering-formats.md` recommend.
- **After the take:** an offline tidy pass can do better than live, with the whole take and a smoother (section 6.9). It still cannot invent a meter he did not play. The clean copy should ask him for meter and "1" when the take had no real beat.

---

## 6. Recommended v1 design

### 6.1 Output contract (for T3/T4 and `Take`)

```
beatState {
  source:    "jam" | "song" | "taps" | "inferred" | "none",   // ladder rung in force; written into every bar
  mode:      "steady" | "loose" | "free" | "hold",             // periodicity bands (6.7) + pause rule (6.6)
  beats:     [{ t_ms, index, conf, settled }],                  // settled after lag L (6.8)
  period_ms, bpmShown,                                           // bpmShown: integer tactus BPM, updated at most once a bar
  family:    [{ ratio: 1 | 2 | 0.5 | 1.5 | 0.667, score }],     // live runner-ups for the ÷2 / ×2 / "2 <-> 3" buttons
  meter:     { beats, beatType, tactusPerBar, subdivision: 2 | 3,
               source: "jam" | "user" | "accepted-suggestion" | "default",
               suggestion?: { label, margin, since_ms } },
  barPhase:  { downbeatIndex, source: "jam" | "song" | "this-is-1" | "inferred", conf },
  pickup:    { tatums } | null,
  holds:     [{ from_ms, to_ms }]
}
```

- **`Take.tempo`:**
  - `bpm` = the take's median settled `bpmShown`.
  - `confidence` = the share of the take in `steady`.
  - `map` = one segment per settled bar, `{from_bar, bpm, epoch_ms}`. That is the jam tempo map's shape, so export and replay reuse `tempomap.js` arithmetic.
- **`Take.time`** = `meter` while `mode` is `steady` or `loose` and a beat source exists; otherwise `"free"`.

### 6.2 The inferred rung: why multiple hypotheses

- `transcription.md` T2.2 proposes a single Large-Kolen oscillator: phase 0.3, period 0.1, seeded from the modal gap doubled into 55-110 bpm. It is simple and it will work in steady stretches.
- On his playing, though, the error that matters is **which level** is the beat. A single oscillator commits to one level and has no runner-up to offer.
- The agent set of section 4.1 is the cheap version of the particle filter T2.2 lists as v2 ([Cemgil & Kappen](http://papers.neurips.cc/paper/1999-tempo-tracking-and-rhythm-quantization-by-sequential-monte-carlo.pdf)). Its cost is at most 24 agents per onset group plus one all-pairs histogram over 12 s, about 50-150 groups. Measured in Node, the whole causal run took 403 ms for S12 (31.2 min, 4,444 onset groups, 7,496 ticks, about 0.05 ms per 250 ms tick) and 281 ms for S3 (22.2 min).
- Parameters to start from are in section 4.1. They are tuned on synthetic playing only; retune them on labelled takes (TM5).
- **Seed and prior.**
  - The prior is centred at 80 bpm with σ 0.7 octave: his feel, not the population's 120.
  - A tap within 8% of a family member selects that member.
  - A new tap sequence replaces the family.
  - The chosen level is remembered for the session.
- **Display.** `bpmShown` updates at most once a bar and only by 3 bpm or more (T2.3). The family buttons act immediately.

### 6.3 Using the real beat sources

| Rung | Beats | Meter and bar phase | Notes |
|---|---|---|---|
| 1 Jam map | `tEpoch(segments, m, bar, beat)` mapped to session `t_ms` with `sessionTms` (jam spec 11.2) | `beats_per_bar` and the run's bar 0; exact | While a run plays, keep the inferred tracker running **in the background** against the jam grid, for his early or late histogram (practice feedback) and as a free receipt of the inferred rung's accuracy on his real playing. |
| 2 Song listener | `nextBeatPerf + k·periodMs`, converted with the log's `t0_perf_ms` | `barPhase` only after "This is 1"; otherwise meter default, with no bar lines until he taps 1 | Below the listener's `phaseConf` floor, fall to rung 3 or 4. The listener's "loose" and "lost" words map to `mode`. |
| 3 Taps | The `deck.js` tap (4 taps, median) gives the period. The last tap gives the phase. "This is 1" gives the bar. | His meter choice | The inferred agents are re-seeded from the tap, so the grid keeps adapting to his rubato after tapping. |
| 4 Inferred | Section 4.1 | Section 6.4 suggestion; default 4/4 | Only `steady` stretches draw metric bars without his input (6.7). |
| 5 None | none | `"free"` | Tape notation. |

### 6.4 Meter

**Product rule (recommended, D1).**
- The meter is **his setting**: 4/4 by default, one tap for 3/4, 6/8, 12/8 or free.
- The tracker **suggests** a different meter as a chip ("sounds like 3/4?") only when all of these hold:
  1. its template margin over the current meter is at least 0.15 R²;
  2. it stays ahead for 8 consecutive decisions;
  3. the passage reads `steady`.
- The label never switches on its own in v1. The data: automatic labels on his sessions follow a 0.05 tie-break (4.3), and even the best live MIDI meter model scores a metrical F of about 57 on live performance (McLeod 2018).

**Algorithm, for the suggestion and for the tidy pass.**
1. **Subdivision first.** Over the last 32 beats, compare off-beat salience near ½ with salience near ⅓ and ⅔.
   - Grid 3 if thirds win and exceed 25% of the on-beat salience.
   - Grid 2 if halves exceed 25%.
   - Otherwise grid 1: no subdivision evidence.
2. **Tatum accents.** For each tatum, take the maximum over its onsets of:
   - salience;
   - **+0.7** if the group holds a new bass (the lowest note within ±0.8 s, at or below G3);
   - **+1.2 × harmonic change**. The prototype uses the pitch-class Jaccard distance of 0.6 s before against 0.6 s after. In the build, use a **harmony window start** from `harmony.js`, the chord reader's one commit clock.

   Then add **+0.8** to the tatum a **pedal change** follows within 0.3 s. His pedal lags the chord by a median of 110-190 ms, per `transcription.md`.
3. **Grouping templates.** Score the R² of the whole accent sequence against each template expanded over it. (A folded-mean correlation is degenerate for 2-beat bars; the prototype's first version always chose 2/4 because of it.)

   | Grid | Template (per tatum) | Meter | Tactus |
   |---|---|---|---|
   | 1 (beat) | 1,0 / 1,0,0 / 1,0,.5,0 | 2/4, 3/4, 4/4 | beat |
   | 1, beat above 125 bpm | 1,0,0,.6,0,0 / 1,0,.4,0,.4,0 | 6/8 / 3/4 at the eighth | 3 / 2 tatums |
   | 2 (eighths) | 1,0,.3,0 / 1,0,.4,0,.4,0 / 1,0,.3,0,.6,0,.3,0 / 1,0,0,.6,0,0 / 1,0,0,.4,0,0,.7,0,0,.4,0,0 | 2/4, 3/4, 4/4, 6/8, 12/8 | 2, 2, 2, 3, 3 tatums |
   | 3 (triplets) | 1,0,0,.6,0,0 / 1,0,0,.4,0,0,.4,0,0 / 12-tatum | 6/8, 9/8, 12/8 | 3 tatums |

   - Preferences: 4/4 +0.02, 6/8 +0.05, 12-tatum bars −0.03.
   - These are the tie-breaks that decide 3/4 against 6/8 on ambiguous playing (4.2). Record them as priors, not truths.
4. **Tactus conversion.** `bpmShown = beat BPM × grid ÷ tactus tatums`. For example, 6/8 heard at the quarter shows the dotted quarter. Apply it only to a committed meter, or it causes ×1.5 display flips (4.3).
5. **Hysteresis.** 4 consecutive decisions (4 s) before a committed label changes. A new beat hypothesis re-derives the phase at once.

### 6.5 Downbeats and pickups

- **Bar phase priority:**
  1. jam;
  2. song `barPhase`;
  3. "This is 1";
  4. inferred: the tatum phase of the winning template. On his style the strongest cues are a new bass, a harmony window start, and a pedal change right after.
- **An inferred phase is drawn only in settled bars,** and only once the meter is set or accepted. Synthetic downbeat F is 0.91, 0.66 and 0.17 by rubato level.
- **Pickups:**
  - Onsets before the first committed downbeat of a phrase become an anacrusis.
  - It is measured as a whole number of sub-beats (the met-align constraint), counted in tatums.
  - It is allowed only while the first bar is unsettled (T2.4).
  - A phrase starting after a hold re-tests the pickup against the carried bar phase.

### 6.6 Pauses and fermatas

- `hold` starts when the gap since the last onset group exceeds **max(2 s, 2.5 beats)**:
  - no beats are emitted;
  - `bpmShown` freezes, dimmed;
  - the tempo segment ends.
  - Holds cover 0-49% of session time (S11 is the high one).
- **On the next onset:** re-anchor the phase on it, keep the period, and halve every hypothesis score so a new tempo can win quickly. (A 70 → 95 bpm change took 5-10 s to show without a pause.)
- **Fermata or rest:** follow `transcription.md` T2.4. A held or pedalled last chord longer than twice its beat is a fermata; otherwise the bar is completed with rests.
- **Retro-anchor:** if the first onsets after a hold read `steady` within 4 beats, the phrase's bar phase may be re-derived; that is what a pianist does after a breath.

### 6.7 Steadiness and free time

- **Primary signal: periodicity strength** from the induction histogram, with 2 s hysteresis:

  | Strength | Word | Notation |
  |---|---|---|
  | ≥ 4.5 | `steady` | metric bars allowed from the inferred rung |
  | 3 to 4.5 | `loose` | metric bars only with a beat source on rungs 1-3; otherwise tape with a `rubato` mark |
  | < 3 | `free` | tape; `freely` |

- The cut points are calibrated on synthetic data:
  - random playing: median 2.7, p90 3.2;
  - mild rubato: p10 4.1;
  - metronomic: p10 6.9;
  - strong rubato straddles loose and free, which is the honest reading.
- **Secondary signal:** the chosen hypothesis's hit share over 8 beats. It may **lower** the word, never raise it.
- **Reconcile with `transcription.md` T2.2 and T2.5.** Its confidence, "share of the last 8 beats' onsets within 12% of a beat of their division grid", is this secondary measure. On synthetic data it cannot tell random notes (median 0.62) from strong rubato (0.60), because the tracker bends to the notes. Use periodicity strength to enter and leave free time, and keep grid fit as a veto.
- **Expect mostly tape on unaccompanied takes.** His sessions read steady 0-12%, loose 13-69% and free 19-85% of the time.

### 6.8 Latency and settling

| Consumer | Beats it uses | Lag |
|---|---|---|
| Cursor, beat pip, `bpmShown` | causal agent beats | a group is usable 40 ms after its first note; the display waits for the next beat |
| Quantizer (T3) | settled beats: a hit takes its onset time; a miss is interpolated between neighbouring hits | 2 beats |
| Bar freeze (T4, T9) | settled bars | **4 beats** (the transcription lane measured 5.7% relabel churn at 4 against 10.7% at 2) |

### 6.9 Offline tidy pass after the take

- Run a non-causal pass over the whole take:
  - the same agents forward and backward, or a Viterbi over (period, phase) with McLeod's proportional tempo penalty;
  - **one meter per phrase,** separated by holds;
  - a smoothed tempo map exported as `<sound tempo>` and metronome marks in MusicXML, plus MIDI tempo events (`rendering-formats.md`).
- The clean copy asks for "1" and the meter when the take had no real beat, then re-quantizes. Logic's Adapt mode is the precedent.
- PM2S or met-align can be run next to it as a comparison **only after D4**.

### 6.10 Timestamps

- **Log `ev.timeStamp`.** The page's `onMidiMessage` passes only data to `noteOn`, which stamps `clock()`. Logging `ev.timeStamp` removes handler delay from every onset; convert it with the same `T0`.
- **The synthetic injection path already fakes it:** `onMidiMessage({... timeStamp: performance.now() ...})`.
- **Measure before changing** (drill TM-D, section 8), because the difference is unknown here.
- **The prototype shows why it matters:** ±25 ms of added jitter moves the beat level on up to 69% of readouts on some sessions.

---

## 7. Why not adopt a model

- **All strong symbolic systems are offline** and trained on classical piano: ASAP, MAPS and A-MAPS.
- **Even offline they struggle on downbeats in expressive playing:** ASAP downbeat F 14-28%.
- **His material is outside their training:** by-ear pop and worship harmony, pedalled rolls, long holds.
- **The live problem is different:** it needs runner-ups, a free-time decision and hysteresis, which those models do not expose.
- **Installing them is a download** (PyTorch, a Java build), and each needs Daniel's OK.

The value they could add is an **offline upper bound** on labelled takes (TM5), not a live component.

---

## 8. Build slices (proposal)

| Slice | Content | Receipt |
|---|---|---|
| TM0 fixtures | Promote the synthetic generator (3 meters × 3 textures × 3 rubato levels, pickups, fermatas, tempo steps, random unmetered pieces) to `tests/fixtures/sheet/beat_cases.json` with truth. Port the metrics: beat F ±70 ms, lag-2 F, Acc1 / Acc2, level errors, flips per minute, meter confusion, downbeat F, periodicity bands. | Report-only numbers, reproducing section 4.2 within noise |
| TM-D drill (Daniel plays, no sound needed) | Log `ev.timeStamp` and `clock()` side by side for 2 minutes while the 3D scene renders | The offset and jitter distribution, in a dated drill note; decide on section 6.10 |
| TM1 `arsenal/web/piano/beat.js` | Pure module in `tempomap.js` style: groups, induction with periodicity strength, agents, family, readout, hold, settle. No DOM and no clock. | TM0 fixtures pass at the report's numbers; one fixture per failure named here (×1.5, ×2, fermata, tempo step, random) |
| TM2 meter and bar phase | Tatum-level suggestion, the meter chooser (default 4/4), "This is 1", `harmony.js` window starts as accents, pickup rule | Meter confusion on fixtures. A chip appears on steady 3/4 fixtures and never on random ones. |
| TM3 ladder | Jam rung (`sessionTms`), song rung (`beat` to `t_ms`), tap rung re-seeding the agents, a source label on every bar, `beatState` into `Take` | A jam run's bars match the tempo map to 2 ms. The inferred rung's accuracy against the jam grid is logged as a receipt on **his real playing**. |
| TM4 tidy pass | Non-causal smoother, one meter per phrase, tempo-map export | On fixtures, tidy beat F at least causal beat F; MusicXML carries `<sound tempo>` |
| TM5 labelled takes (Daniel) | About 10 short takes with known meter and tempo: some with the jam click, some free, 3/4 and 6/8 included | The first real accuracy numbers for rungs 3-4; retune the prior, windows and meter biases; decide whether any suggestion ever auto-applies |

---

## 9. Decisions for Daniel

1. **D1 Meter.** Should the meter be your setting (4/4 default, one tap to change, suggestions only), or should the page switch meters by itself? Recommended: your setting. The automatic label on your sessions changes with a tiny tie-break, so it cannot yet be trusted.
2. **D2 Free time in the live score.** Tape (unmetered) where there is no steady beat, forced bars marked rubato, or both (tape live, bars in the clean copy)? Recommended: both. This is shared with `transcription.md` Q1.
3. **D3 Labelled takes.** Will you record about 10 short takes where you tell us the meter and count (a few with the jam click)? Without them no one can claim "correct notation" for inferred beats.
4. **D4 Reference models.** Should any of these be installed as local, offline-only comparisons?
   - PM2S: MIT, needs PyTorch (a download);
   - met-align: MIT, Java, needs a build;
   - MIDI2ScoreTransformer.

   Recommended: not for v1; revisit after TM5.
5. **D5 Counting.** For a slow ballad, do you count about 70 or about 140? Is a 6/8 feel "in 2" or "in 6"? This sets the prior centre (80 bpm now) and which family member the page shows first.
6. **D6 Timestamps.** After the TM-D drill, should the log switch to the MIDI event's own timestamp? It changes how every future session is timed; old sessions stay as they are.

---

## 10. Open questions and risks

1. **Synthetic is not Daniel.** Every accuracy number in section 4.2 is on generated playing with built-in velocity accents on downbeats. His sessions have no ground truth, so section 4.3 shows stability and plausibility, not correctness. TM5 is the fix.
2. **3/4 against 6/8** is decided by a prior on ambiguous arpeggiated playing (4.2 confusion). Harmony windows may break the tie on real music; this is untested.
3. **Compound meter in the jam map.** `beats_per_bar` is an integer with an implied quarter. A 6/8 or 12/8 jam loop needs a beat unit, or a convention of dotted-quarter beats. That is a jam-spec question, raised here because notation needs the beat unit.
4. **Tempo changes by section** are recovered in 5-10 s without a pause. A worship-style build or a sudden double-time will lag by about 2 bars.
5. **Hand independence.** A melody running ahead of the bass (his solo line over the bass) blurs group times. Groups use the earliest note, and the rolls he plays are narrow (p90 30-38 ms), but a deliberate melody lead of 40-80 ms (`transcription.md` near-chord rule) could shift beats. Test on TM5 takes.
6. **Performance at session scale.** The prototype's meter step rescans a 32-beat window every second. Fine for v1; keep the harmony-window accents incremental in the build.
7. **The periodicity cut points (3 and 4.5)** come from synthetic calibration. Their exact values on real playing should come from TM3's background receipt against jam grids.

---

## Sources

- [PM2S paper, ISMIR 2022](https://www.turing.ac.uk/sites/default/files/2022-09/midi_quantisation_paper_ismir_2022_0.pdf) · [PM2S code](https://github.com/cheriell/PM2S) · [PM2S page](https://cheriell.github.io/research/PM2S/)
- [Murgul & Heizmann, Beat and Downbeat Tracking in Performance MIDI, arXiv 2507.00466 (SMC 2025)](https://arxiv.org/abs/2507.00466)
- [Beyer & Dai, End-to-end Piano Performance-MIDI to Score Conversion with Transformers, arXiv 2410.00210 (ISMIR 2024)](https://arxiv.org/abs/2410.00210) · [code](https://github.com/TimFelixBeyer/MIDI2ScoreTransformer)
- [Wachter, Murgul, Heizmann, Transformer-Based Rhythm Quantization Using Beat Annotations, arXiv 2604.22290 (2026)](https://arxiv.org/abs/2604.22290)
- [McLeod & Steedman, Meter Detection and Alignment of MIDI Performance, ISMIR 2018](https://apmcleod.github.io/pdf/ISMIR_Meter.pdf) · [met-align](https://github.com/apmcleod/met-align)
- [Temperley, A Unified Probabilistic Model for Polyphonic Music Analysis, JNMR 2009](https://davidtemperley.com/wp-content/uploads/2015/11/temperley-jnmr09.pdf) · [Music and Probability, MIT Press](https://direct.mit.edu/books/monograph/2326/Music-and-Probability)
- [Nakamura et al., Rhythm Transcription of Polyphonic Piano Music Based on Merged-Output HMM, arXiv 1701.08343](https://arxiv.org/abs/1701.08343)
- [Dixon, Evaluation of the Audio Beat Tracking System BeatRoot, JNMR 2007](http://www.eecs.qmul.ac.uk/~simond/pub/2007/jnmr07.pdf)
- [Cemgil, Kappen, Desain, Honing, On Tempo Tracking: Tempogram Representation and Kalman Filtering](https://www.mcg.uva.nl/mcg-2023/papers/mmm-27.pdf) · [Cemgil & Kappen, Tempo tracking and rhythm quantization by sequential Monte Carlo](http://papers.neurips.cc/paper/1999-tempo-tracking-and-rhythm-quantization-by-sequential-monte-carlo.pdf)
- [Dynamic models for musical rhythm perception and coordination, Frontiers 2023](https://www.frontiersin.org/journals/computational-neuroscience/articles/10.3389/fncom.2023.1151895/full)
- [Meier, Chiu, Müller, A Real-Time Beat Tracking System with Zero Latency and Enhanced Controllability, TISMIR 2024](https://transactions.ismir.net/articles/10.5334/tismir.189) · [real_time_plp](https://github.com/groupmm/real_time_plp)
- [Carnovalini & Rodà, A Real-Time Tempo and Meter Tracking System for Rhythmic Improvisation, arXiv 2208.14717](https://arxiv.org/abs/2208.14717)
- [Moelants, Preferred tempo reconsidered](https://www.semanticscholar.org/paper/Preferred-tempo-reconsidered.-Moelants/b0db06a5a8b2c1942afff5c317c5f6da55a7dcf7)
- [Apple, Match the tempo automatically in Logic Pro](https://support.apple.com/en-us/102165) · [Sound On Sound, Logic Pro: Using Smart Tempo](https://www.soundonsound.com/techniques/logic-pro-using-smart-tempo)
- [MuseScore 3 handbook, MIDI import](https://musescore.org/en/handbook/3/midi-import) · [MuseScore forum, quantization in MuseScore 4](https://musescore.org/en/node/363436) · [MuseScore forum, MIDI recorded without metronome](https://musescore.org/en/node/321251)
- [Scoring Notes, Real-time MIDI recording in Dorico](https://www.scoringnotes.com/tips/real-time-midi-recording-in-dorico/)
- [W3C Web MIDI API (MIDIMessageEvent timeStamp)](https://www.w3.org/TR/webmidi/)
- [Time Signature Detection: A Survey, Sensors 2021](https://www.mdpi.com/1424-8220/21/19/6494)
