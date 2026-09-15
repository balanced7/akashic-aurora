# Critic pass: live sheet music plan

| | |
|---|---|
| Date | 2026-09-14 |
| Status | Critique only. Nothing under `arsenal/` edited (the jam build still holds `piano.js`, `piano.html`, `piano.css`, `log.js`, `serve.py`, `cues.js`: `git status` shows them modified). No server, browser, download, install or login. |
| Reviewed | `live-sheet-music-plan.md` (the plan) and the three lanes: `tempo-meter.md`, `transcription.md`, `rendering-formats.md` |
| Asked for | Daniel, verbatim: "what if we keep a rough estimate of bpm and make it possible to save the notes i am playing into something that can render into sheet music with correct notation in real time, I wonder if we can make that happen!" |
| Method | (1) Load-bearing claims re-checked against primary sources: npm registry, jsDelivr, VexFlow source, W3C specs, the arXiv papers, the PM2S, McLeod and EngravingGNN PDFs, product docs. (2) The plan's rules checked against how Daniel plays, with two new read-only scratch passes over the practice log. (3) The plan's own arithmetic and receipts read for internal errors. |
| New scratch (untracked) | `C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/sheet/critic_stats.py` → `critic_stats.out`; `critic_pedal.py` → `critic_pedal.out` |
| Privacy | Counts, shares and intervals only. Sessions are **S1..S14 in folder order**, so S1-S12 match the lanes' numbering. S13 and S14 are newer. S8 is skipped (too short), which leaves 13 sessions. |
| Labels | Corrections **C1-C20**, missing items **M1-M9**. Plan labels (LS, LR, LQ) are cited as-is. |

---

## 0. In one screen

**The plan's structure holds up.** The beat ladder, tape for free time, settle-then-freeze, one engine for live and clean, and in-house writers are sound. Most of its facts check out: VexFlow 5.0.0, its size, licence and global; the PM2S, SMC 2025 and McLeod numbers; the MusicXML elements; the Web MIDI `timeStamp` wording.

**It fails on Daniel's actual texture in several places.** Applied as written, rules that look reasonable on synthetic data would give unreadable pages on his sessions. Measured on 13 sessions:

| Plan rule, as written | What his log says | Result if built as written |
|---|---|---|
| Written end = key release; a rest unless the gap to the next onset is under a 16th (6.4) | Gap from release to the next onset in the same register is a 16th or more for **18-48%** of notes (crude proxy). **57-98%** of releases happen with the pedal down. | A rest after a fifth to half of all notes, almost all under the pedal. **(C1)** |
| Divisions per beat d ∈ {1, 2, 4, 3}; denser beats are `loose` and export as 16th chords (6.4) | **0-22%** of non-empty beats (median 10%) hold 5+ onset groups at his rough quarter | Sextuplet arpeggios written as wrong 16th chords, in up to a fifth of beats. **(C2)** |
| Tape at 120 px/s, noteheads by time (2.1, 7.3) | **7.5-34%** of successive onset gaps are under 148 ms, the time a black notehead's width takes at s = 15; **5-20%** are under 100 ms | Overlapping noteheads in every fast arpeggio. **(C6)** |
| Held bass extends to its sound end (6.4) | **3-43%** of pedal-ended bass notes (below C3) sound past a 4/4 bar; 21% in S12, the longest | Tie chains across bar lines. **(C7)** |
| Accent when 20+ above the hand's running median (6.5) | **7-20%** of notes at or above C4 would get an accent | Accent marks on a fifth of the melody. **(C8)** |
| `performance.mid` keeps "raw" CC64 and half-pedal (7.4) | The log keeps only crossings of CC64 = 64, with crossing values of 64-127 | Half-pedal is not in the data; the claim is false. **(C5)** |

**Three design changes matter most:**

1. **Durations under the pedal (C1).** Fill each note to the next onset in its voice whenever the pedal is down or the note still sounds. Write a rest only where the sound stopped.
2. **Sextuplets in v1 (C2).** Add d = 6. `TPQ = 24` already holds sextuplets (4 ticks), so it is one row in the cost table.
3. **A way to mark the beat that works for how he plays (C3, C4).**
   - He plays with both hands and his right foot is on the sustain pedal, so the HUD **Tap** and **This is 1** buttons cannot be used mid-take.
   - For free takes, the saved copy should come from **tapping along to the replay** plus **clicking a note to mark "1"**. Logic Pro's Beat Mapping and ScoreCloud's Tap Beat are the precedents.
   - The plan's default of forced bars at the inferred beat would, by its own numbers (downbeat F 0.17, 24% coverage under strong rubato), save a page of wrong bars.
   - Live, the KeyLab 88 mk3's two assignable Aux pedal inputs could take a left-foot switch for tap and "1" (a purchase, so Daniel's call).

**Two facts to fix before LQ1 goes to Daniel (C9):**
- **VexFlow's font loader is not pinned.** `Font.HOST_URL` is the bare `https://cdn.jsdelivr.net/npm/@vexflow-fonts/`, and it also wants the Academico text font. "CDN-pinned like three.js" is only true if the page skips `loadFonts` and reuses its own `FontFace("Bravura")`, or pins `HOST_URL` first.
- **The quantizer paper's 97.3% onset F1** was measured with ground-truth beats **and downbeats**, and no noisy-beat test was run (C18). It supports rung 1, not rungs 3-4.

**One honesty fix for section 0 (C12).** His sessions read `steady` only 0-12% of the time. So without a jam loop, taps or the song listener, the live panel is tape about 90% of the time. The one-screen summary should say so plainly: "correct notation in real time" means "with a beat source".

---

## 1. Fact-check of load-bearing claims

Verdicts: **OK** (confirmed from the primary source), **FIX** (wrong or incomplete), **UNVERIFIED** (not checkable here).

### 1.1 Libraries and formats

| Claim (where) | Verdict | Evidence |
|---|---|---|
| VexFlow latest stable is 5.0.0, MIT (plan 7.2) | OK | npm registry `latest` = 5.0.0, `license` MIT, exports `.`, `./core`, `./bravura` ([registry](https://registry.npmjs.org/vexflow/latest)) |
| `build/cjs/vexflow-core.js` is 336,625 B (plan 0, 7.2) | OK | jsDelivr listing: 336,625 B; `vexflow-bravura.js` 728,171 B; `vexflow.js` 1,128,380 B ([jsDelivr](https://data.jsdelivr.com/v1/packages/npm/vexflow@5.0.0?structure=flat)) |
| A script tag for the cjs core defines global `VexFlow` (plan 5.3) | OK | The getting-started guide shows the pinned core URL and the global ([guide](https://vexflow.github.io/vexflow-examples/guides/getting-started/)) |
| "VexFlow uses the same `@vexflow-fonts/bravura@1.0.2` woff2 the page already loads" (plan 7.3) | **FIX (C9)** | `src/font.ts` sets `HOST_URL = 'https://cdn.jsdelivr.net/npm/@vexflow-fonts/'` with no version, and `loadFonts` registers `new FontFace(fontName, url(...))` ([font.ts](https://github.com/vexflow/vexflow/blob/main/src/font.ts)). The guide loads Bravura **and Academico**. As written, the page would fetch an unpinned Bravura (a second `Bravura` face) plus Academico. Sharing is possible because `piano.js` 1168 registers `new FontFace("Bravura", …)` under the same family name, but only if the adapter calls `setFonts` without `loadFonts`, or pins `HOST_URL`. |
| Cross-stave voices since PR #1434 (rendering 4.0, plan 7.2) | OK | "Voice cross stave support in System", merged 2022-10-16 ([PR](https://github.com/0xfe/vexflow/pull/1434)) |
| `PedalMarking` is available (plan 7.2) | OK, with a limit | Types `text`, `bracket`, `mixed`. It takes `StaveNote[]` only, and a change notch is the same note listed twice ([pedalmarking.ts](https://github.com/vexflow/vexflow/blob/main/src/pedalmarking.ts)). A pedal change that lands between notes (his lag is 110-190 ms) cannot be placed by time. The plan's choice to paint the pedal line itself is therefore right, and the rendering lane's reliance on `PedalMarking` is not. |
| Slot-placed `TickContext` x is possible (plan 7.3, medium confidence) | OK in principle | `TickContext.setX` with one context per note bypasses the Formatter ([VexFlow wiki, formatting](https://github.com/0xfe/vexflow/wiki/How-Formatting-Works); [TickContext API](https://0xfe.github.io/vexflow/api/classes/TickContext.html)). Collision handling (accidentals, seconds) then becomes ours (C15). |
| Verovio 6.3.0, LGPL-3.0-or-later, about 7.3 MB (rendering 4.2, plan 7.2) | OK | Registry licence LGPL-3.0-or-later; `verovio-module.mjs` 7,296,807 B, `verovio-toolkit-wasm.js` 7,310,681 B ([registry](https://registry.npmjs.org/verovio/latest), [jsDelivr](https://data.jsdelivr.com/v1/packages/npm/verovio@6.3.0?structure=flat)) |
| Verovio "about 1.2 MB WebAssembly build" (transcription Q5) | **FIX (C19)** | Same listing: about 7.3 MB. The transcription lane is wrong; the plan uses the right figure. |
| OpenSheetMusicDisplay 2.1.2 bundles "a VexFlow 1.2.93 fork" (plan 7.2) | FIX (wording) | The registry shows a plain dependency `vexflow: 1.2.93`, BSD-3-Clause ([registry](https://registry.npmjs.org/opensheetmusicdisplay/latest)). "Fork" was not shown; "depends on VexFlow 1.2.93" is what the registry says. The conclusion stands. |
| MusicXML `<senza-misura>` exists (plan 7.4) | OK | It "explicitly indicates that no time signature is present" ([W3C](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/senza-misura/)). Import behaviour in MuseScore and Dorico is still untested (UNVERIFIED). |
| `<pedal type="start\|change\|stop" line="yes">` (plan 7.4) | OK | With `line="yes"`, `sign` defaults to no ([W3C pedal](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/pedal/)). Set `sign="no"` explicitly anyway for importers. |
| `performance.mid`: PPQ 500 with tempo 500,000 µs gives 1 tick = 1 ms (plan 7.4) | OK | 500,000 µs ÷ 500 = 1,000 µs. Rendering lane 6.2 says SMF type 1 with one track, the plan says type 0. Pick one (C19). |
| `performance.mid` keeps "CC64 with raw values … half-pedal" (plan 7.4, LR9b) | **FIX (C5)** | `onMidiMessage` calls `setSustain(d[2] >= 64, d[2])`, and `setSustain` returns early unless the state flips (`piano.js` 2025-2026, 2738). The comment says only the crossing is logged. On the log, down-crossing values are median 96-103, range 64-127; up-crossings are median 0. The pedal is continuous, but the log holds only a two-state signal. |

### 1.2 Research numbers

| Claim | Verdict | Evidence |
|---|---|---|
| Beat-conditioned quantizer, onset F1 97.3%, note values 83.3% on ASAP (plan 1, transcription 4.2) | OK, **wording FIX (C18)** | Numbers confirmed. But beat **and downbeat** annotations are given as ground truth. The model pre-quantizes to "twelve equidistant sub-beats" per beat. No test with estimated or noisy beats is reported ([arXiv 2604.22290](https://arxiv.org/abs/2604.22290), [HTML](https://arxiv.org/html/2604.22290)). This supports "rung 1 then notation is solved", not rungs 2-4. |
| SMC 2025 MIDI beat tracker: ASAP beat F 78.1 / downbeat 27.8; PM2S 83.0 / 14.1; Beat This! 76.3 / 61.2; A-MAPS 98.0 / 76.6; 5 s vs 10 s segments (tempo lane 3.1) | OK | Table 7: 78.13 / 27.81; PM2S 82.95 / 14.14; Beat This! 76.30 / 61.20; A-MAPS 98.01 / 76.56. Table 3: 5 s 91.77 / 65.54, 10 s 96.03 / 59.52 ([HTML](https://arxiv.org/html/2507.00466)). |
| Nakamura HMM on ASAP: 47.7 / 13.4 (tempo lane 3.1) | FIX (C19) | Table 7 gives the classical HMM 43.60 / 13.67. Not used by the plan. |
| PM2S: beat F 86.2, downbeat 69.8; MV2H 87.9 against Finale 65.0 and MuseScore 54.0; Fme 61.7 / 9.9 / 15.3 | OK | PM2S Tables 4-5 (read from the lanes' saved text of the paper, [paper](https://www.turing.ac.uk/sites/default/files/2022-09/midi_quantisation_paper_ismir_2022_0.pdf)) |
| McLeod and Steedman 2018: metronomic 80.5 against Temperley 67.7; live 56.5 against 47.6 | OK, with a nuance | Table 1: Temperley 67.65 / 47.62; best metronomic 80.50 (+Bach +X); best live 56.51 (+Bach +X +T). The base model scores **39.63** on live data, below Temperley. The best live score needs extra training data and a tempo feature ([PDF](https://apmcleod.github.io/pdf/ISMIR_Meter.pdf)). "About 57" is the ceiling of the best variant, not of a plain HMM. |
| EngravingGNN: J-Pop staff 97.6, spelling 96.3, key 80.6, clef 96.2; romantic staff 91.9, spelling 93.5, key 50.5 | OK | Table 1 ([arXiv 2509.19412](https://arxiv.org/abs/2509.19412)) |
| Cluster and Separate voice F1 96.6 (J-Pop), 89.9 (romantic) | OK | The same EngravingGNN Table 1 rows cite them |
| Rubato (May 2026), CC BY-NC-ND (transcription 4.2) | OK | Submitted 2026-05-22, CC BY-NC-ND 4.0 ([arXiv 2605.24291](https://arxiv.org/abs/2605.24291)) |
| Dual evaluation (Aug 2026): "MIDI2ScoreTransformer leads on notation, MuseScore on playback" (transcription 4.2) | UNVERIFIED | The paper exists (2026-08-05). Its abstract speaks of 24 pipelines and CLEWS, and does not name those two systems ([arXiv 2608.04511](https://arxiv.org/abs/2608.04511)). Not used by the plan. |
| W3C Web MIDI `timeStamp` (tempo lane 1.7, plan LR16) | OK | "the time the message was received by the system". The spec is a W3C **Working Draft**, 2025-01-21 ([W3C](https://www.w3.org/TR/webmidi/)). How Chrome on Windows stamps it was not found in a primary source, so the TM-D drill (LR16) is the right gate. |

### 1.3 Prior art

| Claim | Verdict | Evidence |
|---|---|---|
| ScoreCloud "does not know what your foot is tapping"; click track for MIDI; sustain pedal unpredictable | OK, **and one omission** | The FAQ also points audio users to a **Tap Beat** feature, and warns about "extensive use of sustain pedal" ([FAQ](https://scorecloud.com/support/)). Tap Beat is prior art for C3. |
| MuseScore issue 28402 (quantization options), June 2025 | OK | Opened 2025-06-13, still open ([issue](https://github.com/musescore/MuseScore/issues/28402)) |
| Logic Pro Smart Tempo as the "tempo map follows the player" precedent | OK, **incomplete** | Logic also has **Beat Mapping**: you connect notes of a free recording to ruler positions, and Logic inserts tempo events to match. This is exactly the "click a note, this is 1 / this is beat 3" tool the clean copy lacks ([Apple, beat mapping MIDI regions](https://support.apple.com/en-nz/guide/logicpro/lgcp46a73246/10.7/mac/11.0); [overview](https://support.apple.com/en-gb/guide/logicpro/lgcp624214db/10.7/mac/11.0)). |
| KeyLab 88 mk3 has only a sustain pedal in use | New fact | The mk3 has **four** pedal sockets: Sustain, Expression, Aux 1 and Aux 2, all assignable to CCs or note commands ([Sound On Sound review](https://www.soundonsound.com/reviews/arturia-keylab-88-mkiii)). This makes a hands-free tap possible (C4). |

### 1.4 Repository claims

| Claim | Verdict | Evidence |
|---|---|---|
| `noteOn` stamps `clock()` in the handler | OK | `piano.js` 1976. Line numbers have drifted by about 8-10 lines under the jam build's edits, so re-read before LS6. |
| Overlay layers are Canvas2D uploaded as `CanvasTexture`, which REC records | OK | `makeLayer` 1197-1212; `recorder.js` captures the canvas and counts `skipped` |
| Page font face is `Bravura` from `@vexflow-fonts/bravura@1.0.2` | OK | `BRAVURA_URL` 1163, `FontFace("Bravura", …)` 1168, with a 9 s timeout and a Noto Music fallback |
| `spellForKey` reads `theoryUi.minor` | OK | 1851-1854 (the move in LS6 must thread it through) |
| Tap rule: 4 taps, 40-200 bpm, 2 s reset | OK | `deck.js` 43-44 `TEMPO` |
| `tempomap.js` exports `tEpoch`, `sessionTms` | OK | 70, 220 |
| `state/*` git-ignored at `.gitignore` 122; `AREA_MIN_MS` 30,000; `ONSET_MERGE_MS` 40; `KINDS` | OK | `.gitignore` 122; `performance.py` 36, 41, 64 |
| "Now" staff and score share one speller, so they "cannot disagree" | FIX, partly (C17) | Spelling is shared, but staff placement is not. `drawStaff` splits at a fixed middle C (`n.midi >= 60` treble, 1451-1452), while the score uses a hand model. In 16:9 both are on screen and will put the same note on different staves. |

---

## 2. Against how Daniel plays

New scratch numbers: `critic_stats.out`, `critic_pedal.out`. Ranges are over 13 sessions.
- **Caveat on hands.** "Hand" is a crude split at C4.
- **Caveat on the quarter.** The rough quarter is the modal onset gap (120-600 ms) doubled and folded into 55-110 bpm, which gives 71-100 bpm per session, in line with the lanes' 70-94.

These are proxies, not transcriptions. They bound how often a rule fires, not how a finished score reads.

| # | Measure | Range (median session) | Plan rule it tests |
|---|---|---|---|
| A | Successive onset-group gaps under 148 ms / under 100 ms | 7.5-33.5% / 5.3-20.4% (S12, 31 min: 33.5% / 19.9%) | Tape at 120 px/s. A Bravura black notehead is 1.18 staff spaces wide ([SMuFL glyphBBoxes](https://w3c.github.io/smufl/latest/specification/glyphbboxes.html); [smufl crate docs](https://docs.rs/smufl/latest/smufl/)), 17.7 px at s = 15, which is 148 ms of tape. |
| B | Notes whose release comes a 16th or more before the next onset in the same register (within 4 quarters) | 17.9-47.8% (26.6%) | Written end = release; rest unless gap < 16th |
| B' | The same, counted only for releases with the pedal down | 17.5-47.8% | Same |
| B'' | Releases that happen with the pedal down | 56.8-97.6% (91%) | Same |
| C | Non-empty beat windows with 5+ / 7+ onset groups | 0-22.3% (10%) / 0-3.2% | d ∈ {1, 2, 4, 3}; 5+ onsets force a collision and a `loose` beat |
| D | Bass notes (below C3) ended by the pedal: share; sounding length in quarters, median / p90; share longer than 4 quarters | 34-71%; 0.8-3.7 / 2.8-7.6; 3.3-42.6% (S3 18%, S12 21%) | Held bass extends to sound end |
| E | Notes at or above C4 that are 20+ velocity above the running median of the last 16 | 6.7-19.6% (11.8%); 4-43% of those are the top note of a group | Accent rule |
| F | CC64 crossing values: down median / range; up gaps under 50 ms; up gaps under 300 ms | 96-103 / 64-127; 0-2.5%; 72-99% | Pedal notch rule; half-pedal claim |

*Not reported:* a run and roll ambiguity count was computed without a pitch-monotonic test, so it is discarded.

### 2.1 Flags, each with the naive failure and the fix

1. **Pedalled durations produce a rest-littered page (B, B', B''). See C1.**
   - **Why it happens.** He lifts his fingers early and lets the pedal hold the sound, the normal technique for lush pedalled piano. The plan's legato fill only closes gaps under a 16th, so a quarter to half of his notes would be followed by a 16th or 8th rest in their voice.
   - **What pianists write.** Pedalled broken chords are written with each note lasting until the next note of its voice, with no rests; the pedal marking carries the ring. Dorico's "fill gaps" is the same move (transcription lane source).
   - **Fix.** If the pedal is down at the release (or at any time before the next onset in the voice), set the written end to the next onset in that voice, capped at the bar line and at the next pedal lift. Write a rest only where `sound_end` comes before the next onset.
   - **Receipt.** Add rests per voice per bar to LR8, for example median ≤ 1 in pedalled bars.
2. **Dense arpeggio beats fall outside the alphabet (C). See C2.**
   - At his tempos, a beat with 6 onsets is a 16th-note sextuplet or a 32nd figure. The plan's `loose` export snaps those onsets to the nearest 16th with `<chord/>` collisions, which writes separate notes as a chord: wrong notation, not just untidy.
   - **Fix.** Add d = 6 (λ between λ[4] and λ[3], to tune on fixtures), and add sextuplet arpeggio fixtures to LS0. Consider d = 8 for 32nds, which TPQ 24 also holds (3 ticks).
   - Keep `loose` for 5 and 7 per beat, and export those as a tuplet only in the clean copy after a check.
   - **Caveat.** Beat windows here use a rough quarter, so some of these beats may really be two beats at half the tempo. If LS1 finds that, the ×2 button is the fix, not d = 6.
3. **Tape collides in fast passages (A). See C6.**
   - At 120 px/s, a third of successive onsets in S12 are closer than a notehead's width. With no stems or beams to organise them, overlapping heads read as clusters.
   - **Fix.** Tape should be proportional with a collision push: each onset column takes at least about 1.4 staff spaces, time is warped locally and restored after the passage, and a faint tick every second keeps time readable.
   - **Receipt.** Overlapping heads per minute in LR11a.
4. **Held bass ties across bar lines (D). See C7.**
   - A fifth of pedal-ended bass notes in the two long sessions ring past a full 4/4 bar, some past two. Held to sound end, each becomes a tie chain.
   - **Fix.** Cap the written end at the next lowest-voice onset and at the bar end. Allow at most one tie into the next bar, and only when that bar has no bass onset before beat 3. The pedal line carries the rest.
5. **Accents mark the melody (E). See C8.**
   - He voices the top line louder, which is correct playing, not accenting. A +20 rule over the hand median marks about 1 note in 8 in the upper register, and in some sessions a third to 43% of those are the top notes of chords.
   - **Fix.** No accents in v1; or measure against the running median of the same voice, at +25 or more with a 2-note minimum gap. Add accents per minute to LR8.
6. **Triplet feel under the 4/4 default. See C11.**
   - The cost table gives triplets the largest simplicity penalty (λ[3] = 2.0).
   - The meter suggestion chip needs `steady`, which is 0-12% of his time, so it will rarely appear.
   - A 6/8 or 12/8 ballad played with the 4/4 default will therefore be written with dotted-8th-16th and 16th figures instead of triplets, and the bar-back prior locks the mistake in.
   - The section 3 run did not test this case: its 12/8 pieces ran with the meter known and beats at the dotted quarter. It also used d ∈ {1, 2, 4, 3} for 12/8, not the plan's stated compound set {1, 3, 2} (`quant.mjs` line 93).
   - **Fix.** A per-session **feel** setting (straight or triplet) that swaps the simplicity table. A subdivision-only suggestion ("sounds like triplets?") driven by the tempo lane's grid-2 vs grid-3 test, without the `steady` gate, since that test does not need bar lines. A fixture where a 12/8 piece is quantized under 4/4.
7. **Live taps need a free hand. See C4.**
   - Rung 3 assumes he can press Tap and This is 1 while playing. With two hands on the keys and his right foot on the sustain, he can only tap before starting (a count-in).
   - Under rubato, the tapped period decays into rung 4 behaviour within bars. How fast is unmeasured: add an LS1 fixture "4 taps, then rub1 or rub2 for N bars" and report bars exact against N.
   - **Hands-free option.** A footswitch on KeyLab Aux 1 for the left foot, sending a CC mapped to tap, with a long press for "This is 1". Needs Daniel: it may be a purchase, and it touches `onMidiMessage` after the gate.
8. **Free time in saved files. See C3.**
   - LQ2's default (c) writes forced bars at the rough BPM for the clean copy. The plan's own numbers say those bars will mostly be wrong: rub2-like wobble, downbeat F 0.17, inferred coverage 24%, and ×1.5 level flips of 0.2-3.4 per minute. A MusicXML that "opens as normal sheet music" but has wrong bars is the "false autobiography" the rendering lane warns against.
   - **Fix.** Save take for any span without rungs 1-3 offers **"tap along"**: the take replays, he taps the beat on Space or the footswitch, taps are snapped to nearby onsets by the existing agents, and a note click in review mode sets "1". This is the clean pass's rung 3 with both hands free and full hindsight, and repeatable. Precedents: Logic Beat Mapping and ScoreCloud Tap Beat.
   - If he skips it, save `performance.mid` and `score.json` with tape measures, and write MusicXML bars only with every measure marked `freely` and `score.json` flagged `rhythm: unverified`.
9. **Pedal notches are clean; half-pedal is not in the data (F). See C5.**
   - The logged pedal has no flutter: up gaps under 50 ms are 0-2.5%, and 72-99% of lifts return within 300 ms, which confirms the "change notch" rule.
   - Because only crossings are logged, the notation rules are fine, but `performance.mid` cannot "keep half-pedal", and LR9b can compare only crossing times.
   - Logging continuous CC64 is a `log.js` change (jam-held) and a Daniel decision, since it changes new sessions.

---

## 3. Internal errors in the plan

- **C13, TPQ rationale.** "12 cannot hold the 12/8 duplet" is wrong.
  - At 12 per quarter a dotted quarter is 18 ticks, so a duplet eighth is 9 ticks, an integer.
  - The "(9)" listed under TPQ 24 is actually a 12/8 **quadruplet 16th** (36 ÷ 4).
  - TPQ 24 is still the right choice, because it holds 32nds (3 ticks), sextuplets (4) and compound quadruplet 16ths (9), none of which 12 holds.
  - Fix the sentence; no design change.
- **C14, timing spread mapped to jitter rows.**
  - The transcription lane's 35-55 ms is the spread of a **gap** (two onsets). With independent per-note jitter σ, a gap's spread is √2·σ, so per-note σ is about 25-39 ms. That is an upper bound, because drift is included; cluster selection pulls the other way.
  - Interpolating the jitter sweep (live, oracle beats: 15 ms 99.7%, 30 ms 92.7%, 45 ms 65.0%) gives roughly **76-95% bars exact against a click, about 1 wrong bar in 4 to 1 in 20**. The plan says "1 in 3 to 1 in 14".
  - Still synthetic; LR15's learned σ decides.
- **C10, what "bars fully right" means.**
  - `quant.mjs` `score()` counts a bar exact when every **onset position** is right. Durations, rests, ties, voices, hands and spelling are not scored.
  - Section 0 should read "bars with every onset in the right place".
  - LR4f ("≥ 0.95 exact inside matched intervals") conditions on the tracker's beats already matching the truth within 70 ms. It passes even if rung 4 is mostly at the wrong level or phase.
  - **Add LR4i:** of the bars actually **shown** metrically from rung 4 on fixtures, the share whose bar lines and onsets are right, with level and phase errors counted as wrong. That is the precision Daniel sees.
- **Downbeat F is not a rate.** "Inferred downbeats are right only 17% of the time" (section 0) should be "downbeat F-measure 0.17".
- **Section 3's taps model is iid ±30 ms per beat.** Count-in taps followed by tracking fail differently: the error grows over bars, not independently per beat. The 97.9% / 89.5% row describes the listener rung better than the tap rung (see flag 7).
- **C18.** Section 1's "97.3% onset F1 once beats are given" should say "ground-truth beats and downbeats, no noisy-beat test".

---

## 4. Rendering and frame checks

- **C15, dense bars do not fit fixed 96 px beats.**
  - At s = 15 a 16th slot is 24 px = 1.6 staff spaces.
  - A black notehead is 1.18 staff spaces. An accidental needs about 1 more, and a second-displaced head another 1.18.
  - So a 16th-slot chord with an accidental or a second already overflows its slot, and his chords are lush (6-10 keys held, 11-24 semitone gaps).
  - VexFlow's Formatter squeezes into a fixed width; slot-placed `TickContext` avoids the shift but inherits the collisions.
  - LR11e measures notehead shift only. **Add a collision receipt**: overlapping glyph boxes per bar on the dense fixtures.
  - Let a settled beat grow to its content's minimum width, and accept the settle shift under the crossfade.
- **C16, TikTok frame.** Third-party 2026 safe-zone guides give margins of top 130 px, bottom 484 px and right 140 px on 1080 × 1920; TikTok itself says the zone varies ([Zeely guide](https://zeely.ai/blog/tiktok-safe-zones/); [Creamate guide](https://creamate.ai/en/blog/tiktok-safe-zone-guide)).
  - The 9:16 staff box (`LAYOUT` 1186: x 110-970, y 500-1100) is vertically safe.
  - The open bar sits right of the 70% playhead (x ≈ 712-970) and reaches past x 940 into the like and comment rail.
  - Keep the band's right edge at or left of 940 px. A full-width bottom band in 9:16 would sit under the caption zone below y 1436.
- **C17, "now" staff and score disagree on staves.** In 16:9 both are visible. Either hide the "now" staff while the score is on, or give `drawStaff` the hand model's split. Changing `drawStaff` is a jam-held edit and a visible behaviour change, so ask first.
- **C9, fonts.**
  - Gate `engraveBar` on `fontState.smufl`. Canvas `measureText` on an unloaded face returns fallback metrics, so the first bars would be laid out wrong.
  - Either call `VexFlow.setFonts("Bravura", "Archivo")` against the page's loaded faces without `loadFonts`, or set `VexFlow.Font.HOST_URL` to pinned `@vexflow-fonts/…@version/` paths before `loadFonts`.
  - Which text faces `setFonts` accepts in 5.0.0 is medium confidence; check in the LS5 lab.

---

## 5. What is missing

- **M1. A hands-free beat and "1" input** (flag 7): a left-foot Aux switch, or a count-in tap convention. The plan's rung 3 has no physical path mid-take.
- **M2. Tap along to the replay, and click a note as "1"**, in the clean copy (flag 8; Logic Beat Mapping, ScoreCloud Tap Beat). This is the missing rung for free playing, which is most of his playing.
- **M3. Pedal-aware written durations and a rest-density receipt** (flag 1).
- **M4. A feel setting (straight or triplet)** and a subdivision suggestion without the `steady` gate (flag 6).
- **M5. Readability receipts that match what he sees**:
  - rests per voice per bar;
  - accents per minute;
  - overlapping heads in tape and in settled bars;
  - precision of shown rung-4 bars (LR4i).

  Today's LR8 caps tuplets, ties and voices only.
- **M6. A lead-sheet view as a readability fallback.** His texture is a bass and a solo line a 3rd or 10th above it, and he plays by ear. Top voice plus chord symbols plus a bass note avoids the hands, voices, rests and dense-arpeggio failure surfaces entirely. It is in v2 item 6. It is worth offering to Daniel as the "readable on a phone" mode, since `harmony.js` already names the chords. It is not a replacement for the grand staff.
- **M7. A decision on the transcriber feed when the log is off.** `logged()` returns early when `perfLog` is null, when logging is off, or while the demo runs (`piano.js` 1934-1936). The transcriber calls must sit beside those calls, not inside the callback, and must copy the demo and cue exclusions.
- **M8. A replay-first lab bench.** LS5 assumes Web MIDI is shared across tabs (unverified). Make `events.jsonl` replay the lab's primary input and live MIDI a bonus, so LR11 never depends on it.
- **M9. Data questions for the log.** Log continuous CC64 (half-pedal), and log `ev.timeStamp` (already LR16). Both change new sessions, and both belong to `log.js`, which is jam-held.

---

## 6. Corrections that change the plan (ordered by impact)

| # | Section | Change |
|---|---|---|
| **C1** | 6.4 durations | Under the pedal, or while a note still sounds, fill to the next onset in the voice, capped at the bar line and the next pedal lift. A rest only where `sound_end` comes before the next onset. LR8 gains a rests-per-voice-per-bar cap. |
| **C2** | 6.4, 3, LS0, LR4 | Add d = 6 (and consider 8) to the v1 alphabet. Add sextuplet arpeggio fixtures. `loose` stays for 5 and 7. Re-run section 3 with them. |
| **C3** | 2.2, 8, LQ2, LS5/LS7 | Free takes: Save take offers tap-along replay plus click "1". Forced bars only if skipped, marked `freely` and flagged `rhythm: unverified`. Change LQ2's default from (c) to "tape live; tap-along for the saved copy". |
| **C4** | 2.1, 6.2 ladder, LQ | Rung 3 live means count-in taps or a left-foot Aux switch. Add a fixture measuring how long taps help under rubato. Ask Daniel about the footswitch (possible purchase). |
| **C5** | 7.4, LR9b | `performance.mid` carries CC64 crossings only (0/127 steps at the logged times). Drop "half-pedal kept". Continuous CC64 logging becomes a `log.js` decision. |
| **C6** | 2.1, 7.3, LR11a | Tape with a collision push (at least 1.4 staff spaces per column, local time warp, 1 s ticks). Receipt: overlapping heads per minute. |
| **C7** | 6.4 held bass | Cap at the next lowest-voice onset and the bar end, with at most one tie. |
| **C8** | 6.5 dynamics | Accents off in v1, or against the same voice at +25 or more. Accents per minute in LR8. |
| **C9** | 5.3 `piano.html`, 7.3 fonts, LQ1 | VexFlow fonts: no unpinned `loadFonts`. Reuse the page's `Bravura` face or pin `Font.HOST_URL`. Plan for the Academico text font or a substitute. Gate on `fontState.smufl`. LQ1 wording: "pinned, fonts included". |
| **C10** | 0, 3, LR4 | "Bars exact" means onset positions only. Add LR4i, precision of shown rung-4 bars. |
| **C11** | 6.3, 6.4, LQ3 | A feel setting (straight or triplet) and an ungated subdivision suggestion. A 12/8-under-4/4 fixture. Re-run the compound set as stated. |
| **C12** | 0 | State up front: without jam, song or taps, the live panel is mostly tape (steady 0-12% on his sessions). |
| **C13** | 1 (tick unit) | Fix the TPQ rationale (12 holds the 12/8 duplet; 24 holds 32nds, sextuplets and compound quadruplets). |
| **C14** | 3 point 2, 13 point 2 | Per-note σ ≈ gap spread / √2, 25-39 ms. Roughly 76-95% bars exact against a click. |
| **C15** | 7.3 geometry, LR11 | Collision receipt for dense bars; settled beats may widen to content. |
| **C16** | 7.3, LQ4 | Keep the score band inside the TikTok safe zone (right edge ≤ 940 px, bottom ≤ 1436 px in 9:16). |
| **C17** | 2.1, LS6 | "Now" staff vs score staff split: hide the "now" staff while the score is on, or share the hand split (ask first). |
| **C18** | 1 | 2604.22290 is oracle beats and downbeats, with no noisy-beat test. |
| **C19** | lanes | Transcription Q5 Verovio size (7.3 MB, not 1.2); tempo lane HMM row (43.6 / 13.7); OSMD "fork" → "depends on vexflow 1.2.93"; SMF type 0 vs 1 for `performance.mid`; rendering 4.5 "pedal bar from real CC64 values" → crossings only; rendering's reliance on `PedalMarking` (needs notes, cannot place a lagged change by time). |
| **C20** | 4.1, LS6 | The transcriber feed sits beside `logged()`, not inside it, with demo and cue exclusion copied (M7). |

### Suggested shape of the four questions after this pass

1. **LQ1:** VexFlow 5.0.0 core from jsDelivr, pinned **with its fonts pinned or shared with the page** (unchanged otherwise).
2. **LQ2:** When there is no steady beat, the live page shows tape. For the saved copy, would you rather **tap along to the replay** (and click the "1"), or accept forced bars marked `freely`? Also: would you use a **left-foot switch** on the KeyLab's Aux input to tap live?
3. **LQ3:** Meter is your setting, and add **feel: straight or triplet**. Do you count a slow ballad at about 70? Is 6/8 "in 2"?
4. **LQ4:** Score panel in REC, placed inside the TikTok safe zone.

Continuous half-pedal logging and the MIDI timestamp switch stay "decided after the drill" items (M9), not questions tonight.

---

## 7. Still unverified

- MuseScore 4.7 and Dorico 6 import of `<senza-misura/>`, cross-staff `<staff>` changes, and pedal `change` with `line="yes"` (LR10 by hand).
- VexFlow 5.0.0 Canvas format and draw time for 43-67-onset piano bars (LR11b), and whether `setFonts` accepts a page-loaded text face.
- Chrome on Windows: when `MIDIMessageEvent.timeStamp` is stamped, and whether Web MIDI input is shared across tabs (LR16, M8).
- How long count-in taps keep a usable grid under his rubato (flag 7 fixture).
- How accurately a player taps along to his own rubato replay. It is expected to be better than live taps, but no primary number was found here; measure it in LS9 (tapped take against the jam-click take).
- Whether the section 2 proxies (C4 hand split, rough quarter) over- or understate. Re-measure A-E with `hands.js` and the tracked beat once LS1-LS3 exist.

---

## Sources

**Checked for this pass**
- VexFlow registry: https://registry.npmjs.org/vexflow/latest
- VexFlow files: https://data.jsdelivr.com/v1/packages/npm/vexflow@5.0.0?structure=flat
- VexFlow getting started: https://vexflow.github.io/vexflow-examples/guides/getting-started/
- VexFlow `font.ts` (`HOST_URL`): https://github.com/vexflow/vexflow/blob/main/src/font.ts
- VexFlow `pedalmarking.ts`: https://github.com/vexflow/vexflow/blob/main/src/pedalmarking.ts
- VexFlow PR 1434: https://github.com/0xfe/vexflow/pull/1434
- VexFlow formatting wiki: https://github.com/0xfe/vexflow/wiki/How-Formatting-Works
- VexFlow TickContext API: https://0xfe.github.io/vexflow/api/classes/TickContext.html
- Verovio registry: https://registry.npmjs.org/verovio/latest
- Verovio files: https://data.jsdelivr.com/v1/packages/npm/verovio@6.3.0?structure=flat
- OpenSheetMusicDisplay registry: https://registry.npmjs.org/opensheetmusicdisplay/latest
- MusicXML 4.0 `senza-misura`: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/senza-misura/
- MusicXML 4.0 `pedal`: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/pedal/
- W3C Web MIDI (Working Draft 2025-01-21): https://www.w3.org/TR/webmidi/
- Wachter, Murgul, Heizmann 2026: https://arxiv.org/abs/2604.22290 and https://arxiv.org/html/2604.22290
- Murgul and Heizmann, SMC 2025: https://arxiv.org/html/2507.00466
- PM2S, ISMIR 2022: https://www.turing.ac.uk/sites/default/files/2022-09/midi_quantisation_paper_ismir_2022_0.pdf
- McLeod and Steedman, ISMIR 2018: https://apmcleod.github.io/pdf/ISMIR_Meter.pdf
- EngravingGNN: https://arxiv.org/abs/2509.19412
- Rubato: https://arxiv.org/abs/2605.24291
- A Dual Evaluation for Music Transcription: https://arxiv.org/abs/2608.04511
- ScoreCloud FAQ: https://scorecloud.com/support/
- MuseScore issue 28402: https://github.com/musescore/MuseScore/issues/28402
- Logic Pro beat mapping (MIDI regions): https://support.apple.com/en-nz/guide/logicpro/lgcp46a73246/10.7/mac/11.0
- Logic Pro beat mapping overview: https://support.apple.com/en-gb/guide/logicpro/lgcp624214db/10.7/mac/11.0
- KeyLab 88 mk3 review, Sound On Sound: https://www.soundonsound.com/reviews/arturia-keylab-88-mkiii
- SMuFL glyphBBoxes: https://w3c.github.io/smufl/latest/specification/glyphbboxes.html
- smufl crate docs: https://docs.rs/smufl/latest/smufl/
- TikTok safe zones, 2026 (third-party): https://zeely.ai/blog/tiktok-safe-zones/
- TikTok safe zones, 2026 (third-party): https://creamate.ai/en/blog/tiktok-safe-zone-guide

**Repository** (read only)
- `arsenal/web/piano.js`: `BRAVURA_URL` 1163, `loadFonts` 1166, `LAYOUT` 1183, `makeLayer` 1197, `drawStaff` 1393 (C4 split 1451), `spellForKey` 1851, `logged` 1934, `noteOn` 1974, `setSustain` 2025, `onMidiMessage` 2727 (CC64 ≥ 64, 2738), test hook `timeStamp` 3700
- `arsenal/web/piano/log.js` 600-604 (`pedal(down, value, t)`)
- `arsenal/web/piano/deck.js` 43
- `arsenal/web/piano/tempomap.js` 70, 220
- `arsenal/web/piano/recorder.js` (`skipped`)
- `arsenal/performance.py` 36, 41, 64, 336
- `.gitignore` 122

**Scratch** (untracked)
- `scratchpad/sheet/critic_stats.py` / `.out`
- `scratchpad/sheet/critic_pedal.py` / `.out`
- The plan's `quant.mjs` (read for the metric definition)
