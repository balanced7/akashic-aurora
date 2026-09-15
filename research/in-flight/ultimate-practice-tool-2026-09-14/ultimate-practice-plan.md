# The ultimate practice and jam tool: the ranked plan

| | |
|---|---|
| Type | research (in flight), synthesis of four lanes |
| Date | 2026-09-14 |
| Author | Vandor (claude seat), research subagent |
| Status | Research only. No `arsenal/` edits, no servers, browsers, downloads, installs or logins. |
| Built from | `products.md` (about 40 commercial tools), `open-source.md` (open and academic projects), `chord-accuracy.md` (C1-C14) in this folder, and the analysis-displays lane. That lane's report reached the orchestrator as text because the harness refused its file; its numbers are aggregates over 11 logged sessions and its thresholds are not yet checked against Daniel's ear. |
| Checked against | `piano-jam-2026-09-14/jam-spec.md` (sections 0, 2, 13, 15) and `design-music.md` 9.8-9.10; `piano-spectacle-2026-09-13/spectacle-spec.md` 3.4, 6, and Daniel's decisions; `piano-suggest-lights-2026-09-14/suggest-lights-plan.md` 0, 4, and decisions; `practice-along-2026-09-14/practice-along-plan.md` 0, 7, and decisions; `piano-theory-nextgen-2026-09-14/theory-nextgen-spec.md` 0-1, 3.6-6, 9, and decisions; `design-pedagogy.md` P6, P9, P10. |
| Checked locally | `git status` of `arsenal/`; `arsenal/REPLAY.md`; the `practice.py` verb list; `pianocue.py` (`build_replay_cue`, `replay-link`); `recorder.js` frame pacing. |
| Privacy | No session ids, clock times or transcriptions. Only counts and shares from the lanes. |

Daniel, verbatim (Discord):

> "I wonder how we can make this be the ultimate practice / jamming tool, are there any other projects that are
> similar that we could look at for features we can integrate? Any ideas on how to improve chord accuracy? I also love
> how our system shows you the chord for notes arpegiated with sustain! What other detections or analysis do you think
> would be really cool to display?"

---

## 0. In one screen

**The short answer for Daniel.**

1. **Nobody else does the thing you love.** No commercial app and no open project names pedalled, arpeggiated
   playing live. The strong research recognisers all work offline on tidy scores. We take their ideas and leave their
   code.
2. **Jamming: two big steals.**
   - **Loop me:** your last few bars loop exactly as you played them, and you play over yourself.
   - **The band follows you:** bass and a soft comp take whatever chord you hold, one beat later.
3. **Practising: be told true things about your touch, never scores.** No app reads these three from MIDI, and all
   three are your lush, pedalled style:
   - when you change the pedal against chord changes;
   - whether you roll or block your chords;
   - whether your top note sings over the inner voices.
4. **Chord accuracy: measure against your ear first, then use context.** Today every accuracy number compares our
   engine with our own offline engine. Twenty minutes of you naming disputed chords makes the numbers real. After that,
   the cheapest gain is choosing among the top three names using the chords before and after.
5. **Displays and videos: draw the rich analysis in re-renders, not in the live take.** A take replayed from the log
   knows the future, so phrase arcs, the note that moved and pedal fog can be exact on video while your live canvas
   stays yours.

**The top 15, ranked by value to Daniel for the effort.** S is half a day or less, M is 1-2 days, L is 3 or more days.

| # | Idea | Group | Effort | Earliest slot | Needs an OK from |
|---|---|---|---|---|---|
| 1 | **Loop me** | jam and backing | M | own wave after J10; zero-code preview tonight | Daniel (Q1, order) |
| 2 | **Touch facts:** pedal at changes, roll or block, top-voice balance, harmonic rhythm | learning and feedback | M | after practice verbs (B2) land | none |
| 3 | **Measure against his ear:** gold set, field scoring, textured test streams | chord accuracy | M | with TN1 | Daniel (Q2, 20 minutes); conductor (corpus) |
| 4 | **Voicing shape label** (shell, rootless, quartal, cluster on top) | analysis displays | S | with TN1, HUD at TN7 | none |
| 5 | **Cheap accuracy trio:** context re-rank, per-part confidence, roll grouping | chord accuracy | S-M | TN1, TN2 | conductor note |
| 6 | **The band follows my chords** | jam and backing | L | after J10, TN7, V2-A | none |
| 7 | **Offline re-render with a hindsight layer** | content formats | M-L | after spectacle P3 and TN7 | Daniel (Q3) |
| 8 | **Run routines:** around the keys, earned speed, slices, lookahead | jam and backing | S-M | V2-A and V2-G | none |
| 9 | **Pedal depth logging, then pedal fog** | analysis displays | S-M, then M | logging this week; fog after TN7 | log-schema owner and conductor; Q3 for video |
| 10 | **Moment to FL** (`practice moment --mid`) | content formats | S | after B2 lands | none |
| 11 | **The note that moved** (voice-leading arcs, P/L/R words) | analysis displays | M | after TN7 | Q3 for video |
| 12 | **Call it:** his corrections, applied in all 12 keys | chord accuracy | M | after TN9 | Daniel and conductor |
| 13 | **Find it:** ear cards made from his own moves | learning and feedback | M | after the replay companion lands | Daniel (taste, in chat) |
| 14 | **Progression family and arrivals** ("2-5-1", "backdoor", "deceptive") | analysis displays | M | after TN4 and TN8 | Q4 before any non-commercial data |
| 15 | **End-of-night poster** (`practice map`) | content formats | S-M | any time after #2 | none |

---

## 1. Already planned, so not re-proposed

The lanes found these in other products. Our specs already have them, so this plan only extends them.

| Capability the lanes saw elsewhere | Where we already have or plan it |
|---|---|
| Wait mode, tempo ramps, call and response, glass marks on his notes, follow-me tempo, `.mid` export of cards | jam-spec 2.2 (V2-A, V2-C, V2-E, V2-G) |
| Clear next step after a session; facts with times | riff "one thing to try" (jam-spec 11.4) |
| Next-chord chips (theory, his habits, growth edge), near voicing, lit keys | suggest-lights SG0-SG9, L0-L5 |
| Song key and BPM from audio, a count-in on the song's beat, follow key and tempo | practice-along AL0-AL9 |
| Big chord vocabulary, the ALSO name, function words, scale captions, key ring, Lesson view | theory-nextgen TN0-TN11 |
| Rarity tiers, stage effects, live recording at the framing size | spectacle P0-P6 |
| Clickable excerpts with loop and speed; question cards answered by playing | the replay companion in flight (`arsenal/REPLAY.md`; `arsenal/replay.py`, `web/piano/replay.js`, `conversation.*`, untracked) |
| Rhythm placement, swing, phrases and motifs, call-and-response labels | design-music 9.8-9.10 (jam V2-C) |

---

## 2. The top 15, by group

Every card uses the same fields. Rank is the overall rank from section 0.

### 2.1 Jam and backing

#### #1 Loop me

- **What.** Daniel plays 2-8 bars and taps Loop me (a deck button, later a KeyLab pad). What he just played loops
  exactly as played, under the bar clock, and he plays over himself.
  - Loop ends snap to the nearest bar line when a run tempo exists. With no tempo they snap to a gesture boundary: a
    pedal lift plus a gap.
  - v1 has one lane. "Add a layer" (up to 3) comes later.
- **Prior art.**
  - Scaler 3 Multi-Bind and performance recording: https://scalermusic.com/products/scaler-3/
  - Soundslice loops that snap to note, rest or barline: https://www.soundslice.com/blog/199/introducing-enhanced-slowdown-and-perfect-looping/
  - Aria-Duet hands the turn back and forth with a pedal (a later turn-taking gesture): https://arxiv.org/html/2511.01663
- **Why it fits Daniel.** His best material is what he just improvised. A loop of his own voicing under his right hand
  is a jam partner that sounds like him from the first night. It gives him call and response with himself, and a
  layering format for TikTok.
- **Plugs into.**
  - A new run kind `loop_me` in the jam run schema (jam-spec 4.3). J0 froze that contract, so the change goes through
    the conductor.
  - The slice comes from the log through `pianocue.build_replay_cue`, which already exists and tags notes
    `source: "replay"`.
  - Timing uses the bar clock and hand-off (jam-spec 9.1-9.3). The button sits beside Hear me (8.4).
- **Guards.**
  - Replayed notes never reach `detect()`, the log, the key tracker or rarity (jam-spec C11).
  - In REC, jam view `auto` moves the keys to the glass. The loop's sound stays out of the take, as for any Claude
    sound (jam Q1).
- **Effort.** M for the transport run kind, capture and button, plus S for the snap rules.
- **Depends on.** J9 integrated and J10 held; the J5 timebase, so the live cut lands on the right notes; a run tempo
  (or #6's pulse gate) before bar snapping.
- **Needs an OK from.** Daniel, for ordering only (Q1). The loop sounds in the built-in keys voice until V2-E's MIDI out,
  which needs his OK for a loopback download.
- **Receipt.**
  - Capture-to-loop latency is measured.
  - Loop drift over 5 minutes stays inside A1's bound.
  - Replayed notes are absent from the log and the label (the A6 pattern).

#### #6 The band follows my chords

- **What.** While Daniel plays freely, a bass and a soft comp take the chord he holds and land on the next beat or bar.
  - **Three follow rules.**
    - **Bass:** the bass goes to his chord's bass.
    - **Narrow:** each comp note moves to the nearest chord tone.
    - **Parallel:** a riff shifts by the root interval.
  - **Two knobs only:** complexity (groove density) and intensity (velocity and register).
  - **The comp steps aside** while his left hand comps; bass and pulse keep going.
- **Prior art.**
  - Studio One Follow Chords (Narrow, Parallel, Bass): https://www.audeobox.com/learn/studio-one/chord-track-guide/
  - Logic Session Players following the Chord Track, with complexity and intensity: https://support.apple.com/guide/logicpro/chords-and-session-players-lgcp70dd5af3/mac
  - Band-in-a-Box, where the player takes over the piano part: https://www.pgmusic.com/bbwin.htm
  - ReaLJam's commit window: https://arxiv.org/html/2502.21267
- **Why it fits Daniel.** This is the core jamming wish, a band that listens. Cards prescribe the chords; here he leads.
- **Plugs into.**
  - **Input:** the harmony window commit (theory-nextgen D2, the one commit clock). The band moves only when #5's
    per-part confidence says root and bass are sure.
  - **Voicing:** the jam `band` voicer (10.1), with `upper: "same"` for held hands.
  - **Patterns:** `groove.js` (10.2), re-pitched by each rule. `band.py`'s `_nearest_in_range` is already the Narrow
    rule for one voice.
  - **Timing:** changes land by 9.4. The duck (9.5) grows a comp-drop rule.
  - **Tempo:** a run tempo, practice-along's BPM (AL3), or later Follow me (V2-G).
  - **Honesty:** the Now header says "follows you, one beat behind".
- **Effort.** L.
- **Depends on.** J10; TN7 (the harmony window running on the page); V2-A grooves; #5's per-part confidence. Free play
  with no run waits for a pulse-or-free gate (analysis lane E1: blurred-onset autocorrelation over 12 s windows).
- **Needs an OK from.** Nobody while it uses the built-in voice. Kontakt sound means V2-E and a download.
- **Receipt.**
  - On synthetic streams, the band's bass pitch class equals the committed bass within 1 beat 95% of the time.
  - No change on unsure windows.
  - Zero backing notes reach `detect()`.

#### #8 Run routines: around the keys, earned speed, slices, lookahead

- **What.** Four run options in the deck's run menu, with no new surface.
  - **`cycle`:** the key moves each pass: up a 4th, down a half step, or through "his keys". His signature moves are
    the minor-third and half-step drops.
  - **`speed`:** Try starts slower and adds a few bpm after each clean pass, up to the card's tempo. "Clean" means the
    riff alignment shows his chord tones landed in each bar. No number appears beyond the bpm already in the Now header.
  - **`slices`:** a long card is tried in bar pairs, then halves, then whole.
  - **`lookahead`:** incoming ghosts appear 1 beat (today), 1 bar or 2 bars ahead. Committed chords are drawn solid,
    tentative ones see-through.
- **Prior art.**
  - iReal Pro key cycling and automatic tempo increase: https://www.irealpro.com/
  - Melodics Auto BPM: https://support.melodics.com/en/articles/6777027-practice-mode
  - Soundslice speed training: https://www.soundslice.com/blog/215/introducing-speed-training/
  - Piano Marvel slicing: https://pianomarvel.com/en/feature/practice-mode
  - ReaLJam's solid-versus-see-through upcoming chords and adjustable commit window; its players disagreed on the best
    settings: https://arxiv.org/html/2502.21267
- **Why it fits Daniel.** Seventeen cards become months of nights. Key cycling is how an ear player learns that the
  numbers stay while the letters move. The reward is sound, a tempo creeping up, never a score (P9).
- **Plugs into.**
  - Run schema 4.3 gets the fields. The names should be reserved now in 4.5 so J0's contracts leave room.
  - `cycle` uses the top-of-pass key change (C3).
  - `speed` is a gated form of V2-A's tempo ramps (9.1 step changes), with the gate from riff alignment (11.2).
  - `lookahead` extends the ghost states (8.5). The A4 transposition fixture covers cycled runs.
- **Effort.** S each; S-M in total.
- **Depends on.** J10; V2-A for ramps; J4's riff for the clean gate.
- **Needs an OK from.** Nobody.
- **Receipt.** A4 passes across cycled runs. In the fixture, speed never steps up without a clean pass.

### 2.2 Learning and feedback loops

#### #2 Touch facts

- **What.** `py -m arsenal.practice touch`, plus riff talking points, for skills read from MIDI already in the log.
  - **Pedal at chord changes.** Does he re-pedal just after the new chord strikes (clean), before it (a gap), or late
    (a smear)? This is measured at harmony-window changes only.
  - **Roll or block.** The onset spread of chord attacks, as a night's style: "you roll your 4 chords and block your
    5s".
  - **Top-voice balance.** Top-note velocity against the inner voices.
    - *Melody lead in milliseconds is refused*: the lane measured a median of 0 ms, and research attributes lead to
      velocity.
  - **Harmonic rhythm.** "Changes every 2 beats"; "your changes speed up into the ending".
  - **Presentation.** Facts carry times and Hear links, thresholds use per-session percentiles, and nothing is graded.
- **Prior art.**
  - ROLI AI Music Coach's harmony, rhythm and dynamics dimensions: https://musictech.com/news/gear/roli-ai-music-coach-airwave-first-look/
  - PercePiano's performance vocabulary (pedal clean or blurred, timing stability): https://github.com/JonghoKimSNU/PercePiano
  - Profy's feedback pinned to specific passages: https://arxiv.org/abs/2606.10627
  - Goebl on melody lead as a velocity artefact: https://iwk.mdw.ac.at/goebl/papers/Goebl_JASA2001_melodyLead.pdf
  - Pedalling taxonomy: https://zenodo.org/records/3242149
  - Harmonic rhythm as a detected quantity in Logic 12 Chord ID: https://cdm.link/logic-pro-12-hands-on/
- **Why it fits Daniel.** No product reads these from MIDI; learning apps grade note accuracy for beginners. The
  analysis lane's aggregates from the log:
  - block share runs 0.35-0.77 by night;
  - the top voice is louder by 8 or more in 42-57% of wide attacks;
  - hands split cleanly on a gap of 7+ semitones in 76-100% of attacks;
  - velocity p50 ranges 46-86 across nights, so fixed thresholds would lie.
- **Plugs into.**
  - A new `arsenal/practice_touch.py` with a 3-line registration, the same pattern as riff (jam-spec C18).
  - Harmonic windows from `practice.py`.
  - Riff talking points (jam-spec 11.4; design-music 9.8, 9.11).
  - The wording guard (P9), and Hear links via `pianocue replay-link`.
  - The hand split (analysis lane C1) is the first function built.
- **Effort.** M.
- **Depends on.**
  - The B2 practice verbs landed. Queue the registration line against TN8 and SG5, which also edit `practice.py`.
  - Re-measure pedal timing at harmony-change attacks before claiming "legato pedalling". The lane's medians of 128-195
    ms after the latest attack may be chance in dense textures.
- **Needs an OK from.** Nobody (read only). The first readout goes to Daniel in chat.
- **Receipt.** Synthetic sessions with known roll spans, pedal offsets and top-voice velocities read back exactly, and
  the wording guard passes.

#### #13 Find it: ear cards from his own moves

- **What.**
  - A card plays a two-chord move Daniel himself played last week, and he finds it on the keys, in any key. The
    "answer" is his original moment replayed beside his new one. There is never a mark.
  - Shelf variant: a kept sound he has not played in 3 weeks comes back as a Tonight card.
- **Prior art.**
  - EarMaster: ear-training answers played on a MIDI keyboard: https://sonofield.com/blog/best-ear-training-apps-2026
  - ToneGym: https://www.tonegym.co/
  - Piano Companion flashcards with spaced review: https://www.songtive.com/products/piano-companion
- **Why it fits Daniel.** It builds the bridge from ear to name out of his own vocabulary (P6, "his moves are the
  textbook"). Sunshine's rule holds: prediction, never a quiz, with no counters or points (P9).
- **Plugs into.**
  - The replay companion's conversation cards, in flight: `py -m arsenal.replay cards`, `web/conversation.html`,
    answers saved by playing. A Find-it card's source excerpt is the move.
  - `practice` compares the saved answer's windows with the source in numbers ("same move, a 4th up") and shows it as
    two replays.
  - Later: a deck card kind (jam V2-B) and the Tonight tab.
- **Effort.** M.
- **Depends on.** The replay companion committed. TN8 is optional, so the numbers come through the new reader.
- **Needs an OK from.** Daniel, as taste: offer one card in chat first.
- **Receipt.**
  - The same move played in another key reads as the same numbers.
  - No score string appears anywhere (wording guard).

### 2.3 Analysis displays

#### #4 Voicing shape label

- **What.** A second word for how the chord is voiced, from small interval tests on the reading:
  - shell (root, 3rd, 7th);
  - rootless A or B;
  - quartal stack;
  - open 10th;
  - cluster on top (a 2nd in the top three voices);
  - spread;
  - drop 2;
  - upper structure (a triad over a dominant shell).
- **Prior art.** Chord ai claims voicing and position recognition from audio: https://chordai.net/
- **Why it fits Daniel.** His hands already make these shapes by feel, and he is learning the names for what they know.
  From exact MIDI the label is honest in a way audio apps cannot be.
- **Plugs into.**
  - An additive `shape` tag on theory-nextgen's `Reading` (`chordread.js`, TN1's file, present and untracked). TN0
    froze the shapes, so the tag needs a conductor note.
  - The words go in `lexicon.json` (D10).
  - Surfaces: the HUD line (3.3) at TN7; a riff fact ("7 of your 9 G♭ chords were cluster on top"); the Lesson view
    (TN11) later.
  - Not on the recorded canvas this round (theory-nextgen section 4).
- **Effort.** S.
- **Depends on.** TN1.
- **Needs an OK from.** Nobody.
- **Receipt.**
  - One fixture per shape in 12 keys.
  - His 24 vocabulary voicings, tagged and read to Daniel for a yes or no.

#### #9 Pedal depth logging, then pedal fog

- **What.** Two steps.
  - **(a) Log the pedal's depth.**
    - His KeyLab pedal sends continuous CC64, and the page keeps only crossings of 64. Even so, 42-52% of logged pedal
      events already carry values other than 0 or 127 (analysis lane; `chord-accuracy.md` 3.2).
    - Log a thinned curve: changes of 8 or more, or every 50 ms while the pedal moves.
    - Start early. Every later pedal receipt needs sessions logged with the curve.
  - **(b) Pedal fog.**
    - A haze over the low keys thickens when pedal-carried notes rub a semitone against new notes low in the register.
      It clears when he lifts. High overlaps count as shimmer, not fog.
    - It appears on the glass live, in re-renders (#7), and as a report line with Hear links.
    - The words are "fog" and "clear", never "blur" or "error". A deliberate wash is a colour.
- **Prior art.**
  - Pedal depth estimation: https://arxiv.org/abs/2510.03750
  - PercePiano's clean versus blurred pedal: https://github.com/JonghoKimSNU/PercePiano
  - Low interval limits: https://www.sweetwater.com/insync/low-interval-limit/
- **Why it fits Daniel.** Lush pedalled harmony is his style. Seeing when the low end muddies and when it shimmers is a
  real pianist's skill, and it looks lovely on video. The lane measured carried semitone rubs at 20-32% of carried
  attacks, and 8-18% below G3.
- **Plugs into.**
  - **(a)** `performance.py` KINDS first (server), then `log.js`. This is `chord-accuracy.md` C7. It needs its own
    log-schema wave, not shared with TN5 or spectacle P4, which also edit `performance.py`. Later, `harmony.js` treats
    a dip-and-return within 350 ms as a strong boundary.
  - **(b)** A `glass.js` layer (J8's file, edited again by V2-B), the render (#7), and a line in #2's verb.
- **Effort.** S-M for (a); M for (b).
- **Depends on.**
  - **(a):** J5 landed.
  - **(b):** (a); TN7; and a glass slot once the jam ghosts and suggestions have shipped. Theory-nextgen section 5 cut
    new key-top marks until then.
- **Needs an OK from.** The log-schema owner and the conductor for (a). Daniel (Q3) for fog on videos.
- **Receipt.**
  - **(a):** the log grows by a measured amount per minute, and batch validation still passes.
  - **(b):** Daniel's answers on about 20 "fog here?" moments agree before any threshold is trusted.

#### #11 The note that moved

- **What.**
  - At each settled chord change, pair old and new voices by least total movement, then show:
    - which notes held (common tones);
    - which moved, and by how many semitones;
    - whether the motion was contrary or parallel.
  - Moved keys flare, and a hairline arcs from the old key to the new one on the glass or in a render.
  - Triad moves get Tonnetz names in words ("one note moves: the relative minor").
- **Prior art.**
  - Tymoczko's voice-leading size: https://dmitri.mycpanel.princeton.edu/voiceleading.pdf
  - TonnetzViz (MIT) and its P, L and R moves: https://github.com/cifkao/tonnetz-viz
- **Why it fits Daniel.** It shows why his favourite moves feel smooth, and makes the seed card "One note apart"
  (jam-spec 12.3) visible on every change. It looks good on video.
- **Plugs into.**
  - A pure `voicemove.js` over harmony-window commits.
  - Glass arcs; riff counts; P, L and R words in `lexicon.json`.
  - This is the key-top version of theory-nextgen's deferred staff ghost column (section 5), so it avoids the staff
    texture upload that blocked that idea.
- **Effort.** M.
- **Depends on.** TN7; the hand split (#2); the same glass slot as #9(b). Rate-limit it to settled windows:
  theory-nextgen measured about 49 commits a minute.
- **Needs an OK from.** Daniel (Q3), for video.
- **Receipt.**
  - Synthetic moves (one-note, half-step, contrary) read back correctly.
  - Arcs per second stay under a cap.
  - A render snapshot is looked at.

#### #14 Progression family and arrivals

- **What.**
  - When a committed loop of 3-4 windows matches a known family, name it in players' words: "1-5-6-4, the pop axis",
    "2-5-1", "backdoor", "lament bass", "turnaround".
  - Name arrivals (authentic, plagal, deceptive, half) from cadences backed by a pedal lift or a dynamic fall.
  - The table is ours, in Nashville numbers, with a few song examples written by us.
- **Prior art.**
  - Hooktheory Trends and TheoryTab: https://www.hooktheory.com/trends
  - Impro-Visor's named "bricks" (GPL: write our own table): https://github.com/Impro-Visor/Impro-Visor
  - DCML cadence labels (non-commercial: private tests only): https://github.com/DCMLab/distant_listening_corpus
- **Why it fits Daniel.** These are the words an ear player needs to talk with other musicians. "Same move as ..." is
  caption material.
- **Plugs into.**
  - A new tracked `progressions.json` table, safe for the public repo.
  - A matcher over `practice progressions` output and harmony windows; `cadence_kinds` already exists in
    `practice.py`.
  - Surfaces, in this order:
    1. `practice brief` and riff (chat);
    2. the HUD;
    3. render overlays;
    4. the Nashville row, only on a sure match and only through D8's priority, after TN9.
- **Effort.** M.
- **Depends on.** TN4's function words and lexicon; TN8, so practice reads through the reader.
- **Needs an OK from.** Daniel (Q4) before any non-commercial data, such as Chordonomicon rarity. Daniel also reads
  Hooktheory's terms before any use of their data; the default is none.
- **Receipt.**
  - Table fixtures pass in 12 keys.
  - No match while the key is unsure.
  - A caption-priority test against D8 passes.

### 2.4 Chord accuracy

#### #3 Measure against his ear

- **What.** Three pieces.
  - **Gold set** (C1). 150-300 disputed windows, weighted toward leaning, ambiguous and loss windows. Each is
    replayed; Daniel picks the name or names he accepts, or "none of these". About 20 minutes per 100 windows.
  - **Field scoring** (C2).
    - Root, thirds, triads, sevenths and tetrads, each with its bass-aware variant and weighted by duration.
    - Over- and under-segmentation, so boundary misses stop hiding inside naming misses.
    - A Harte export through `parseSuffix`. The metrics are reimplemented, so nothing is installed.
  - **Textured test streams** (C5). His 24 voicings and the 17 seed cards, in 12 keys, rendered through `groove.js`
    textures: rolled, arpeggio under pedal, walking bass, passing melody, re-pedal.
- **Prior art.**
  - The Chordify annotator dataset (CASD): 4 experts agree on about 73% of simple labels and 54% of complex ones: https://github.com/chordify/CASD
  - mir_eval chord metrics: https://mir-eval.readthedocs.io/latest/api/chord.html
  - AugmentedNet, where block chords did not transfer to real textures and textured synthetic data did: https://archives.ismir.net/ismir2021/paper/000050.pdf
- **Why it fits Daniel.**
  - Today every number compares our reader with our own offline engine (theory-nextgen risk 1).
  - For his colours, only his ear is truth, and several names can be right.
  - The labelling doubles as a listening session.
- **Plugs into.**
  - The gold set goes through the replay companion's conversation cards, with the top 3 names as choices, not a new
    UI. Answers stay private under `state/`.
  - Scoring is a new lane, `arsenal/lanes/theory_scoring.mjs`.
  - The streams join the TN0 corpus through the conductor.
  - NG2 is then reported against the gold set beside offline agreement.
- **Effort.** M for the gold set, S for scoring, S-M for the streams.
- **Depends on.** TN1's names; the replay companion committed.
- **Needs an OK from.** Daniel (Q2, 20 minutes); the conductor for the corpus addition.
- **Receipt.** At least 150 labelled windows, with each engine's top-1 and top-3 hit rates against them.

#### #5 Cheap accuracy trio

- **What.**
  - **Context re-rank** (C3). When a window closes, re-rank its top 3 names by the chords either side: root motion in
    fifths, staying in the key, shared tones, bass steps.
    - The log takes the re-ranked name.
    - The live label swaps in place only while the chord still sounds.
  - **Per-part confidence** (C4).
    - Root and bass commit at the settle.
    - A change that keeps both is a `grow`, never a pop.
    - The HUD can say "root sure, colour unsure".
  - **Roll grouping** (C9). Notes sweeping one way with gaps of 90 ms or less, within 300 ms in total, count as one
    attack. This replaces the fixed 50 ms group; the lane measured sweep spans with a p90 of 96 ms.
- **Prior art.**
  - Chord-level language models add about 2 points; frame-level ones add almost nothing: https://arxiv.org/abs/1808.05335 and https://arxiv.org/pdf/1702.00178
  - BACHI decodes root, then quality, then bass: https://arxiv.org/abs/2510.06528
  - Pardo and Birmingham treat attacks as events: https://interactiveaudiolab.github.io/assets/papers/pardo-birmingham-cmj02.pdf
- **Why it fits Daniel.**
  - In the leaning and ambiguous bands the right name is already in the top 3 for 91-95% of windows, but first only
    56-69% of the time.
  - The estimated gain is +2 to +4 points of static agreement, from arithmetic on the band table, not measured.
  - Fewer pops is the steady name he chose (theory-nextgen Q3).
- **Plugs into.**
  - TN1: C3 and C4 are pure functions over `readings`.
  - TN2: C9 and the `grow` rule go in `harmony.js`.
  - Receipts: NG2 and NG5.
- **Effort.** S-M in total.
- **Depends on.**
  - The TN1 and TN2 owners.
  - Confirmation on #3's gold set. The offline reference itself uses context, so agreement could rise by construction.
- **Needs an OK from.** Nobody; the conductor sends a note to the TN owners.
- **Receipt.**
  - NG2 gains and losses in both directions.
  - Pops per minute and median label life, from the calibrated replay (D14).
- **Next in this group, not ranked.** Salience v2 (C6): decay, register, passing tones that resolve by step, and beat
  accent when a grid exists (this absorbs products' beat-grid prior). Then a duration prior (C12). Both are tuned
  against the gold set only.

#### #12 Call it

- **What.** From the HUD (never recorded) or a conversation card, Daniel picks the right name for a chord.
  - The choice is stored as a key-free fingerprint: the intervals above the bass, plus the bass's degree in the key.
  - It applies in all 12 keys, and same-fingerprint windows in the session are re-named.
  - The HUD shows it as "your name".
  - Fixtures always win.
  - C8's automatic weight nudge stays off until the gold set shows it helps.
- **Prior art.**
  - Serenade, human-in-the-loop chord correction: https://arxiv.org/abs/2310.11165
  - Chord label personalisation (Koops et al.): https://arxiv.org/abs/1706.09552
  - Correction loops in Chordify, Logic and Scaler (`products.md` 4.5).
- **Why it fits Daniel.**
  - He is the authority on what he means.
  - His vocabulary is concentrated, so 20-30 corrections should cover most of his loss time (estimate).
  - It revives theory-nextgen's deferred reading pins in a shape that keeps the screen, log, rarity and suggestions in
    agreement.
- **Plugs into.**
  - The reader consults the store before ranking (`chordread.js`).
  - The store is `state/arsenal/piano/names-daniel.json`, deliberately not `lexicon.json`, which is theory-nextgen's
    words file (D10).
  - A HUD control at or after TN7; a conversation-card path; `practice brief` lists the overrides.
- **Effort.** M.
- **Depends on.** TN9's first night held; #3, which shares the card UI; the conductor, because it sits next to the
  frozen corpus.
- **Needs an OK from.** Daniel and the conductor.
- **Receipt.**
  - A correction replayed in 12 transpositions gives identical names.
  - NG1 and NG2 stay green after 30 scripted corrections.

### 2.5 Content formats

#### #7 Offline re-render with a hindsight layer

- **What.** Replay a logged take into the page at a fixed timestep and record every frame, instead of capturing live.
  - **No live limits.** No dropped frames, and any size up to the render budget.
  - **Hindsight.** The render knows the future, so analysis that is unsure live is exact here: phrase arcs, the note
    that moved (#11), pedal fog (#9), arrivals and family titles (#14). All of it comes from one analysis file written
    by the practice verbs, so the video and the report never disagree.
  - **Audio.** Export the same span with #10, Daniel renders it through Kontakt in FL, and the render muxes that file.
    The clip sounds like his real instrument.
  - **Tidy pass.** An optional tidy pass edits the replay only, never the log.
  - **Honesty.** The live canvas stays his (P10), and the caption never claims live analysis.
- **Prior art.**
  - SeeMusic renders 4K faster than realtime and aligns camera footage: https://www.seemusicapp.com/
  - LumaKeys has 4K export: https://lumakeys.app/
  - Our own `design-loot-feel.md` (spectacle folder, "Replay the moment", listed as later).
- **Why it fits Daniel.** He can play freely and pick the best 40 seconds afterwards, with no performance pressure. The
  rich analysis reaches TikTok without cluttering practice.
- **Plugs into.** Checked tonight, and this is new:
  - Spectacle 3.4 plans live capture only.
  - `recorder.js` already writes constant-frame-rate H.264, but it assigns frames to wall-clock slots. It needs a
    frame-index clock mode.
  - Spectacle 3.4 makes every effect a function of the clock, so a virtual clock makes renders deterministic.
  - `pianocue.build_replay_cue` already rebuilds onsets, velocities and pedal durations from the log.
  - The render mode feeds Daniel's notes through the normal input path, so labels, colours and rarity are his, with
    logging switched off.
  - It needs one `piano.js` wave, plus a practice verb that writes the hindsight file.
- **Effort.** M-L.
- **Depends on.** Spectacle P2-P3; TN7; the recorder committed; #10 for audio. The hindsight items (#9b, #11, #14 and
  phrase boundaries) plug in as they land.
- **Needs an OK from.** Daniel (Q3).
- **Receipt.**
  - A render reproduces the live label sequence of the same span exactly.
  - Frame count equals duration times fps.
  - Zero log writes happen during a render.
- **Phrase boundaries in free play.** Use the analysis lane's multi-cue vote: lengthening, pedal lift, velocity dip,
  arrival, silence. Riff 9.9's gap-only split found only 2-56 phrases per session in pedalled free play.

#### #10 Moment to FL

- **What.** `py -m arsenal.practice moment <t> --mid out.mid` turns any log moment into a MIDI file: notes,
  velocities, pedal CC64, and our chord names as marker text. In FL Studio it plays through Kontakt and can start a
  project. FL 2026's own Chord Panel re-reads it, a free second opinion on our names. Spot-check that with Daniel,
  never automatically.
- **Prior art.**
  - Scaler's drag-to-DAW MIDI: https://scalermusic.com/products/scaler-3/
  - FL Studio 2026's Chord Panel detection: https://blog.dubspot.com/fl-studio-2026-whats-new
- **Why it fits Daniel.** FL is his DAW. Improvisations become songs and real-instrument audio for videos. It is the
  cheapest bridge to content.
- **Plugs into.**
  - The `practice.py` `moment` verb: read-only on the log, one file written where he names it.
  - Build the SMF writer once and share it with jam V2-E's card export (`arsenal/jam/smf.py`). If V2-E is later,
    create the writer here and hand it over.
  - It feeds #7's audio.
- **Effort.** S.
- **Depends on.** B2 landed.
- **Needs an OK from.** Nobody. It writes a file; nothing is downloaded and no MIDI goes out live.
- **Receipt.**
  - Round trip: onsets within 1 ms, velocities and pedal identical.
  - Marker names equal the logged names.

#### #15 End-of-night poster

- **What.** `py -m arsenal.practice map` writes one 9:16 image, on request:
  - an 88-key heat strip (finger versus pedal-carried);
  - a register line;
  - the night's key journey on a circle of fifths, or a wavescape, which does not force modal vamps into major or
    minor;
  - the sounds he kept.

  No counters, and no "best".
- **Prior art.**
  - Sapp's keyscapes: https://mazurka.org.uk/info/keyscape/
  - Wavescapes: https://journals.sagepub.com/doi/full/10.1177/10298649211034906
- **Why it fits Daniel.** A TikTok end card, and a night at a glance in the page's own pitch colours.
- **Plugs into.**
  - A new `arsenal/practice_map.py` with a registration line.
  - Key paths from `practice keys`; touch data from #2.
  - SVG first, which needs no install. PNG through an already-approved path: the headless page snapshot, or PyAV.
- **Effort.** S-M.
- **Depends on.** Nothing hard; #2's hand split colours the hands.
- **Needs an OK from.** Nobody; it runs on request only.
- **Receipt.**
  - A synthetic session gives the expected heat and key path.
  - The image contains no session id and no clock times.

---

## 3. Not in the top 15 (parked or refused)

| Item | Status | Reason and trigger |
|---|---|---|
| Streaks, stars, percentages, red notes, leaderboards | refused | P9. Evidence in the analysis lane: gamified motivation fades after the novelty. |
| Melody lead in ms | refused | Measured median 0 ms; show balance instead (#2). |
| A neural model naming the live label; frame-level smoothing | refused | `chord-accuracy.md` "What not to do": latency, no coverage of his colours, and no gain at frame level. |
| Calendar of nights with no counter | parked | `products.md` Q2 default is no. Revisit only if Daniel asks. |
| Spoken coach line after a run (TTS) | parked | Default no; never during REC (`products.md` Q3). |
| Model jam partners (ReaLchords, Notochord, Aria, Magenta RealTime) | parked | Rules first; install weight and CPU latency on this AMD machine. Revisit after the jam has had real nights. |
| Tension braid (separate rub, distance, lean and time strands) | parked | Study and render only, to respect P6 and the theory-nextgen tension cut. After #7. |
| Performance worm, motif returns, novelty form strip, style palette, melodic surprise, inner-voice lines | parked | Need phrase boundaries, a pulse gate and gold taps first. They slot into #7's hindsight layer later. |
| Chord lock-in animation (root, then quality, then bass) | parked | Visual idea from BACHI. Only after #5's C4 exists; it must not add pops. |
| Beat-grid prior | merged | Into #5's follow-on (C6 beat accent). |
| KeyLab 88 mk3 Chord-mode card | tonight, no code | Section 6. The `controller_mode` session meta waits for the log-schema wave. |
| Simple name level for recordings (C13) | parked | Theory-nextgen D4 cut presets; revisit with the Lesson view (TN11). |
| Harmonise my top note chips | parked | After suggest-lights SG8. |
| Page follows your piece (Matchmaker); JJazzLab beside FL | parked | Not asked for. Matchmaker is Apache-2.0; JJazzLab is LGPL and would run as a separate app. |
| Stem separation ("mute the song's keys") | parked | Download needs Daniel's approval; local files only, never Spotify audio. |
| Loopback audio features (Meyda) | parked | Routing needs Daniel's OK. Essentia.js is AGPL-3.0, so it stays out of the public repo. |
| POP909-CL and When in Rome benchmarks, BACHI as an offline judge (C14) | parked | Downloads need approval. After the gold set (#3), so labelling time goes to the disputed windows. |
| Mood word per session; named moments | parked | Cheap, but nobody has asked. Fold into the log-schema wave if Daniel wants them. |

---

## 4. For Vandor (not for Daniel): collisions and reconciliations found in this pass

- **Port collision.**
  - The replay companion listens on `127.0.0.1:8796` by default (`arsenal/REPLAY.md`).
  - jam-spec 13.1 rule 7 gives 8796 to J7's live checks, and theory-nextgen reserves 8795-8798.
  - Move one of them. The companion already has `--port`.
- **Name collision.** `products.md` proposed `state/arsenal/piano/lexicon.json` for Daniel's corrections, but
  `lexicon.json` is theory-nextgen's words file (D10). This plan uses `names-daniel.json` (#12).
- **Reuse instead of new UI.** The replay companion (untracked, in flight) already has looping excerpts, a chord strip
  and cards answered by playing. #1's preview, #3's gold set, #12 and #13 should build on it, not on new pages or
  verbs. Get it committed and its owner named before those items start.
- **Wave queues.**
  - **`piano.js`** is now wanted by TN7, SG7, AL7b, V2-B, V2-D, V2-E, V2-G and TN10, plus #1, #7 and #9(b). Each needs
    its own integration wave.
  - **`glass.js`** is wanted by V2-B, SG6, #9(b) and #11.
  - **`performance.py`** is wanted by TN5, spectacle P4 and #9(a).
  - **`practice.py` registration lines** are wanted by TN8, SG5, #2, #10 and #15.
  - The conductor should sequence all four queues.
- **Frozen contracts.** Reserve names in jam-spec 4.5 now: the `loop_me` run kind and the `cycle`, `speed`, `slices`
  and `lookahead` run fields. Reserve an additive `shape` tag on `Reading` with the TN0 owner.
- **Claims to re-measure before they reach Daniel.**
  - Pedal presses at harmony-change attacks, not all attacks (#2).
  - The C3 gain estimate, on the gold set (#5).
  - Every analysis-lane threshold: pulse clarity 0.3, fog register weights, phrase votes.
- **Offline re-render is verified new.** Spectacle 3.4 is live capture only, and `recorder.js` slots frames by wall
  clock. B12 in `products.md` therefore stands as a new item (#7), not a confirmation.
- **Tension display conflict.** The open-source lane's single tension ribbon conflicts with P6 and theory-nextgen's cut.
  The analysis lane's braid (separate strands, Study and render only) resolves it; it is parked in section 3.
- **Missing lane file.** The analysis-displays report was never written to this folder, because the harness refused
  it. Save its text as `analysis-ideas.md` here if the lanes are ever committed.
- **Privacy.** `design-data.md` and `design-music.md` in the jam folder name session ids (jam-spec 16), and the replay
  companion's cards and answers are private state. Neither this file nor the three lane files in this folder carry
  session ids.
- **Licences, for a public Apache-2.0 repo.**
  - Port ideas, or code under MIT, BSD or Apache.
  - GPL projects (Impro-Visor, IDyOM, Neothesia, Somax2) are study only.
  - Non-commercial data (Chordonomicon, DCML, Hooktheory TheoryTab, ACCompanion models) stays local and never appears
    on video, pending Q4.

---

## 5. Sources

Each card in section 2 links its own prior art. The lane files hold the full lists: `products.md` section 9,
`open-source.md` sections 2-5, `chord-accuracy.md` section 6. Local files cited: `arsenal/REPLAY.md`,
`arsenal/pianocue.py` (`build_replay_cue`, `replay-link`), `arsenal/web/piano/recorder.js` (wall-clock frame slots),
`arsenal/practice.py` (verbs, `cadence_kinds`, `touch_data`, `harmonic_windows`).

---

## 6. Tonight, this week, later

**Tonight** (touches no build in flight):
1. **Daniel tries KeyLab Chord mode, with no code.** He captures his G♭maj13♯11, plays it from one key with the left
   hand, and solos with the right. Tell him in chat that the log will record the notes the keyboard generates, so that
   session's stats describe the mode, not his hands.
2. **A Loop me preview, with no code.** `py -m arsenal.pianocue replay-link latest <m:ss> --seconds 8`, with the
   standalone player on loop while he plays over it. It is not snapped to bars, and it uses the built-in voice. The
   companion must be running, on a port other than 8796.
3. **Send Daniel the four questions** in section 7.
4. **Vandor's notes to owners.**
   - TN1: C3, C4 and the `shape` tag.
   - TN2: C9.
   - Conductor: the 4.5 name reservations and the textured-stream corpus addition.
   - Log-schema lane: the pedal-curve kind.
   - Replay companion: the port move.
5. **A read-only re-measure.** Pedal-press offsets at harmony-change attacks, as a scratch script that outputs counts
   only.

**This week:**
- #4 and #5 ride inside TN1 and TN2 as those phases run.
- #3: the scoring lane and textured streams; gold-set cards drafted once TN1 names exist. Daniel's 20-minute sitting
  happens when he is home.
- Once B2 lands: #10 (`moment --mid`, S), then #2 (`practice touch`, M), both as new files with registration lines.
- #9(a): pick the log-schema wave and start logging pedal depth, so data accumulates.
- One-page specs for #1 and #8, so the jam's v2 waves have them ready.

**Later:**
- After J10: #8 (with V2-A and V2-G), #1 in its own wave, #13 on the conversation cards.
- After TN7 and TN9: #6, #11, #9(b), #12, #14.
- Content wave after spectacle P3: #7, then #15. The parked items in section 3 join #7's hindsight layer one at a time.

---

## 7. Questions for Daniel (four, each with a recommended default)

1. **Which jam feature first: Loop me, or the band following your chords?** Loop me: you play a few bars and play over
   yourself. Band follows: bass and soft chords join whatever you hold.
   *Default: Loop me first. It is smaller, and it is your own sound and timing from the first night.*
2. **Would you spend about 20 minutes naming about 100 chords by ear?** The page replays each one, and you pick the
   name you hear, or say none of them. This is what makes "better chord accuracy" measurable instead of a guess.
   *Default: yes, in one sitting once the new names have landed.*
3. **Should the extra analysis go on videos only through re-renders?** Your live takes stay exactly as they are.
   Replayed clips could show phrase arcs, the note that moved, and pedal fog, all drawn with hindsight.
   *Default: yes, re-renders only.*
4. **Are your TikToks monetised, or might they be?** Some music datasets are free only for non-commercial use.
   *Default: treat the videos as commercial. Those datasets are used only for private measurement, never for anything
   shown on video.*
