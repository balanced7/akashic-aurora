# Live sheet music on /piano: the buildable plan

| | |
|---|---|
| Date | 2026-09-14 |
| Status | Research and design. Nothing under `arsenal/` edited: a jam build holds `piano.js`, `piano.html`, `piano.css`, `log.js`, `cues.js` and `serve.py` tonight (git status at writing). No server, browser, download, install or login. |
| Asked for | Daniel, verbatim: "what if we keep a rough estimate of bpm and make it possible to save the notes i am playing into something that can render into sheet music with correct notation in real time, I wonder if we can make that happen!" |
| Built from | The three lanes in this folder: `tempo-meter.md` (beat, BPM, meter), `transcription.md` (notes to notation), `rendering-formats.md` (drawing and export). Also the code they cite, re-read for this plan (`piano.js` overlay, staff, `spellForKey`, `noteOn`, `onMidiMessage`; `log.js`; `performance.py`; `nashville.js`; `tempomap.js`; `deck.js` tap; `recorder.js`), and the sibling designs `practice-along-2026-09-14/practice-along-plan.md` (listener beat) and `piano-theory-nextgen-2026-09-14/theory-nextgen-spec.md` (`harmony.js`). |
| New measurement | A per-beat quantizer run on 81 synthetic performances with known rhythm, under three beat sources (section 3). Scratch only, untracked: `C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/sheet/quant.mjs`, output `quant.out`. It reuses the tempo lane's `tracker.mjs`. No session content was used for it. |
| Labels | Slices **LS0-LS9**, receipts **LR1-LR16**, questions **LQ1-LQ4**. Labels from the lanes (T, TM, SM, SR, D, G, Q) are cited as sources only. Sessions are S1..Sn as the lanes numbered them. |

---

## 0. In one screen

**Yes, and it can be built mostly in new files, starting before the jam build finishes.**

- **Saving the notes is already done.** The practice log keeps every key down and up, velocity, pedal and sound end to the millisecond (`performance.py` kinds `on/off/pedal/chord/sound_end`). So a take, a moment, or any past session can become sheet music.
- **A rough BPM is easy. Bar lines are the hard part.**
  - The tempo lane's tracker locks at a median of 70-94 bpm on his sessions.
  - His beat-to-beat wobble matches strong synthetic rubato, where inferred downbeats are right only 17% of the time.
- **Once a beat is known, the rhythm is mostly right** (new measurement, section 3). Per-beat quantization on synthetic playing:
  - **99.4%** of onsets exact and **96.6%** of bars fully right when the beat is given, as with a jam loop;
  - **97.9% / 89.5%** with beats off by ±30 ms, as with taps or the song listener;
  - **98.6% / 92.7%** at ±30 ms of note jitter and **92.2% / 65.0%** at ±45 ms. His measured timing spread (35-55 ms per gap, drift included) sits in that band.
  - The inferred beat covers only **44%** of the notes, and 24% under strong rubato. The rest must be shown honestly as unmetered.

**What v1 is:**

1. **A score panel** in the overlay, drawn inside the WebGL canvas so REC captures it:
   - a rolling grand staff with a rough-BPM header (`♩ ≈ 84 · loose · heard`) and the meter;
   - bars that stay light while provisional and freeze 4 beats after they end;
   - spelling through the page's own speller in the tracked key, two staves split by a hand model, and pedal brackets with change notches;
   - **tape** (notes placed by time, no rhythm claimed) wherever no trustworthy beat exists.
2. **The beat-source ladder:**
   1. the jam tempo map;
   2. the song listener's beat;
   3. his taps plus "This is 1";
   4. the inferred beat;
   5. free time.

   Meter is **his setting** (4/4 default, one tap to change); the page only suggests a change.
3. **Save take** writes `take.musicxml`, `performance.mid` (raw times, 1 tick = 1 ms) and `quantized.mid` (on the grid, following his tempo map). They are written by in-house code with no dependencies, and always come from the **clean pass**.
4. **The clean pass** re-runs the same code with full hindsight, for a take, a moment (`--at 3:43 --seconds 30`) or a whole session, from a Node CLI or the page.

**Rendering:** a hybrid (section 7).
- **Our own Canvas2D painter** draws what changes often or claims no rhythm: tape, the open bar's noteheads, pedal line, words, BPM header.
- **VexFlow 5.0.0 core** (MIT, 336,625 B, Canvas backend) engraves each bar once its rhythm is decided. That needs Daniel's OK (LQ1); if he says no, our painter takes that job with a reduced notation set.

**Order:**
- **LS0-LS5** are new modules, Node tests, a CLI and a lab page. They touch none of the jam build's files and can start now.
- **LS6-LS9** edit `piano.js`, `piano.html`, `piano.css`, `serve.py` and later `log.js`, only after the jam build commits and releases them (section 5.3).

**Four questions** are in section 12. In short: VexFlow yes or no, what free time looks like, meter and counting, and whether the panel goes into recordings.

---

## 1. What the lanes settled, and the calls this plan makes where they disagreed

| Topic | Lanes said | This plan | Why |
|---|---|---|---|
| Beat ladder | All three agree: jam → song → taps + "This is 1" → inferred → free | **Adopt** | Beats first, then notation: the 2026 beat-conditioned quantizer gets 97.3% onset F1 once beats are given ([arXiv 2604.22290](https://arxiv.org/abs/2604.22290)). |
| Inferred tracker | Transcription T2.2: one Large-Kolen oscillator. Tempo lane: IOI induction + up to 24 competing agents (BeatRoot, causal). | **Agents** | His dominant error is the beat level (×1.5 flips 0.2-3.4/min). Only runner-ups can feed ÷2 / ×2 / "2↔3" buttons. Cost is 0.05 ms per 250 ms tick (S12 whole session 403 ms in Node). |
| Steadiness word and free-time entry | Transcription: grid-fit share < 0.5. Tempo lane: IOI periodicity strength. | **Periodicity strength** (≥ 4.5 steady, 3-4.5 loose, < 3 free, 2 s hysteresis); grid fit may only lower the word | Grid fit reads random notes (0.62) the same as strong rubato (0.60); the old "lock" rule calls random playing locked 62% of the time. |
| Meter | Transcription Q6: auto 3/4 and 12/8. Tempo lane D1: his setting, suggestions only. | **His setting**, suggestion chip only after margin 0.15 R², 8 decisions, steady | On his sessions the auto label follows a 0.05 tie-break (6/8 wins 58-100% with it; 4/4 and 12/8 split without). McLeod's live metrical F is about 57 ([ISMIR 2018](https://apmcleod.github.io/pdf/ISMIR_Meter.pdf)). |
| Tick unit | Transcription: 12 per quarter. Rendering: 840. | **24 per quarter** (`TPQ = 24`), a field in the score JSON | 24 holds 16ths (6), triplet 8ths (8), triplet 16ths (4), 32nds (3) and **12/8 duplet eighths** (9). 12 cannot hold the 12/8 duplet. Quintuplets (v2) need 120 or 840; the field makes that a constant change. MusicXML `<divisions>` = 24. |
| Live renderer | Transcription Q5: no vendoring, extend our Canvas2D. Rendering: VexFlow 5 core on the Canvas backend. | **Hybrid** (section 7): our painter for tape, the open bar, pedal and words; VexFlow for settling and settled bars; fallback to our painter alone if LQ1 is no | The open bar changes at up to 8 Hz and has no decided rhythm, so drawing stems and beams there claims a rhythm not yet decided. Settled bars need beams, tuplets, ties, rests, dots and two voices, which VexFlow has solved. |
| Export writer home | Rendering: Python for regeneration, JS for "save now". Transcription: JS, one engine. | **JS only**: `score/musicxml.js` and `score/midi.js`, run in the page and by `arsenal/score_cli.mjs` under Node | One engine for live, clean and export (theory-nextgen D1). Regeneration is the CLI re-run. Tests that read the output back use Python stdlib as an independent reader. |
| Where exports live | Rendering: `state/arsenal/performance/<session>/export/` | **`state/arsenal/score/<session>/<take>/`** | Keeps `PerformanceStore`'s directory contract untouched. `state/*` is git-ignored (`.gitignore` line 122), so the folder stays private. |
| Live vs clean | All: the log is the truth; live and clean are separate views; settled bars never move live | **Adopt**, and exports always come from the clean pass | Dorico and Logic keep notation separate from played data. |
| Timestamps | Tempo lane: log the MIDI event's `timeStamp` after a drill | **Deferred decision** after drill TM-D (LR16) | `noteOn` stamps `clock()` inside the handler (`piano.js` 1968). ±25 ms of jitter moves the chosen beat level on up to 69% of readouts. |

---

## 2. What Daniel sees (v1)

### 2.1 The panel

```
 ♩ ≈ 84 · loose · heard            4/4                         (recorded, inside the canvas)
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ 𝄞 ♭♭ │ settled bar │ settled bar │ settling (light ink) │ open bar ● ● │
 │ 𝄢 ♭♭ │ ...         │ ...         │ ...                  │ heads by slot│
 │  Ped.└──────∧───────────────∧───────┘                                   │
 └─────────────────────────────────────────────────────────────────────────┘
 HUD (not recorded):  [÷2] [×2] [2↔3] [Tap] [This is 1] [4/4 ▾] [Score: off|tape|bars] [Save take] [Clean last take]
```

- **Header** (drawn in the canvas):
  - `bpmShown` changes at most once a bar and only by 3 bpm or more (T2.3).
  - The word is `steady | loose | free | hold` (periodicity bands; hold is dimmed).
  - The source is `jam | song | tap | heard`.
- **Settled bars** are full ink, one texture tile each, scrolling left. They never repaint.
- **The settling bar** (from its end until 4 beats later) is light ink. It may re-engrave when a later beat changes it, at most 8 times a second.
- **The open bar** shows noteheads at their provisional slot inside fixed-width beats, with a faint beat tick. There are no stems or beams until the beat closes.
- **Tape** replaces bars wherever the ladder has no trustworthy beat: a rung-4 beat reading `loose` or `free`, or `hold` after a pause.
  - Noteheads sit by time at a fixed px per second, with a thin duration line to sound end.
  - There are no stems or bar lines, and a small `freely` marks it.
  - Spelling, staves and pedal still apply.
- **Pedal:** one continuous bracket line along the panel bottom, with a notch at every change. It is drawn by our painter across tiles, by time, so it never needs a cross-tile object.
- **Controls live in the HTML HUD**, so they are never recorded.
  - The tap control reuses the `deck.js` rule: 4 taps, median gap, 40-200 bpm, reset after 2 s. A tap within 8% of a live hypothesis selects it; otherwise it re-seeds the agents.
  - "This is 1" sets the bar phase at the nearest settled beat.

### 2.2 Save and clean

- **Save take.** A take is the span since REC started if recording, otherwise since the last silence of 10 s or more (capped at 10 min). Saving runs the clean pass over that span and writes three files plus `score.json`:
  - after LS7, through a new server route into `state/arsenal/score/<session>/<take>/`;
  - before LS7, or when the route is missing (the same check `log.js` does), as a browser download.
- **Clean last take** opens the clean copy in the panel's review mode, paused and scrollable, in place of the live strip.
- **CLI, available from LS4 with no page change:**
  - `node arsenal/score_cli.mjs clean <session|latest> [--at 3:43 --seconds 30] [--meter 3/4] [--one 12.40] [--bpm 70]`
  - `node arsenal/score_cli.mjs export <session|latest> ...`
  - Both read `state/arsenal/performance/<session>/events.jsonl` directly, the way `practice_theory.mjs`-style tools run beside the page.

---

## 3. New measurement: per-beat quantization on synthetic performances

**Why.**
- The tempo lane measured beats and the transcription lane measured grid fit and settle churn on his logs.
- Neither measured **rhythm accuracy against a known score**, which the receipts need.

**Method** (scratch `quant.mjs`).
- **Scores.** 81 pieces × 24 bars:
  - meters 4/4, 3/4, 12/8 (dotted-quarter beat);
  - textures: ballad (bass, rolled triad, melody), arpeggio (broken bass under a sparse melody), mixed (melody with off-beat left-hand dyads);
  - 3 rubato levels × 3 seeds;
  - tempo 60-100 bpm, and 45-70 for 12/8.
- **Rhythms.** Per-beat patterns: quarter, two 8ths, rest-8th, four 16ths, dotted-8th-16th, 8th-two-16ths, two-16ths-8th, triplet, triplet with a rest, and an empty beat. 12/8 uses the compound set. A bar repeats the previous bar's patterns half the time, for his loops.
- **Tempo curves and jitter** are the tempo lane's rub0/1/2:
  - rub1: ±4% swell and ±6% drift;
  - rub2: ±10% swell, ±12% drift, ritardando and fermata stretches;
  - note jitter σ 10/20/30 ms by level;
  - bass leads 0-20 ms; rolls of 20-60 ms.
- **Grouping.** 40 ms chords, plus a near-chord rule: a note ≤ 60 ms after a group joins it when it is 7+ semitones outside the group's range.
- **Quantizer** (transcription T3 cost, lane parameters, **not tuned here**). Per beat, pick d ∈ {1, 2, 4, 3} minimizing:
  - the timing fit Σ((f − k/d)·P)²/2σ²;
  - plus simplicity λ = 0 / 0.5 / 1.5 / 2.0;
  - plus 0.8 if d differs from the previous non-empty beat;
  - plus 0.8 if it differs from the same beat one bar back;
  - plus 6 per slot collision.

  Onsets past 0.875 of a beat belong to the next beat. σ starts at 40 ms and adapts, as an EMA of squared residuals with weight 0.05, clamped to 15-60 ms.
- **Variants:**
  - *naive* snaps each onset to the nearest of {0, ¼, ⅓, ½, ⅔, ¾, 1} beat;
  - *no priors* sets both 0.8s to 0;
  - *live* is greedy and causal;
  - *clean* is a Viterbi over divisions with the bar-back prior from the previous pass, run twice.
- **Beat sources:**
  - *oracle* = the true beat curve (the jam rung);
  - *±30 / ±45 ms* = the true beats plus gaussian error (the taps and listener rungs);
  - *inferred* = `tracker.mjs` lag-2 settled beats with the tempo lane's recommended configuration.
- **Evaluation for inferred beats.** Only onsets inside tracker intervals whose two ends each match consecutive true beats within 70 ms are counted, and that share is reported as coverage.
- **Metrics.** Onsets exact (tick position equals truth), beats exact (every onset of the beat right), bars exact. The first 5 s are skipped. Durations were **not** measured.

**Results** (onsets exact / bars exact; `quant.out`)

| Beat source | Variant | All 81 | rub0 | rub1 | rub2 |
|---|---|---|---|---|---|
| Oracle (jam) | naive nearest grid | 98.3% / 88.9% | 100 / 100 | 99.1 / 93.9 | 95.8 / 72.9 |
| Oracle | per beat, no priors | 99.1 / 94.9 | 100 / 100 | 99.8 / 99.0 | 97.4 / 85.6 |
| Oracle | **per beat + priors (live)** | **99.4 / 96.6** | 100 / 100 | 99.9 / 99.2 | **98.2 / 90.6** |
| Oracle | clean (Viterbi) | 99.4 / 96.6 | 100 / 100 | 99.8 / 98.8 | 98.4 / 91.1 |
| Beats ±30 ms (taps, song) | live / clean | **97.9 / 89.5** · 98.1 / 90.3 | 99.6 / 97.4 | 98.1 / 91.1 | 96.1 / 80.1 |
| Beats ±45 ms | live / clean | 94.6 / 76.8 · 94.9 / 78.8 | 97.4 / 87.0 | 94.9 / 79.9 | 91.4 / 63.7 |
| Inferred (tracker lag 2) | live, inside matched intervals | 97.4 exact; **coverage 44.3%** | coverage 64.9% | 43.8% | **24.2%** |

By meter, the inferred coverage is 4/4 56.8%, 3/4 57.9% and **12/8 18.2%**: the tracker often counts the 12/8 at another level. With oracle beats, bars exact are 4/4 96.5%, 3/4 96.2% and 12/8 97.1%.

**Jitter sweep** (rub1 tempo, oracle beats; onsets exact / bars exact)

| Note jitter σ | Naive | Per beat + priors (live) | Clean | Live with beats ±30 ms |
|---|---|---|---|---|
| 15 ms | 99.8 / 98.4 | 99.9 / 99.7 | 99.9 / 99.5 | 99.3 / 95.9 |
| 30 ms | 96.3 / **75.3** | 98.6 / **92.7** | 98.7 / 93.5 | 96.1 / 80.5 |
| 45 ms | 88.8 / **40.0** | 92.2 / **65.0** | 92.5 / 67.6 | 89.2 / 53.8 |
| 60 ms | 79.9 / 20.6 | 82.0 / 36.9 | 82.8 / 39.1 | 78.0 / 24.8 |

**Compute** (Node): live quantizer **0.002 ms per bar**, clean **0.007 ms per bar**. Rendering will dominate the budget, not transcription.

**What the numbers say.**

1. **With a real beat, rhythm is mostly right, and the per-beat priors earn their place** once timing loosens. At 30 ms jitter, bars exact rise from 75% (naive) to 93%; at 45 ms, from 40% to 65%.
2. **His timing spread decides the ceiling even with a click.** The transcription lane measured a per-gap spread of 35-55 ms at his eighth, drift included. Against a jam loop the per-note jitter is probably in the 30-45 ms rows: roughly **1 wrong bar in 3 to 1 in 14**. So the clean copy needs a quick per-beat fix (v2 section 11, "cycle the runner-up"), and the drill must measure his real residual σ (LR15).
3. **The clean Viterbi adds almost nothing when beats are fixed.** Live and clean disagree on 0.2% of onsets. The clean copy's value is the **beat tidy** (non-causal tempo map, meter per phrase, "1" in hindsight), not a smarter division choice.
4. **The inferred rung notates under half of synthetic playing metrically,** and a quarter under strong rubato. What it notates is 97% right. Tape for the rest is the honest design, not a stopgap.

**Caveats.**
- All rhythms come from a small alphabet that the quantizer can express. Real playing includes figures outside it: quintuplets, a quarter-note triplet across beats, grace-like pickups.
- Jitter is independent per note; real hands drift together.
- Parameters were not tuned. Durations, hands and spelling were not tested.
- The numbers bound what the design can do on clean input. They say nothing about Daniel until LR15.

---

## 4. Data flow

### 4.1 Live

```
KeyLab MIDI ──► piano.js onMidiMessage(ev) ──► noteOn(m, vel) / noteOff(m) / setSustain(down, value)
                                                  │  t = clock()  (page seconds; T0 + t = performance.now()/1000)
                     ┌────────────────────────────┼──────────────────────────────────────────────┐
                     ▼                            ▼                                              ▼
         log.js (practice log, as today)   transcriber.noteOn/noteOff/pedal/soundEnd       harmony.js (TN2, when it lands)
         t_ms = perf_ms − meta.t0_perf_ms  (perf ms; Daniel's sources only: the same         window starts ──► transcriber
                                            places logged() is called, never demo, cues,
                                            replays or ghosts)
                                                  │
    beat sources, read at tick:                   ▼
      jam: tempomap segments + ack   ──►  transcriber.tick(perfMs, { keyView, beatSources })   (renderer calls it once per frame;
      song: listener state().beat    ──►     T1 onsets → T2 beat ladder + bands + meter →      it does work only when an onset
      taps / This is 1 (HUD)         ──►     T3 per-beat division → T4 bars → T5 hands →       group, a beat or a bar boundary
      inferred: beat.js agents              T6/T8 pedal, dynamics → T7 spelling → T9 settle     is new; event time, not timer time)
                                                  │
                                                  ▼
                           { header: {bpm, word, source, family, meter}, changed: [bar...], view }
                                                  │
                                                  ▼
                 piano.js overlay: score layer family (one tile per bar in overlayScene, tape tiles, header layer)
                     paint.js (tape, open bar, pedal line, words)   engrave.js (VexFlow, settling/settled bars)
                     tile.tex.needsUpdate only for changed bars; scroll = mesh position.x per frame
                                                  │
                                                  ▼
                              WebGL canvas ──► recorder.js (captures the canvas) ──► REC MP4
```

- **Timebase.**
  - The transcriber runs on `performance.now()` milliseconds.
  - Every score note keeps `perf: { t_ms, note }` in the log's session time (`t_ms = perf_ms − log.timebase().t0_perf_ms`). The live score, the clean copy and `events.jsonl` therefore point at the same notes.
  - With the log disabled, `t_ms` counts from the take start.
- **Jam beats:** `tEpoch(segments, m, bar, beat)` goes to session time by `sessionTms` (jam spec 11.2, L1/L2 at 2 ms or better).
- **Listener beats:** `nextBeatPerf + k·periodMs` is already performance time.
- **Key:** `keyView` (`key`, `name`, `confidence`, `locked`) is read at tick. The key signature follows the tracker's non-provisional key (7.4 below).

### 4.2 Offline (clean pass, export)

```
state/arsenal/performance/<session>/events.jsonl  (or the page's in-memory take buffer: the same events)
   └─► score/index.js clean(events, { span, meter?, one?, bpm?, jam? })        (same modules, full lookahead)
         beat tidy (forward agents + backward pass, one meter per phrase split at holds; jam map if a run was live)
         → Viterbi divisions → measures → hands → spelling (closed session: summary.json key areas; else tracker replay)
         → marks → Score (kind "clean")
   └─► musicxml.js → take.musicxml      midi.js → performance.mid, quantized.mid      score.json
         written by score_cli.mjs (LS4) or the serve.py route (LS7) to state/arsenal/score/<session>/<take>/
```

- Old sessions work the same way, so every session on disk can become a score.
- The clean pass never overwrites a live score. Both are stored side by side (`score.live.json`, `score.clean.json`).

---

## 5. Module boundaries

### 5.1 New files (all pure unless marked; Node-testable; no DOM or clock inside)

| File | Stage | Exports (sketch) | Depends on |
|---|---|---|---|
| `arsenal/web/piano/score/onsets.js` | T1 | `createOnsets()`: chords 40 ms, near-chord ≤ 60 ms with 7+ semitone register gap, rolls, grace candidates, runs | none |
| `arsenal/web/piano/score/beat.js` | T2 | `createBeatTracker(params)`: IOI induction, periodicity strength, agents, family, readout, hold, lag-2 settle; `ladder(sources)` | `tempomap.js` (read-only import of `tEpoch`, `sessionTms`) |
| `arsenal/web/piano/score/meter.js` | T2.4 | meter state (his setting), suggestion scorer (tatum templates), bar phase, pickups | `beat.js` output; harmony window starts when available |
| `arsenal/web/piano/score/quantize.js` | T3 | `divideBeat(items, P, ctx)`, `createLiveQuantizer()`, `cleanDivisions()` (Viterbi) | `beat.js` |
| `arsenal/web/piano/score/measures.js` | T4 | bars, ties, dots, beaming groups, tuplets, rests, fermata or rest completion | `quantize.js` |
| `arsenal/web/piano/score/hands.js` | T5 | split DP, 2 voices per staff, clef, 8va/8vb | none |
| `arsenal/web/piano/spell.js` | T7 | **`spellForKey(info, key, opts)` moved out of `piano.js` unchanged** (it reads `theoryUi.minor`, which becomes `opts.minor`), plus score helpers: key signature hysteresis, accidentals, courtesy | `nashville.js` `spellInKey`; `Theory` passed in |
| `arsenal/web/piano/score/marks.js` | T6, T8 | pedal brackets and notches, dynamics bands, accents, tempo words, chord symbols (reader names) | `harmony.js` windows when available |
| `arsenal/web/piano/score/settle.js` | T9 | bar states open → settling → settled, `rev`, forward-only corrections | the above |
| `arsenal/web/piano/score/index.js` | all | `SCORE_API = "arsenal.piano.score/v0"`, `createTranscriber(opts)`, `clean(events, opts)` | the above |
| `arsenal/web/piano/score/musicxml.js` | T10 | `toMusicXML(score) → string` | score JSON |
| `arsenal/web/piano/score/midi.js` | T10 | `performanceMid(events)`, `quantizedMid(score) → Uint8Array` | score JSON, events |
| `arsenal/web/piano/score/layout.js` | display | ribbon geometry: staff size, px per beat, tile widths, playhead, tape px per second, per framing | none |
| `arsenal/web/piano/score/paint.js` | display (Canvas2D; needs a 2D context only) | `paintTape`, `paintOpenBar`, `paintPedalLine`, `paintHeader`, `paintBarReduced` (fallback engraver) | `layout.js`; SMuFL codepoints shared with `piano.js` |
| `arsenal/web/piano/score/engrave.js` | display (Canvas2D) | `engraveBar(ctx, bar, geom, VF)`: VexFlow passed in as an argument, never imported | VexFlow global (LQ1) |
| `arsenal/score_cli.mjs` | offline | `clean`, `export`, `bench` over `events.jsonl`; writes `state/arsenal/score/...` | `score/*` |
| `arsenal/web/piano-lab-score.html`, `piano-lab-score.js` | lab | Web MIDI input, `events.jsonl` file picker for replay, a 2D canvas plus a WebGL canvas for the upload bench, G1 timings | `score/*` |
| `tests/fixtures/score/gen.mjs` | tests | synthetic generator promoted from scratch `tracker.mjs` + `quant.mjs`: meters, textures, rubato, pickups, fermatas, tempo steps, random unmetered; ground-truth score. **No session content.** | none |
| `tests/score_beat.test.mjs`, `score_quantize.test.mjs`, `score_hands.test.mjs`, `score_settle.test.mjs`, `score_export.test.mjs`, `test_score_export.py` | tests | receipts LR1-LR10 | fixtures |

### 5.2 Interfaces

```js
// score/index.js
createTranscriber({ spell, reader = null, harmony = null, params = {}, options = {} }) -> {
  noteOn(midi, vel, perfMs, source), noteOff(midi, perfMs), soundEnd(midi, perfMs, by), pedal(down, value, perfMs),
  tap(perfMs), thisIsOne(perfMs), setMeter("4/4" | "3/4" | "6/8" | "12/8" | "free"), chooseLevel(ratio /* 0.5 | 2 | 1.5 | 2/3 */),
  setOptions({ scoreMode: "off" | "tape" | "bars", pedalled: "played" | "sounding", heldBass: true, tpq: 24 }),
  tick(perfMs, { keyView, jam /* {segments, m, anchor} | null */, song /* listener state().beat | null */ })
    -> { header: { bpm, word, source, family: [{ratio, score}], meter, suggestion }, changed: [barIndex...], view },
  take(fromPerfMs, toPerfMs) -> events[],             // the in-memory take buffer for Save and Clean
}
clean(events, { span, meter, one, bpm, jam, keyAreas, spell, reader }) -> Score   // same code, full lookahead
```

- **`beatState`** is the tempo lane's section 6.1 contract, unchanged: source, mode, beats with `settled`, `period_ms`, `bpmShown`, family, meter, `barPhase`, pickup, holds.
- **Score JSON** is the transcription lane's T10 shape, with these amendments:
  - `tpq: 24`;
  - `pos` and `dur` in ticks of a quarter;
  - `measures[].source` (`jam | song | taps | inferred | free`);
  - `measures[].mode` (`steady | loose | free | hold`);
  - `measures[].kind` (`metric | tape`);
  - tape measures carry `notes[].t_ms` instead of `pos`.
- **`Take`** (rendering 5.1) is derived from the score JSON. It is not a second model.
- **`spell` is injected.**
  - The page passes `(info, key) => spellForKey(info, key, { minor: theoryUi.minor })` from `arsenal/web/piano/spell.js`.
  - Node tests and the CLI pass the same function, with `Theory` taken from the THEORY block the way `tests/nashville_js.test.mjs` extracts it.
  - There is one speller, so the staff, the chips and the Nashville row cannot disagree.

### 5.3 Existing files: what changes, and when

**The rule.** No edit to a file the jam build holds until that build has committed and `git status` shows the file clean. Then one owner at a time, with an advisory lock, per the fleet rule.

| File | Change | Slice | Gate |
|---|---|---|---|
| `arsenal/web/piano.js` | (1) Remove `spellForKey` and import it from `piano/spell.js`: no behaviour change. (2) Feed `noteOn`, `noteOff`, `setSustain` and sound-end points to `createTranscriber` beside each `logged()` call. (3) Add a score layer family in `overlay.build`/`update` (tiles like `makeLayer`, disposed like `disposeLayer`), a `LAYOUT` entry per framing, and a header layer. (4) Wire the HUD controls, Save take and Clean last take. (5) Load VexFlow fonts through the existing `BRAVURA_URL` face. | LS6 | Jam build released `piano.js`; LS5 lab receipts LR11 passed |
| `arsenal/web/piano.html` | The VexFlow `<script>` tag, pinned `https://cdn.jsdelivr.net/npm/vexflow@5.0.0/build/cjs/vexflow-core.js` (the guide shows it defines a global `VexFlow`), with a load-failure note like the three.js one. Only if LQ1 is yes. | LS6 | Same, plus LQ1 |
| `arsenal/web/piano.css` | HUD controls for the score | LS6 | Jam build released it |
| `arsenal/serve.py` | `POST /api/score/<session>/take` (body: span and options; the server runs nothing, it stores what the page's clean pass produced) and `GET /api/score/<session>` (list takes). Events for "clean a moment" of an old session come from the CLI, or from a small `GET /api/performance/<session>/events?from&to` (today's GET returns only the summary, `performance.py` 336). | LS7 | Jam build released it |
| `arsenal/web/piano/log.js` | Log the MIDI event's own `timeStamp` (converted with `T0`) instead of `clock()` at handler time | after LS9 | TM-D drill receipt (LR16) and Daniel's OK to change how new sessions are timed |
| `arsenal/web/piano/tempomap.js`, `arsenal/jam/*` | **None.** A 6/8 or 12/8 jam loop has no beat unit (`beats_per_bar` is an integer). That is raised to the jam spec, not changed here. | none | none |
| `arsenal/web/piano/nashville.js`, `chordread.js`, `recorder.js`, `performance.py` | **None** for v1 | none | none |
| `harmony.js` (TN2, not yet built) | Consumed when it lands: window starts become meter accents and chord-symbol positions | LS8 | TN2 receipts |
| `arsenal/replay.py`, `arsenal/web/piano/replay.js`, `arsenal/pianocue.py` | v2 replay re-render and a possible `pianocue score-link` | v2 | Their own builds released them |

---

## 6. Algorithms and parameters

Start values come from the lanes and the prototypes. "Tuned" means on synthetic seeds only; every value is retuned on LS9 labelled takes.

### 6.1 T1 onsets

| Rule | Parameters |
|---|---|
| Chord group | note-ons within **40 ms** of the group's first (`performance.py` `ONSET_MERGE_MS`). His within-group spread: median 12-20 ms, p90 30-38 ms. |
| Near-chord across hands | next note ≤ **60 ms** after the group and **7+** semitones outside its range → same group (used in section 3) |
| Rolled chord | 3+ notes chained within **120 ms**, monotonic, total spread **≥ 50 ms**, all still held or pedalled at the last → one chord with an arpeggio line |
| Broken-chord run | 4+ onsets **60-300 ms** apart, monotonic → real rhythm (never a roll) |
| Grace note | held **< 110 ms**, **30-120 ms** before an onset **1-2** semitones away in the same hand, and the main note on a grid slot while the grace is not (checked after T3) |
| Salience (for beat.js) | √Σ(0.4 + vel/127), +0.5 if the lowest note ≤ G3 |

### 6.2 T2 beat, BPM, steadiness

- **Induction** (every tick with new onsets, 250 ms clock):
  - pairs of groups in the last **12 s** with gaps of **0.15-3 s**, weighted by the salience product × **0.8**^(groups between);
  - a log-period histogram with **1/60 octave** bins and Gaussian σ **3.5%**;
  - harmonic sum H(P) + ½H(2P) + ⅓H(3P) + ¼H(4P);
  - a log-normal prior centred at **80 bpm**, σ **0.7 octave**.
- **Periodicity strength** = best score ÷ mean score. Bands: **≥ 4.5 steady, 3-4.5 loose, < 3 free**, with **2 s** hysteresis. The hit share over 8 beats may only lower the word.
- **Agents:**
  - hit window max(**60 ms**, **0.18·P**);
  - phase gain **0.8**, period gain **0.35**, period clamped to **0.7-1.4** of its birth value;
  - score τ **10 s**, miss cost **0.15** × mean salience;
  - an off-window salient onset spawns a child;
  - the top **3** induction candidates are anchored and retro-scored;
  - at most **24** agents, near-duplicates pruned;
  - the shown agent changes only when a rival ranks **1.5×** higher.
- **Readout:** BPM is the median of the last **4** inter-beat intervals.
  - `bpmShown` changes **≤ once a bar** and only by **≥ 3 bpm**.
  - It is the tactus under the committed meter (6/8 shows the dotted quarter).
  - Family ratios {2, ½, 1.5, ⅔} feed the buttons.
- **Hold:** starts when the gap is ≥ max(**2 s**, **2.5 beats**).
  - The next onset re-anchors the phase, keeps the period and halves every score.
  - The phrase's bar phase may be re-derived if the first 4 beats read steady.
- **Settle:** a beat is final once **2** more beats exist. A hit takes its onset time; a miss is interpolated between hits.
- **Ladder rules:**

  | Rung | Condition to use it |
  |---|---|
  | jam | a run is live and aligned at L1/L2 |
  | song | listener `phaseConf` above its floor; bar lines only after "This is 1" |
  | taps | 4 taps within the last phrase; "This is 1" optional (beat-aligned tape-bars until pressed) |
  | inferred | **metric bars only while `steady`** (and meter is his setting or an accepted suggestion) |
  | free | otherwise: tape |

- **While a jam run plays,** `beat.js` also runs in the background. Its accuracy against the jam grid is logged per run: the first real-data receipt for rung 4, at no cost to Daniel.

### 6.3 T2.4 meter, bar phase, pickups

- **Meter is his setting:** 4/4 default; 3/4, 6/8, 12/8 or free with one tap; remembered per session.
- **Suggestion chip** ("sounds like 3/4?") appears only when all three hold:
  - template margin **≥ 0.15 R²** over the current meter;
  - **8** consecutive decisions (one per second);
  - `steady`.
- **Scoring:**
  - subdivision grid first: over the last **32** beats, thirds against halves, each needing more than **25%** of on-beat salience;
  - tatum accent = salience, **+0.7** new bass (lowest within ±0.8 s, ≤ G3), **+1.2** × harmonic change, **+0.8** for a pedal change within **0.3 s** after;
  - harmonic change is the pitch-class Jaccard distance over **0.6 s** before and after until `harmony.js`, then window starts;
  - R² of the whole accent sequence against each expanded template (not a folded mean: degenerate for 2-beat bars);
  - priors 4/4 **+0.02**, 6/8 **+0.05**, 12-tatum bars **−0.03**, recorded as priors.
- **Bar phase priority:** jam → song `barPhase` → "This is 1" → inferred. The inferred phase is drawn only in settled bars under a set or accepted meter.
- **Pickup:** onsets before the first committed downbeat become an anacrusis counted in whole sub-beats, allowed only while the first bar is unsettled. Otherwise the phrase starts with a partial bar of rests. MusicXML writes it as `<measure number="0" implicit="yes">` ([W3C measure](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/measure-partwise/)).

### 6.4 T3 per-beat rhythm (measured in section 3)

- For a beat with period P, onset fractions f, and divisions d ∈ {1, 2, 4, 3} (and {1, 3, 2} in compound meters, where a beat is a dotted quarter):

  ```
  C(d) = Σ min_k ((f − k/d)·P)² / (2σ²)  +  λ[d]  +  0.8·[d ≠ previous non-empty beat]  +  0.8·[d ≠ same beat one bar back]  +  6·collisions
  λ[1] = 0, λ[2] = 0.5, λ[4] = 1.5, λ[3] = 2.0 ;  σ₀ = 40 ms, EMA(0.05) of squared residuals, clamped 15-60 ms ;  f > 0.875 → next beat
  ```
- **Loose beat:**
  - If the best cost exceeds **12**, or a collision remains that T1 cannot explain as a roll or grace, the beat is marked `loose`.
  - Live, its notes are drawn proportionally inside the beat slot, with no beam.
  - In export, they snap to the nearest 16th (collisions become `<chord/>`) and are flagged in `score.json`.
  - The cost ceiling of 12 is a start value to set on fixtures (LS2).
- **Swing:** off in v1.
- **Durations** (T3, Q2 default A):
  - the written end is the key release snapped forward within the division;
  - legato fill when the gap to the next onset in the voice is **< one 16th**;
  - shortest value is a 16th;
  - staccato when held **< 40%** of the slot with the pedal up;
  - **held bass**: the lowest voice extends to its sound end;
  - the pedal marks carry the ring.
- **Rests** fill voices. Voice 2 hides whole-bar rests.

### 6.5 T4-T8 notation rules (compressed from `transcription.md`)

- **Bars and ties:**
  - split and tie across bar lines;
  - in 4/4, an off-beat note crossing beat 3 is split;
  - dotted values only on a beat or half-beat;
  - beams by beat (dotted quarter in 12/8), one tuplet bracket per beat;
  - an accidental is never reprinted on a tied-to note.
- **Hands** (DP per onset group over time):
  - candidate splits at every pitch gap, plus all-left and all-right;
  - span > 12 costs 1, > 16 costs 4;
  - continuity is the distance from each hand's key-held centre over 2 s;
  - crossing costs 3;
  - a split not at the largest gap costs 0.5.

  A right-hand line down to F3 stays on the treble staff. There are at most 2 voices per staff (sustained lower notes become voice 2), and no cross-staff beams in v1.
- **Clefs and octave lines:**
  - 3 ledger lines allowed;
  - 8va or 8vb for 1+ bar beyond that;
  - the bass staff switches to treble clef at a bar line after 2 bars at or above C4.
- **Pedal:**
  - a down within **250 ms** after a group is placed at that group;
  - up then down within **300 ms** is one change notch;
  - half-pedal is ignored in the notation (kept in `performance.mid`);
  - `con Ped.` replaces notches when down 80%+ of a phrase.
- **Dynamics:**
  - the median velocity of 4 s windows maps to bands pp < 36, p < 50, mp < 64, mf < 80, f < 96, ff;
  - a mark prints after **2** windows (measured 0.5-2.8 marks a minute);
  - accents at **+20** over the hand's running median.
- **Tempo words:**
  - `rit.` when the period grows 10%+ over 2+ bars at a phrase end;
  - `a tempo` when it returns within 4%;
  - `freely` at tape entries;
  - a fermata when the last chord is held more than 2 beats.
- **Metronome mark:** `♩ = c. 84` at phrase starts.

### 6.6 T7 spelling and key

- **Chord tones** use `spellForKey`, the chips' own path.
- **Passing tones** use `spellInKey`, then melodic direction breaks ties: rising takes a sharp or natural, falling takes a flat.
- **Key signature:**
  - placed at the first **unsettled** bar line after the tracker has held a non-provisional key for **2 bars**, with a double bar;
  - a minor key uses its relative major's signature, named as `performance.py` `MAJOR_KEY_NAMES` (D♭, not C♯);
  - the clean pass uses the closed session's key areas (30 s minimum area), so a 19 s excursion stays accidentals.
- **Accidentals** last to the end of the bar, per pitch and octave. Courtesy accidentals appear in the next bar and for the same letter in another octave.

### 6.7 T9 settle

| State | When | Drawn by | May change |
|---|---|---|---|
| open | playhead inside the bar | `paint.js`: heads at slot x, beat ticks | everything |
| settling | bar ended, fewer than **4** beats since | `engrave.js` in light ink (or `paintBarReduced`) | rhythm, voices, staff, spelling, marks |
| settled | 4 beats past its end, a **2 s** pause, a source switch, or session end | `engrave.js`, full ink, frozen tile | **never** (live) |

- **Why 4 beats.** Measured relabel churn on his logs is 20.4% / 14.6% / 10.7% / **5.7%** at 0 / 1 / 2 / 4 beats.
- **Forward-only corrections.** When something learned late would change a settled bar (a level flip, "This is 1", a key change), the fix starts at the first unsettled bar: a new metronome mark, a partial bar, or a new signature. The clean copy fixes the old bars.
- **Settle crossfade:** 120 ms, using the same opacity damping as `staffAlpha`.

---

## 7. Renderer: choice and trade-offs

### 7.1 The constraint

- The overlay is Canvas2D layers uploaded as `THREE.CanvasTexture` and composited inside the WebGL canvas (`piano.js` 1147-1211).
- `recorder.js` encodes only that canvas.
- A DOM or SVG score beside the canvas would never reach a TikTok.
- Any SVG renderer needs a rasterize hop, and a tainted canvas cannot upload to WebGL.

### 7.2 Options

| Option | Live fit | REC fit | Size and licence | Engraving | Effort for us | Needs Daniel |
|---|---|---|---|---|---|---|
| **Our painter only** (extend `drawStaff` ideas) | Excellent for tape and open bar | Native | 0 B; ours | Heads, accidentals, ledgers today. A reduced metric set is feasible because beats have fixed width (no justification): stems, beam per beat, flags, dots, rests (SMuFL), ties, a "3" numeral. No collision avoidance for two voices beyond stem direction. | High for settled bars (estimate 600-900 lines, unmeasured) | No |
| **VexFlow 5.0.0 core, Canvas backend** | Good per bar (format + draw of a small bar; unmeasured) | Native (Canvas) | 336,625 B; MIT; latest stable still 5.0.0 ([npm](https://registry.npmjs.org/vexflow)); defines global `VexFlow`; fonts via `loadFonts`/`setFonts` ([guide](https://vexflow.github.io/vexflow-examples/guides/getting-started/)) | Beams, tuplets, ties, voices, cross-stave voices (PR #1434), `PedalMarking`, `TextBracket`, accidentals and dots | Adapter plus layout; beaming groups, voices and rests come from our transcriber anyway | **Yes (LQ1)** |
| Verovio 6.3.0 | Poor live: full reload, 7.3 MB WASM, SVG only | Rasterize hop | LGPL-3.0-or-later | Best in browser | Low for a review page | Yes (v2) |
| OpenSheetMusicDisplay 2.1.2 | Poor: MusicXML re-parse per update; bundles a VexFlow 1.2.93 fork | Hop or its Canvas backend | BSD-3, 1.32 MB | Good | Low as a viewer | Yes (v2 fallback) |
| abcjs 6.7.0 | Poor for dense two-hand piano; pedal brackets unconfirmed | SVG hop | MIT, 512 KB | Weak here | n/a | n/a |

### 7.3 Decision: hybrid, each drawer where it is honest

| Element | Drawer | Cadence |
|---|---|---|
| "Now" staff (today) | `drawStaff`, unchanged | as today |
| Tape tiles | `paint.js` | on each onset group, ≤ 8 Hz |
| Open bar (heads at slot x, beat ticks) | `paint.js` | ≤ 8 Hz |
| Settling bar | `engrave.js` (VexFlow), light ink | when its `rev` changes, ≤ 8 Hz |
| Settled bar | `engrave.js`, full ink, one final paint | once |
| Pedal line, dynamics, tempo words, header | `paint.js`, by time or slot, across tiles | on change |
| Review mode (clean copy in the panel) | same drawers, all bars settled | on scroll |

- **Geometry** (start values; LS5 bench decides):
  - staff space **s = 15** in the ribbon;
  - beat width = max(4 slots × 1.6 s, 5 s) = **96 px** at s = 15;
  - a 4/4 bar is 384 px plus key and clef margins on the first tile of a line;
  - tape runs at **120 px per second** (a 3 s stretch ≈ a 4/4 bar at 80 bpm);
  - the playhead sits at **70%** of the band width.

  In 9:16 (1080 px wide) that shows about **2-2.5 bars**. The p90 density (15-43 onsets in 3 s) fits because a beat holds at most 4 slots plus chord columns. Anything denser is a `loose` beat.
- **Fixed slot x against VexFlow's formatter.**
  - The open bar puts heads at slot x.
  - VexFlow justifies its own spacing inside the fixed bar width, so heads may shift slightly at the settle. The 120 ms crossfade covers it.
  - LR11e measures the shift. If it exceeds **0.5 staff space** on average, place `TickContext` x by slot (medium confidence that VexFlow 5 allows it cleanly) or use `paintBarReduced`.
- **Tiles.**
  - Each bar is a `CanvasTexture` plane about 400 × 280 px (built like `makeLayer`).
  - Scrolling moves one group's `position.x` per frame: no canvas work, no upload.
  - Tiles are disposed off-screen.
  - A tie across the bar line is two half-ties at the tile edges.
- **Fonts.** VexFlow uses the same `@vexflow-fonts/bravura@1.0.2` woff2 the page already loads (`BRAVURA_URL`), so the score and the "now" staff match.
- **If LQ1 is no:**
  - `paintBarReduced` draws settling and settled bars: stems up for voice 1 and down for voice 2, a horizontal beam per beat group (slope 0), flags for lone 8ths and 16ths, SMuFL rests, augmentation dots, tie arcs, and a "3" above triplet groups;
  - cross-stave beams and slurs are dropped;
  - the export is unaffected (MusicXML carries the full notation for MuseScore and Dorico).
- **If a bar's engrave exceeds budget** (LR11b): move `engrave.js` into a Worker with `OffscreenCanvas` and upload an `ImageBitmap` (rendering lane 5.4).

### 7.4 Export formats

| File | Content | Notes |
|---|---|---|
| `take.musicxml` (MusicXML 4.0, uncompressed) | one Piano part, `<staves>2</staves>`, `<divisions>24</divisions>`, `<staff>`/`<voice>` per note, `<backup>`, `<chord/>`, ties (`<tie>` + `<tied>`), `<time-modification>` + `<tuplet>`, `<arpeggiate>`, `<pedal type="start\|change\|stop" line="yes">`, `<octave-shift>`, `<key>` at settled key bars, `<metronome>` `c. 84` + `<sound tempo>` per bar from the tempo map + `<words>rubato</words>`, `<dynamics>`, grace notes, pickup `implicit="yes"` | Free-time passages: forced bars at the rough BPM marked `freely` by default (LQ2). The alternative is `<time><senza-misura/></time>`, which "explicitly indicates that no time signature is present" ([W3C](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/senza-misura/)); MuseScore and Dorico import of it is untested. |
| `performance.mid` | SMF type 0; **PPQ 500 with tempo 500,000 µs per quarter, so 1 tick = 1 ms**, and raw times are exact; note on/off with velocity, CC64 with raw values | Nothing lost: rubato, voicing, half-pedal. MuseScore and Dorico can re-quantize it if ours is wrong. |
| `quantized.mid` | SMF type 1, PPQ 480, RH on track 1 and LH on track 2 by staff, a tempo event per settled beat from the tempo map | Notes on the grid, played back in his time |
| `score.json` | `arsenal.piano.score/v0`, kind `clean`, with perf links | The source for re-engraving and v2 fixes |

---

## 8. The clean pass: a session or a moment

1. **Span:** a take, `--at mm:ss --seconds N` (the same form as `pianocue replay-link`), or the whole session. Notes already sounding at the span start are carried in as ties from a pickup rest.
2. **Beat tidy:**
   - a jam map if a run covers the span;
   - else the taps and "This is 1" logged by the page (proposed as page-local take metadata saved beside the score, not as log events, so `performance.py` stays unchanged);
   - else the same agents run forward, then a backward pass with a Viterbi over (period, phase) using McLeod's proportional tempo penalty;
   - one meter per phrase, with phrases split at holds;
   - CLI flags `--meter`, `--one <t>` and `--bpm` let Daniel or an agent pin them.
3. **Divisions:** Viterbi (section 6.4).
4. **Hands, spelling, marks** as live, with key areas from the closed session's summary (else a tracker replay).
5. **Output:** `score.clean.json` plus the three files. No live score is overwritten.

---

## 9. Build slices

| Slice | Content | Receipts | Touches jam-held files? |
|---|---|---|---|
| **LS0** Fixtures and metrics | `tests/fixtures/score/gen.mjs` (section 3 generator + tempo lane generator, pickups, fermatas, tempo steps, random unmetered, durations with truth); metric helpers (beat F ±70 ms, Acc1/Acc2, flips, bands, onsets, beats and bars exact, duration exact) | LR1 | No |
| **LS1** Onsets and beat | `onsets.js`, `beat.js` (rungs 3-5, bands, BPM readout, family) | LR2, LR3 | No |
| **LS2** Rhythm and settle | `quantize.js`, `measures.js`, `settle.js`, `index.js` skeleton | LR4, LR5, LR6 | No |
| **LS3** Hands and marks | `hands.js`, `marks.js`, `meter.js` (his setting, suggestion scorer, pickups) | LR7, LR8 | No |
| **LS4** Export and CLI | `musicxml.js`, `midi.js`, `score_cli.mjs clean\|export\|bench` over S1..Sn locally (outputs stay in `state/arsenal/score/`) | LR9, LR10 | No |
| **LS5** Lab page | `layout.js`, `paint.js`, `engrave.js` (if LQ1), `piano-lab-score.html/.js`: Web MIDI live, `events.jsonl` replay, G1 bench incl. WebGL upload | LR11 | No (new page, served like the other `piano-lab-*` pages) |
| (gate) | **Jam build committed; `piano.js`, `piano.html`, `piano.css`, `serve.py` clean in git** | | |
| **LS6** Integration | Move `spellForKey` to `piano/spell.js`; feed events; score layer; HUD; header; REC | LR12, LR13 | Yes, after the gate |
| **LS7** Jam rung and saving | Jam rung via `sessionTms`; `serve.py` take routes; Save take; Clean last take | LR14 | Yes, after the gate |
| **LS8** Harmony and song | `harmony.js` window accents and chord symbols (after TN2); song rung (after practice-along AL phases) | LR3 re-run | Only piano.js wiring |
| **LS9** Daniel drill | Three takes (jam loop, tapped, free) and about 10 short labelled takes (meter and count known, some with the jam click); retune priors, windows, cost ceiling; decide timestamps | LR15, LR16 | No code |

**Useful early win.** LS1 plus the LS5 lab page give Daniel a working **rough BPM with tap, ÷2/×2 and the steadiness word** in a lab tab before any jam-held file changes. Web MIDI input is shared across tabs in one Chrome process on Windows (medium confidence; checked in LS5).

---

## 10. Acceptance receipts

Each receipt needs a dated result before it counts. Thresholds sit a few points under today's measured values, and the measured value is shown in brackets. "Fixture" means the LS0 synthetic suite on held-out seeds.

### 10.1 Tempo stability and beat (LS1)

| # | Receipt | Threshold [measured today] |
|---|---|---|
| LR1 | Generator is deterministic by seed; the section 3 and tempo-lane tables reproduce within ±1 point | exact seeds; ±1 point |
| LR2a | Displayed BPM within 8% of local truth (Acc1): all / rub0 / rub1 | ≥ 0.68 / ≥ 0.85 / ≥ 0.80 [0.710 / 0.891 / 0.848] |
| LR2b | Related tempo (Acc2, incl. ×2, ½, ×3, ⅓, ×1.5, ⅔) | ≥ 0.78 [0.815] |
| LR2c | Beat F at ±70 ms | ≥ 0.60 [0.642] |
| LR2d | Level errors / tempo display flips per minute | ≤ 0.13 [0.105] / ≤ 2.0 [1.60] |
| LR2e | Time until shown tempo within 8% for 2 s: mean; pieces never | ≤ 12 s [9.4 s]; ≤ 5 of 81 [4] |
| LR2f | `bpmShown` changes | ≤ 1 per bar (by construction); median per bar reported |
| LR3a | Random unmetered fixtures: share of time `steady` / `free` | 0% [0%] / ≥ 75% [79%] |
| LR3b | On S1..Sn replay with the meter held at 4/4: ×1.5 display flips; ×2 flips | ≤ 1.0 per min (prediction: the tatum-conversion flips, 0.2-3.4, vanish); ≤ 0.5 per min [0-0.4] |
| LR3c | Tracker cost on the S12 replay | ≤ 0.2 ms per 250 ms tick p95 [0.05 mean] |

### 10.2 Quantization, bars and settle (LS2)

| # | Receipt | Threshold [measured, section 3] |
|---|---|---|
| LR4a | Oracle beats: onsets exact / bars exact, all | ≥ 0.985 / ≥ 0.94 [0.994 / 0.966] |
| LR4b | Oracle beats, rub2: bars exact | ≥ 0.87 [0.906] |
| LR4c | Beats ±30 ms: onsets / bars | ≥ 0.97 / ≥ 0.86 [0.979 / 0.895] |
| LR4d | Note jitter 45 ms, oracle beats: onsets / bars | ≥ 0.90 / ≥ 0.60 [0.922 / 0.650] |
| LR4e | Per-beat priors beat naive snapping at 30 ms jitter: bars exact gain | ≥ +12 points [+17.4] |
| LR4f | Inferred rung: onsets exact inside matched intervals | ≥ 0.95 [0.974]; coverage reported [0.443 all, 0.242 rub2] |
| LR4g | Live view never shows metric bars from rung 4 outside `steady` | 0 bars |
| LR4h | Written durations exact on fixtures (legato fill, held bass, staccato) | measured in LS0 first; threshold set then (no number exists yet) |
| LR5 | Transcriber cost excluding paint, S12 replay | ≤ 0.5 ms per onset group p95 [quantizer 0.002 ms per bar live, 0.007 clean] |
| LR6a | Settled measures across a full replay of S1..Sn | 0 changes |
| LR6b | Relabel churn at 4 beats vs 8 beats of hindsight, S1..Sn | ≤ 6% [5.7% with a simpler tracker] |
| LR6c | Flicker (notehead or label changes per minute in open and settling bars) | reported per session; calibrated per theory-nextgen D14 |

### 10.3 Notation and export (LS3, LS4)

| # | Receipt | Threshold |
|---|---|---|
| LR7 | Hands: staff accuracy / voice F1 on fixtures | ≥ 95% / ≥ 0.90 (transcription SR7) |
| LR8 | Readability proxies on S1..Sn clean copies: median per bar ≤ 1 tuplet bracket, ≤ 2 ties, ≤ 2 voices per staff; pedal marks ≤ 1 per beat; dynamics ≤ 3 per min; key signature changes ≤ 1 per 30 s of key area | all met (SR8, SR9) |
| LR9a | Every clean copy (fixtures + S1..Sn): XML well-formed (Python `xml.etree`); every voice's durations sum to its measure length; tie starts and stops pair; sounding notes after tie merge equal performance notes | 100% |
| LR9b | `performance.mid` re-read by an independent Python stdlib parser: every on/off/CC64 time | equal to the log's `t_ms`, 0 ms error (1 tick = 1 ms) |
| LR9c | `quantized.mid` note count equals MusicXML sounding notes | 100% |
| LR10 | Daniel opens one `take.musicxml` in MuseScore or Dorico by hand: it loads, two staves, pedal marks visible | dated drill receipt |

### 10.4 Rendering and recording (LS5, LS6)

| # | Receipt (lab page on this machine, three.js scene running for LR11c-d and LR12) | Threshold |
|---|---|---|
| LR11a | `paintOpenBar` / `paintTape` for 43- and 67-onset windows | p95 ≤ 2 ms / ≤ 3 ms |
| LR11b | `engraveBar` (VexFlow Canvas format + draw) for bars of 12, 24, 43, 67 onsets with 10-head chords and triplets | p95 ≤ 8 ms at 43, ≤ 12 ms at 67 (else Worker, 7.3) |
| LR11c | One tile texture upload (about 400 × 280) | p95 ≤ 2 ms |
| LR11d | Settled tiles repaint count after settling | 0 |
| LR11e | Mean notehead x shift at the settle crossfade | ≤ 0.5 staff space (else slot-placed TickContext or reduced painter) |
| LR12 | 60 s REC at 60 fps with the score panel on against a panel-off control: `recorder.js` `skipped` count; MP4 shows the panel | not above control (±2 frames of 3,600); panel visible |
| LR13 | Staff spelling equals chip spelling on every chord tone of S1..Sn chord events; `piano.js` behaviour unchanged after the `spellForKey` move (chips identical on a replay) | 100%; identical |
| LR14 | During a jam run, score bar lines against `tempomap.js` bars; rung-4 accuracy against the jam grid logged | ≤ 2 ms; reported |

### 10.5 With Daniel (LS9)

| # | Receipt | Threshold |
|---|---|---|
| LR15 | Three 60-90 s takes (jam loop, tapped, free). He marks each clean-copy bar readable or not. The quantizer's learned σ per take is recorded (his real residual). | jam take ≥ 80% readable bars; tapped ≥ 60%; free take shows tape live and forced bars in the clean copy; dated receipt under `state/drills/` |
| LR16 | TM-D: 2 min of playing with `ev.timeStamp` and `clock()` logged side by side while the scene renders | offset and jitter distribution recorded; the timestamp decision is made from it |

---

## 11. v2 ideas

1. **Scrolling score in recordings, re-rendered (path B).**
   - After a take, replay it from the log with the ribbon fed by the **clean** score, and record a fresh MP4 through `recorder.js`, so a post shows settled notation.
   - It builds on the replay machinery (`arsenal/replay.py`, `REPLAY.md`, `piano/replay.js`), which reconstructs onsets, velocities and pedal-aware durations.
   - A variant is a page view that scrolls in sync with recorded audio using Verovio's timemap (needs a v2 decision).
2. **Practice log to PDF.**
   - Cheapest, no install: a review page of the clean copy, printed to PDF from the browser (VexFlow SVG backend for print quality).
   - Better engraving: Verovio 6.3.0 (LGPL, about 7.3 MB) for the review page and as a MusicXML import checker.
   - Or MuseScore Studio 4.x (`MuseScore4.exe -o take.pdf take.musicxml`) or LilyPond 2.26 from a CLI (both GPL-3.0, both installs).
   - Later: `pianocue score-link latest 3:43 --seconds 30` in the style of `replay-link`, for chat replies.
3. **Song-follow tempo.**
   - Rung 2 from the practice-along listener (`beat {periodMs, nextBeatPerf, phaseConf, barPhase}`) with "This is 1".
   - A per-song stored BPM and meter from the practice-along song identity, used as the tempo prior and meter default.
   - Bar lines that follow the record's beat while he plays along.
4. **Fix a beat in the clean copy.** The per-beat cost already ranks divisions. A tap on a beat cycles to the runner-up division and re-engraves that bar. Section 3 predicts about 1 bar in 3 to 14 needs it against a click.
5. **Offline references**, after installs: PM2S (MIT, PyTorch), met-align (MIT, Java), MIDI2ScoreTransformer, as a third opinion on labelled takes.
6. **Notation extensions:** quintuplets and sextuplets (TPQ 120), swing as straight 8ths plus `swing`, hairpins and phrase slurs, `½ Ped.`, `l.v.` ties, cross-staff beams, a chord-symbol line above the treble staff, a lead-sheet export of the solo line (ABC or MusicXML), and a Petaluma handwritten skin.
7. **Score following of his own pieces:** once a clean copy exists, follow it live the next time he plays it ([arXiv 2505.05078](https://arxiv.org/abs/2505.05078)).
8. **Compound meter in the jam map:** a beat unit for 6/8 and 12/8 loops (jam-spec question), so rung 1 covers them.

---

## 12. Questions for Daniel (at most four)

| # | Question | Recommended default |
|---|---|---|
| **LQ1** | May the page load **VexFlow 5.0.0 core** (MIT, 336 KB) pinned from jsDelivr, the same way it loads three.js, to engrave finished bars? The alternative is our own simpler drawing (no cross-staff beams or slurs; more build work). | **Yes, CDN-pinned.** Vendor a copy only if offline use matters. |
| **LQ2** | When there is no steady beat, what should the score show? (a) Notes by time with no rhythm claimed (tape), (b) bars forced at the rough BPM marked `freely`, or (c) tape live and forced bars in the saved and cleaned copy. | **(c).** The live page never shows a rhythm you did not play; saved files open as normal sheet music. |
| **LQ3** | Is the meter **your setting** (4/4 unless you tap 3/4, 6/8 or 12/8; the page only suggests)? And for a slow ballad, is the BPM your felt quarter (about 70, not 140), with 6/8 counted in 2? | **Yes to all three.** On your sessions the automatic meter flips on a tiny tie-break, and a 55-110 quarter matches your 74-102 measured feel. |
| **LQ4** | Should the score panel be in REC videos? It shows live guesses that settle about one bar late. Where should it sit? | **On, replacing the "now" staff box while the score is on** (9:16), with a full-width bottom band in 16:9. For posts, use the re-rendered replay (v2) so the video shows the settled score. |

**Decided by default for now, revisited at their gates** (not questions tonight):
- pedalled notes are written as played, with pedal marks and a held bass (transcription Q2 A);
- exports come from the clean pass;
- MusicXML and MIDI writers are in-house (rendering D7);
- no installs (MuseScore, LilyPond, PyTorch models) and no Verovio until v2;
- the log's timestamp source is decided after LR16;
- labelled takes are invited in LS9, not required for v1.

---

## 13. Risks and unmeasured facts

1. **Synthetic is not Daniel.** Every accuracy number (section 3 and the tempo lane) comes from generated playing with an expressible rhythm alphabet. Only LR15 and LS9 labelled takes can say "correct notation" about him.
2. **His timing spread may cap bar accuracy even with a click.** The 30-45 ms jitter rows give 65-93% bars exact. The per-beat fix (v2 item 4) and the learned σ receipt keep this visible.
3. **Most unaccompanied playing will be tape.** His sessions read steady only 0-12% of the time by periodicity strength. Tape must look good, not like an error state: LR15 asks him.
4. **VexFlow render time for dense piano bars is unmeasured.** LR11b gates it, with a Worker and the reduced painter as fallbacks. VexFlow 5.0.0 has had no release since March 2025. It is MIT, so a pinned copy stays usable.
5. **Settle-time notehead shifts** between the provisional slot layout and VexFlow's justified spacing are unmeasured (LR11e).
6. **Panel width.** At s = 15 the 9:16 band shows about 2-2.5 bars. The 16:9 staff box (640 px) is too narrow, and the band placement is LQ4.
7. **Downbeats from his notes alone are unreliable** (synthetic rub2 downbeat F 0.17). Bars from rung 4 without "This is 1" will often start in the wrong place. Forward-only correction stops flicker, and the clean pass asks for "1".
8. **12/8 is hard for the inferred rung** (coverage 18% in section 3). With his meter setting plus taps it follows rung 3.
9. **`spellForKey` reads page state** (`theoryUi.minor`). The move in LS6 must keep chips identical (LR13) and needs the jam build's release of `piano.js`.
10. **S10 and S11 lowest-key counts** look like re-strikes without a logged release (transcription lane). Check the note pairing in LS0 before tuning hands.
11. **Web MIDI sharing** between the piano tab and the lab tab is assumed (medium confidence), and checked in LS5.

---

## Sources

This plan's measurements
- Scratch, untracked: `scratchpad/sheet/quant.mjs` → `quant.out` (section 3); the tempo lane's `tracker.mjs`, `sweep3.mjs`, `sessions2.mjs`, `timeit.mjs`; the transcription lane's `stats*.py`; the rendering lane's `density.py`.

Lanes (this folder)
- `tempo-meter.md`, `transcription.md`, `rendering-formats.md`

Repository
- `arsenal/web/piano.js`: overlay and `makeLayer` 1147-1211, `drawStaff` 1385, `overlay.update` 1666, `spellForKey` 1843, practice log wiring 1888-1946, `noteOn` 1966 (`clock()` at handler time), `onMidiMessage` 2715.
- `arsenal/web/piano/log.js` (timebase `t0_perf_ms`, `page_id`); `arsenal/performance.py` (`KINDS`, `ONSET_MERGE_MS`, `MAJOR_KEY_NAMES`, `PerformanceStore.get` returns the summary, `events()`).
- `arsenal/web/piano/nashville.js` (`spellInKey`, `createKeyTracker`); `arsenal/web/piano/tempomap.js` (`tEpoch`, `barAt`, `sessionTms`); `arsenal/web/piano/deck.js` (`TEMPO` tap rule); `arsenal/web/piano/recorder.js` (`skipped`).
- `arsenal/serve.py` (`/api/performance` routes); `arsenal/REPLAY.md`; `.gitignore` (`state/*`).
- `research/in-flight/practice-along-2026-09-14/practice-along-plan.md` 2.2 (listener `state().beat`); `research/in-flight/piano-theory-nextgen-2026-09-14/theory-nextgen-spec.md` 2.3 (`harmony.js`); `research/in-flight/piano-jam-2026-09-14/jam-spec.md` 11.2 (alignment ladder).

Web (checked for this plan)
- VexFlow npm registry, latest 5.0.0: https://registry.npmjs.org/vexflow
- VexFlow getting started (CDN core URL, global `VexFlow`, `loadFonts`/`setFonts`): https://vexflow.github.io/vexflow-examples/guides/getting-started/
- VexFlow Canvas backend (`Renderer.Backends.CANVAS`): https://github.com/0xfe/vexflow/wiki/Using-SVG-or-HTML5-Canvas-with-VexFlow
- MusicXML 4.0 `senza-misura`: https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/senza-misura/
- MusicXML 4.0 `measure` (`implicit` for pickups): https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/measure-partwise/

Web (cited through the lanes, 2018-2026)
- Beat-conditioned quantization, 2026: https://arxiv.org/abs/2604.22290
- Beat and downbeat tracking in performance MIDI, SMC 2025: https://arxiv.org/abs/2507.00466
- MIDI2ScoreTransformer, ISMIR 2024: https://arxiv.org/abs/2410.00210
- PM2S, ISMIR 2022: https://www.turing.ac.uk/sites/default/files/2022-09/midi_quantisation_paper_ismir_2022_0.pdf
- McLeod and Steedman, meter detection, ISMIR 2018: https://apmcleod.github.io/pdf/ISMIR_Meter.pdf
- EngravingGNN, 2025: https://arxiv.org/abs/2509.19412
- Cluster and Separate, ISMIR 2024: https://arxiv.org/abs/2407.21030
- Real-time score following, SMC 2025: https://arxiv.org/abs/2505.05078
- W3C Web MIDI (`MIDIMessageEvent.timeStamp`): https://www.w3.org/TR/webmidi/
- MusicXML 4.0: https://www.w3.org/2021/06/musicxml40/
- Verovio: https://book.verovio.org/toolkit-reference/output-formats.html
- OpenSheetMusicDisplay 2.0.0: https://github.com/opensheetmusicdisplay/opensheetmusicdisplay/releases/tag/2.0.0
- Dorico 6: https://blog.dorico.com/2025/04/dorico-6-released/
- MuseScore command line: https://handbook.musescore.org/appendix/command-line-usage
- ScoreCloud FAQ: https://scorecloud.com/support/
- MuseScore issue 28402: https://github.com/musescore/MuseScore/issues/28402
- Logic Pro Smart Tempo: https://support.apple.com/en-us/102165
- Chrome 131 intent on canvas tainting: https://groups.google.com/a/chromium.org/g/blink-dev/c/JpA2vmA9XT8
