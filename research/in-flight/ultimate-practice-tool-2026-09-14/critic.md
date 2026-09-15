# Critic pass: the ultimate practice and jam plan

| | |
|---|---|
| Type | research (in flight), critic pass |
| Date | 2026-09-14 |
| Author | Vandor (claude seat), critic subagent |
| Reviews | `ultimate-practice-plan.md` and its lane files `products.md`, `open-source.md`, `chord-accuracy.md` (this folder) |
| Method | Primary sources re-read tonight: vendor pages, manuals, release notes, papers (abstract or full text), GitHub API for licences. Local claims checked with grep and read only. Paraphrased; no long quotes. |
| Status | Research only. No `arsenal/` edits, no servers, browsers, downloads, installs, logins or purchases. |
| Privacy | No session ids, clock times or transcriptions. No practice log was opened; only code and spec files. |

Confidence labels: **verified** = primary page or paper text read tonight; **medium** = search summary of a primary page,
or a secondary source; **unverified** = could not confirm.

---

## 0. In one screen

**The plan's spine holds.** Loop me, touch facts, measuring accuracy honestly and keeping the live canvas clean are all
sound. But nine corrections change the ranking, and two headline claims to Daniel are overstated.

**Two headline claims to fix before Daniel reads them.**

1. **"Nobody else does the thing you love" is too strong.** Several products name chords from live playing:
   - FL Studio 2026, Daniel's own DAW: the new Chord Panel names chords from live MIDI input, capped at 10 notes. The
     release notes don't mention the pedal. Verified.
   - Neothesia v0.4.0 (January 2025) added chord names in free play. Verified.
   - Yamaha's AI Full Keyboard reads chords from both hands anywhere on the keyboard, and has for years. Verified.
   - UJAM Virtual Bassist follows chords you play. Medium.
   - Audio detectors such as Chord ai hear a pedal wash because the strings really ring.

   What we can honestly say: none of the product documents found describe naming pedal-held arpeggios from MIDI.
   *Turn this into a 5-minute test tonight, with no code:* play the same pedalled arpeggio with FL's Chord Panel open
   beside the page.
2. **"No app reads these three from MIDI" is too strong.** PianoTrace, sold as TempoPro (Apple only), says it
   evaluates pedal use, dynamics and articulation from MIDI (verified). The three specific measures (pedal against
   chord changes, roll against block, top-voice balance) still look unclaimed. Say that instead.

**Ranking changes (details in section 2).**

| Plan # | Item | Change | Why, in one line |
|---|---|---|---|
| 10 | Moment to FL | **up to #3** | FL's own MIDI logger keeps notes but, per user reports, drops the pedal. The Chord Panel second opinion needs no file. |
| 3 | Measure against his ear | **redesign, stays #4** | Our losses are the same notes under two names; an ear player can't settle a naming convention by ear. Use A/B of voicings. |
| 5 | Cheap accuracy trio | **stays #5, claim halved** | The cited chord-level language model gain is about +1.0 point, not about +2. |
| 8 | Run routines | **up to #6** | iReal Pro's tempo ramp has no gate. Dropping the "clean pass" gate removes a hidden grade and the J4 dependency. |
| 9a | Pedal depth logging | **up to #7** | Small, already decided by the piano-ideas panel (item 9), and every later pedal receipt waits on its data. Fog (9b) becomes render-only. |
| 6 | The band follows | **down to #8, add try-before-build** | Arranger keyboards and chord-following bass plugins are 20+ years of prior art; Daniel can try one before an L build. |
| 7 | Offline re-render | **stays #9, not new** | `live-sheet-music` Path B already plans a full-take replay re-render through `recorder.js`. Merge, and add the camera composite. |
| 4 | Voicing shape label | **down to #10** | theory-nextgen already tags upper structure, polychord, quartal and cluster. The rest needs the hand split, not just TN1. |
| 11 | The note that moved | **down to #14** | P, L and R are triad-only moves (rare in his extended chords); live arcs hit the deferred ghost-column problem. |
| 15 | Poster | **stays #15, needs Daniel's OK** | It is built to publish practice data. |

**Also missing from the plan:**
- A whole sibling spec: `live-sheet-music-2026-09-14` (hand split, roll rule, pedal lag, beat tracking, replay
  re-render, an in-house MIDI writer).
- Obvious competitors: Ableton Capture MIDI, FL's own loggers and Chord Panel, arranger keyboards, UJAM, PianoTrace,
  Midiano.
- Four modalities: jamming with other people, voice, the camera, and aftertouch or release articulation (section 6).

---

## 1. Fact-check of load-bearing claims

### 1.1 Chord accuracy and research

| Claim (where) | Verdict | Primary source and note |
|---|---|---|
| CASD experts agree on about 73% of major/minor labels and 54% of the most complex (plan #3; chord-acc 1.5) | **Holds** | JNMR 2019 abstract (Semantic Scholar record). The same abstract says algorithms score about 10% above that ceiling, i.e. they fit one annotator, which supports scoring against several accepted names. **Missed:** CASD itself is CC BY-NC-SA 4.0 (repo badge). Fine to cite numbers; don't use the data. |
| Chord-level language models add "about 2 points" (plan #5; chord-acc 1.4, C3) | **Wrong, about half** | Korzeniowski & Widmer, ISMIR 2018, Table 3: standard model to best model moves major/minor WCSR from 0.795 to 0.805 (+1.0), root from 0.812 to 0.821, segmentation from 0.804 to 0.814. The authors call the gains modest but consistent. It is also audio with 25 classes, so it transfers weakly to MIDI top-3 re-ranking. The +2 to +4 estimate now rests only on our own band arithmetic. |
| Complex frame-level language models add almost nothing (plan #5, section 3) | **Holds** | arXiv 1702.00178 abstract (Korzeniowski & Widmer 2017). |
| BACHI classical root 77.8, quality 79.0, bass 77.0, full 68.1; POP909-CL full 82.4; ChordGNN 58.5 (chord-acc 1.3) | **Holds** | arXiv 2510.06528 HTML, Table 1. Code MIT (repo). ICASSP 2026. |
| POP909-CL fixed about 35% of chord labels (open-source 2.1) | **Holds** | POP909-CL README: about 35% chord label errors, 40.6% start beats, 14.2% key changes, 2.6% time signatures. MIT. |
| POP909-CL corrections "added about 15 points of full-chord accuracy" (chord-acc 1.6) | **Wrong** | The paper contrasts the original rule-based labels (about 65%) with BACHI's 82.4%. That is a model result, not the size of the correction. Minor; doesn't change rank. |
| AugmentedNet: block chords did not transfer, textured synthetic data did (plan #3; chord-acc C5) | **Holds, slightly strong** | ISMIR 2021 paper text: plain block-chord examples were only slightly beneficial, so the authors texturized them (bass split, Alberti bass, syncopation). `open-source.md` 2.1 calls it "synthetic block-chord augmentation" and omits the texturing, which is the part that matters. |
| Goebl: melody lead is a velocity artefact (plan #2) | **Holds** | JASA 110(1) 2001 (PubMed / author PDF): the lead shrinks to near zero at the finger-key level. |
| Pedalling taxonomy, zenodo 3242149 (plan #2) | **Holds, better than used** | Liang (QMUL, 2017) Disklavier dataset. Timing classes: anticipatory, rhythmic, legato. Depths: 127, 96, 64. **Use these established names** in #2 instead of the plan's clean/gap/smear. |
| PercePiano: pedal clean or blurred, timing stability (plan #2, #9) | **Holds** | Repo: 19 features, including two pedal labels and two articulation labels. MIT. |
| Profy, arXiv 2606.10627 (plan #2) | **Holds** | Submitted 2026-06-09. Passage-level highlights from keyboard motion plus audio, 73 pianists; agreement with experts r = 0.61. |
| ReaLJam: chords shown 4 beats ahead, uncommitted see-through, commit 0/2/4 tested, players disagreed (plan #8) | **Holds** | arXiv 2502.21267 HTML. Players split on showing chords, commit length and the metronome. Paper CC BY 4.0; code in realchords-pytorch, MIT (GitHub API). |
| Aria-Duet hands the turn over with a pedal (plan #1) | **Holds** | arXiv 2511.01663: the left (una corda) pedal; Apple Silicon plus a Disklavier; continuous prefill removed a 1-2 s delay. |

### 1.2 Products

| Claim (where) | Verdict | Primary source and note |
|---|---|---|
| Scaler 3 Multi-Bind and performance recording as prior art for Loop me (plan #1) | **Holds as facts, weak as prior art** | scalermusic.com: Multi-Bind loops several chord and Motion lanes, and User Track records performances as MIDI. Neither captures and loops what you just played freely. The real prior art is **Ableton Capture MIDI** (section 6). |
| Soundslice loops snap to note, rest or barline (plan #1) | **Holds, wrong URL** | Stated on Soundslice's Looping help page. The cited blog post (199) is about loop timing, not snapping. |
| Studio One Follow Chords: Narrow, Parallel, Bass (plan #6) | **Holds** | Audeobox guide and Sound On Sound agree. Current product naming not checked. |
| Logic Session Players follow the Chord Track, with Complexity and Intensity (plan #6) | **Holds** | Apple guide (Chord Track following); Sound On Sound and MusicRadar summaries (slider names). Medium on names. They follow chord tracks and regions, not free live playing. |
| Band-in-a-Box lets the player take over the piano part (plan #6) | **Unverified** | Not found on `bbwin.htm` or `bbwin.features.htm`. Drop the citation or find the page. |
| Logic 12 Chord ID detects harmonic rhythm (plan #2) | **Holds** | CDM hands-on: impressed by harmonic rhythm, imperfect on dense material. |
| iReal Pro key cycling and automatic tempo increase (plan #8) | **Holds, and matters** | iReal help and practice pages: +1 to 20 BPM **on every repeat, no condition**; transpose by 1 or 5 half-steps per repeat. |
| Melodics Auto BPM (plan #8) | **Holds** | Melodics support: +10 BPM when you're doing well, up to track tempo. This one is gated. |
| Chord ai claims voicing and position recognition (plan #4) | **Holds on App Store only** | The App Store listing claims a world-first for voicing recognition; chordai.net's own page does not. Pro is $10.99/mo or $69.99/yr (App Store). |
| ROLI AI Music Coach: harmony, rhythm, dynamics (plan #2) | **Holds, wrong citation** | The five dimensions (postural, positional, harmonic, rhythmic, dynamic) are on roli.com's Airwave Learn page, not in the cited MusicTech piece. It relies on camera hand tracking. |
| SeeMusic renders 4K faster than realtime and aligns camera footage (plan #7) | **Half** | seemusicapp.com confirms syncing video footage with falling notes and a MIDI editor. Faster-than-realtime 4K is not on the page. |
| LumaKeys 4K export (plan #7) | **Holds** | lumakeys.app: Mac only (Windows in development). Pro $69 launch price, then $99. The "until 2026-10-15" date was not seen. |
| FL Studio 2026 Chord Panel detection (plan #10) | **Holds, and stronger** | Image-Line release notes: detects chords from MIDI input, the typing keyboard and piano-roll selections, max 10 notes. It works **live**, so the second opinion needs no `.mid` file. |
| KeyLab 88 mk3 Chord mode: capture a chord, play it transposed (plan section 6) | **Holds (medium)** | Manual via search: user chords up to 16 notes, transposed from any key, strum and spread. Arturia overview: up to 4 pedals, switch or continuous sustain with calibration, channel aftertouch. |
| Scaler Detector (products 2.1) | **Holds** | KVR: released 2025-10-22, $9 or free with Scaler 3. Live MIDI detection not stated. |

### 1.3 Licences (plan section 4, open-source 7)

Checked through the GitHub API tonight:
- **As the lanes say:**
  - GPL-3.0: Neothesia, IDyOM, Somax2, BPS-FH.
  - Other copyleft: Impro-Visor GPL-2.0; JJazzLab LGPL-2.1; Essentia.js AGPL-3.0.
  - Permissive: Meyda, MIDIVisualizer, TonnetzViz, realchords-pytorch, PercePiano, PM2S, AugmentedNet and POP909 are
    MIT; Matchmaker and ACCompanion code are Apache-2.0.
  - Chordonomicon is CC BY-NC 4.0 (Hugging Face card).
- **Wrong: When in Rome is CC BY-SA 4.0, not CC BY 4.0** (repo README). ShareAlike means a table derived from it can't
  sit in the Apache repo without SA terms, so keep it local like the NC sets.
- **Missed:** CASD is CC BY-NC-SA 4.0.

### 1.4 Local claims

| Claim | Verdict | Where checked |
|---|---|---|
| Replay companion defaults to port 8796, colliding with jam J7 | **Holds** | `arsenal/REPLAY.md` lines 41, 49, 64 |
| `recorder.js` assigns frames to wall-clock slots | **Holds** | `arsenal/web/piano/recorder.js` header comment |
| The page logs the CC64 value only at the crossing of 64 | **Holds, stale line numbers** | `setSustain` is now at `piano.js` 2015-2021, not 1976-1983 |
| Crossing values show a continuous pedal | **Holds for hardware, not for technique** | The KeyLab mk3 accepts continuous sustain pedals. A value at the moment of crossing proves the pedal is continuous; it says nothing about half-pedalling. Only the curve log (#9a) can show that. |
| Spectacle 3.4 is live capture only, so #7 is "verified new" | **Wrong conclusion** | `live-sheet-music-2026-09-14/rendering-formats.md` Path B plans a full-take replay re-render through `recorder.js`, and D5 recommends it for posting. The plan never checked that folder. |

---

## 2. Card by card: what changes

### #1 Loop me (stays #1)
- **Prior art.** Replace Scaler Multi-Bind with **Ableton Capture MIDI** (Live 12 manual). It recovers what you just
  played without recording, detects tempo (80-160 BPM) and loop boundaries from the phrase, starts the loop, and lets you
  overdub.
  - That answers the card's open "no run tempo" case: estimate tempo and loop length from the captured phrase itself.
  - Clamp the estimate to his playing range.
- **House-rule gap.** The loop is Daniel's own playing, not Claude's. jam-spec Q1 (section 15) only decides Claude's
  backing. The card keeps the loop out of the take yet sells "a layering format for TikTok". Those two contradict.
  - Add a question for Daniel: "Should your loop be heard in your recordings?"
  - Recommended default: no for live takes; layered videos come through re-renders (#7).
  - Add jam Q1's warning: if Chrome plays through the Focusrite and he records its Loopback, the loop leaks into the
    take anyway.
- **Zero-code preview tonight.**
  - The replay-link preview keeps the pedal. It needs the companion running on a port other than 8796.
  - FL's other route (dump the MIDI log into a looping pattern, Kontakt sound) is simpler, but per a user report on
    Image-Line's forum it loses CC64. That route is mush for his pedalled playing.
  - Tell Daniel both routes and the trade-off.

### #2 Touch facts (stays #2)
- **Soften the "no app" claim** as in section 0. PianoTrace grades pedal and dynamics; ours describes without grading.
- **Name the pedal timing the established way.** Liang's pedalling data uses anticipatory, rhythmic and legato.
  "Legato pedalling" (press just after the new chord) is the name a teacher would use, so use it over clean/gap/smear.
- **Duplicate definitions to reconcile before building.**
  - `live-sheet-music/transcription.md` already defines a rolled chord, a hand split (largest gap plus continuity, T5)
    and a measured pedal-down lag (median 110-190 ms).
  - The ultimate plan's C9 uses a third roll rule (gaps of 90 ms or less, 300 ms total), and `products.md` a fourth
    (block under 30 ms).
  - One definition, one owner. Otherwise the score, the chord name and the touch facts will disagree about what a roll is.
- **Harmonic rhythm "every 2 beats"** needs a beat grid. Without a run tempo, say it in bars only when a tempo exists,
  otherwise in seconds.

### #3 Measure against his ear (redesign, stays top 5)
- **The flaw.** The design has Daniel pick theory **names**. He is an ear player still learning them. Worse,
  `design-engine.md` section 9 (line 336) says the losses are same-note mirrors: 2m-over-4 against 4maj13#11, or a 6/9
  in inversion against a minor 7(11). With identical notes the ear cannot decide. What decides is what comes next, or
  a naming convention.
- **Fix: three kinds of window, three kinds of truth.**
  1. **Pitch-content disputes** (a note counted or not, a passing tone): A/B by sound. Play each candidate's clean
     voicing beside his moment; he picks which sounds like what he meant.
  2. **Same-note mirrors:** truth is a convention. Write the house convention into the lexicon (Dilemmadata's lesson),
     and score both names as accepted, CASD-style.
  3. **Function disputes that depend on what comes next:** context decides (this is exactly what C3 is for). Score
     against a blind double annotation by two seats (the house N-version rule). Daniel only breaks ties by ear.
- **Split the card.**
  - C2 scoring and C5 textured streams need no Daniel time and can start now.
  - Only the A/B session needs him.
- **Arithmetic.** Q2 asks for 20 minutes and about 100 windows, but the receipt needs at least 150 windows (about 30
  minutes). Make them agree.

### #4 Voicing shape label (down to #10)
- **Half already exists.** theory-nextgen `Reading.tags` already names upper structure, polychord, quartal and cluster
  (spec line 139), and `rootless` is an omit flag. New: shell, rootless A/B, open 10th, spread, drop 2.
- **Wrong dependency.** "Open 10th (left hand)" and "drop 2" need the hand split and a rule for pedal-carried notes
  (held keys or everything ringing?). That means #2's or live-sheet T5's split, not just TN1.
- **Prior art.** Supported only by Chord ai's App Store listing.
- **Ear-player check.** "Drop 2" and "rootless A/B" are arranging jargon. Plain words first, name second (pedagogy
  rule, `design-pedagogy.md` line 394), and always with a Hear button.

### #5 Cheap accuracy trio (stays #5)
- **Claim halved.** Cite +1.0 WCSR from Korzeniowski, not "about 2".
- **Change the Daniel-facing line in section 0.4** from "the cheapest gain" to "the cheapest thing to try", and report
  it only after the gold-set receipt.
- **Still well aimed.** Context re-rank is the one tool that can separate same-note mirrors (design-engine line 276:
  the gospel 5 over 4 case).

### #6 The band follows my chords (down to #8)
- **Missed prior art.**
  - **Arranger keyboards.** Yamaha's AI Full Keyboard detects chords from both hands in free play, and changes with
    fewer than three notes (verified).
  - **Chord-following plugins.** UJAM Virtual Bassist follows chords you play and shows the chord it read. About
    129 USD/EUR, 30-day trial (medium).
- **Try before build.** The core wish is testable without an L build: a trial of a chord-following bass plugin in FL,
  fed by the KeyLab.
  - That is a download and a trial account, so it needs **Daniel's OK**.
  - It shows whether "band follows" feels good under his rubato and pedal.
  - Our real differentiator is the pedal-aware reader (#5), which those plugins lack.
- **Borrow arranger behaviours:** start on his first chord, variations and fills on KeyLab pads, keep the chord when
  hands lift.
- **Missing REC guard.** The card doesn't state that the band's sound stays out of the take (jam Q1 default). Add it.

### #7 Offline re-render with hindsight (stays #9, merged)
- **Not new.**
  - `live-sheet-music` Path B (rendering-formats lines 403-409) already plans the full-take replay re-render through
    `replay.js` and `recorder.js`.
  - Spectacle `design-loot-feel.md` line 260 lists it too.
  - Merge into one render wave with one owner. The hindsight analysis layer is the real delta. Effort drops.
- **Dropped steal.** The camera composite (SeeMusic, verified) is the standard TikTok format for pianists. Add it as an
  option, not live.
- **Tidy pass: honesty.** A posted video whose notes were edited isn't the take. Default off; when used, the caption
  must not call it a live take.

### #8 Run routines (up to #6)
- **Drop the gate.** iReal Pro's ramp is unconditional per repeat; only Melodics gates. Over an improvised card, a
  "clean pass" gate is a hidden grade (P9), and "clean" is ill-defined for an ear player who colours chords.
- **Default:** a plain +N BPM per pass, with an optional gate. This removes the J4 riff dependency. Effort S.

### #9 Pedal depth logging, then fog (9a up to #7; 9b render-only)
- **(a)** Already decided by `piano-ideas-2026-09-13/panel-synthesis.md` item 9 (log raw CC64; half-pedal visuals only
  after proof). Cite it as that decision's build, not a new idea. It is small, and every pedal receipt waits on its
  data, so it moves up.
- **(b)** Fog on the live glass is a mud meter, conflicting with:
  - P10;
  - theory-nextgen section 5, which cut tension steps because they read as a meter, and anything that moves while a
    chord holds (spec lines 383, 400).

  Make fog render and Study only.

### #10 Moment to FL (up to #3)
- **FL's native capture loses the pedal.**
  - Image-Line's manual describes a note logger with a three-minute buffer.
  - A user report on Image-Line's forum says dumps lose CC64.
  - A secondary tutorial claims a longer buffer in newer versions (conflict, unverified).
  - Either way, a pedalled improvisation dumped from FL comes out dry. Our `.mid` with CC64 fixes the part that
    matters for his style.
- **Free second opinion, live.** The Chord Panel names chords from live MIDI (max 10 notes), so the comparison works
  tonight without the verb. `moment --mid` is still useful for past moments.
- **Three writers planned.** An in-house MIDI writer is decided in `live-sheet-music` (rendering-formats D7), planned in
  jam C22 (`arsenal/jam/smf.py`), and needed by fl-jam-bridge Option A. Name one owner before #10 starts.
- **Unverified.** Whether FL imports MIDI marker text as markers. The card promises names as markers; verify on import
  before promising it.

### #11 The note that moved (down to #14)
- **P, L and R** are neo-Riemannian moves between major and minor triads. Daniel's chord time is dominated by
  extended and sus chords (theory-nextgen's measured vocabulary), so the words would rarely fire truthfully. Drop them;
  keep "held, moved, by how much".
- **Live arcs** at about 49 commits a minute hit the same problem that deferred the voice-leading ghost column (spec
  line 402). Render and riff only.

### #12 Call it (stays #11)
- **Same flaw as #3.** Let his own words count ("my bright 4"), not only a pick from theory names. "Your name" is the
  ear player's path to the theory name.

### #14 Progression family (stays #13)
- **Partial duplicate.** jam-spec seed cards already carry named progressions ("lament bass", "lush 2-5-1"). Reuse
  their names in `progressions.json`.
- **Licences.** When in Rome is CC BY-SA, not CC BY (section 1.3).
- **Missed competitor.** Mapping Tonal Harmony Pro, a harmony-map app. Live MIDI input is not stated on its page.

### #15 End-of-night poster (stays #15)
- "Needs an OK from: nobody" is wrong for a 9:16 TikTok end card. It publishes his keys, kept sounds and a heat map.
  Generating is fine; **each poster needs Daniel's OK before it leaves the machine** (practice data private).
- It is content, not practice. Fine at #15.

---

## 3. House-rule conflicts

| Rule | Where the plan bends it | Fix |
|---|---|---|
| No recording Claude into takes by default | #6 has no REC guard; #1 treats his own loop as Claude's and leaves it undecided | #6: say the band stays out of the take. #1: ask Daniel about his own loop; mention the Focusrite Loopback leak. |
| Recordings stay clean | #7 tidy pass edits notes on a posted video; #9b fog and #11 arcs live on glass | Tidy off by default, never captioned as live; fog and arcs render-only |
| Practice data private | #15 poster designed for posting; #7 hindsight renders post analysis | Per-item OK before anything leaves the machine |
| Downloads need Daniel's OK | #6's natural trial step (plugin trial) | List it as a question with a default, not an action |
| P9, no scores | #8 "clean pass" gate; #9b fog meter live | Ungated ramp by default; fog in Study and render only |

---

## 4. Gimmicks for an ear player

- **P/L/R Tonnetz names (#11).** Academic, triad-only; the moved-note count is the useful part.
- **Voicing jargon as a live label (#4).** "Drop 2", "rootless B". Fine in Study with Hear buttons, not as a headline.
- **Live pedal fog (#9b).** A mud meter while he plays. On a re-render it is lovely.
- **Poster (#15).** Content, not practice. Keep it last.
- **Gated speed (#8).** Turns a jam card into a test.
- **Not gimmicks** despite looking like it: Find it (#13) is how ear players already learn, and Loop me (#1) is the
  most ear-native feature in the plan.

---

## 5. Duplicates with specs the plan didn't check

| Plan item | Already in | What to do |
|---|---|---|
| #7 re-render | `live-sheet-music-2026-09-14/rendering-formats.md` Path B and D5; spectacle `design-loot-feel.md` line 260 | Merge; one render owner |
| #2 hand split, roll rule, pedal lag; #6 pulse gate; #7 phrase boundaries | `live-sheet-music/transcription.md` T1, T5, T6 (measured roll and pedal-lag tables); `tempo-meter.md` (beat tracking, phrases, tidy pass TM4) | One definition per concept, reused by chord names, score and touch facts |
| #10 SMF writer | live-sheet-music D7; jam C22 `smf.py`; `fl-jam-bridge-plan.md` Option A | One writer, one owner |
| #9a pedal curve | `piano-ideas-2026-09-13/panel-synthesis.md` item 9 | Cite as that decision's build |
| #4 shapes | theory-nextgen `Reading.tags` (line 139) | Add only the missing shapes |
| #14 names | jam-spec seed cards | Reuse the names |

The plan's "Checked against" row lists five folders; `live-sheet-music-2026-09-14`, `fl-jam-bridge-2026-09-14` and
`piano-ideas-2026-09-13` are missing from it.

---

## 6. What is missing

### 6.1 Competitors skipped

- **Ableton Capture MIDI** is the closest shipping version of Loop me: retroactive capture, tempo and loop boundaries
  from the phrase, instant overdub.
- **FL Studio's own tools**, in his DAW:
  - the MIDI or score logger;
  - the Audio Logger (the last 60 seconds of the master);
  - the live Chord Panel (2026).

  They set the bar that #1 and #10 must beat, and give tonight's free tests.
- **Arranger keyboards** (Yamaha AI Full Keyboard; Korg and Roland equivalents not checked) are the original "band
  follows your chords".
- **Chord-following instrument plugins.** UJAM Virtual Bassist (medium). NI Session players were not checked. They
  would run inside FL.
- **MIDI practice analysers.** PianoTrace/TempoPro (pedal, dynamics, articulation; Apple only). The Ultimate Piano
  (velocity spread per note, medium).
- **Midiano**, a free browser app with Web MIDI, falling notes plus sheet music, play-along wait mode and offline PWA.
  It is our nearest tech-stack cousin. Medium.
- **Mapping Tonal Harmony Pro**, a harmony-map display to compare with the key ring and function words.

### 6.2 Modalities not searched

1. **Jamming with people.** "Jamming" usually means other humans: a friend on a second keyboard in the room, or online.
   The plan only searched machine partners.
   - Online: Jamulus (GPL per project; the GitHub API shows no SPDX id) and SonoBus (GPL-3.0, verified).
   - Idea: two players' chords on one page, each in their own colour. Not researched.
2. **Voice.** Sing or hum the next note before playing it (the classic ear-training habit), or hum a line and see
   chords under it. Not researched.
3. **Camera.** Hands footage composited with the render is the standard pianist TikTok format. It was in
   `products.md` (SeeMusic) and dropped from the plan.
4. **Touch beyond velocity.**
   - The KeyLab 88 mk3 sends channel aftertouch (Arturia).
   - Key-release timing is already in the log.
   - Legato overlap between successive notes, and key release versus pedal release, are articulation facts PercePiano
     names that #2 ignores.
5. **Pads and drums.** KeyLab pads for fills, variations or finger drumming in the jam. This ties to #6's arranger
   behaviours.

---

## 7. Lane-file errors that don't change the ranking

- `open-source.md` 2.1: When in Rome licence (CC BY-SA, not CC BY); AugmentedNet described without its texturing.
- `chord-accuracy.md` 1.6: POP909-CL "+15 points from corrections" misreads the paper.
- `products.md` 2.4: ROLI dimensions cited to the wrong page; 2.2: Band-in-a-Box take-over unverified.
- `ultimate-practice-plan.md` #1: Soundslice snapping cited to the wrong post; section 4: `setSustain` line numbers
  stale.
- `products.md` 4.5 and plan section 4: CASD's own NC licence goes unmentioned.

## 8. Not verified tonight

- FL score-logger buffer length (manual three minutes; a tutorial says longer), and whether CC64 is really dropped
  (one forum report).
- Whether FL imports MIDI marker text from a `.mid` as markers.
- UJAM prices (from KVR and store summaries). Whether NI Session instruments follow live chords.
- The Band-in-a-Box take-over feature.
- Faster-than-realtime 4K on SeeMusic.
- Whether any practice analyser measures pedal against chord changes specifically. The search found none; that is
  absence, not proof.
- None of the local log aggregates (block share, top-voice rates, carried rubs). This pass didn't open practice logs.

---

## 9. Sources

Research:
- Koops et al., JNMR 2019 (abstract): https://api.semanticscholar.org/graph/v1/paper/DOI:10.1080/09298215.2019.1613436 ; CASD repo (licence): https://github.com/chordify/CASD
- Korzeniowski & Widmer, ISMIR 2018, Table 3: https://archives.ismir.net/ismir2018/paper/000300.pdf ; frame-level LMs: https://arxiv.org/abs/1702.00178
- BACHI: https://arxiv.org/html/2510.06528 ; code: https://github.com/AndyWeasley2004/BACHI_Chord_Recognition ; POP909-CL: https://github.com/AndyWeasley2004/POP909-CL-Dataset
- AugmentedNet, ISMIR 2021: https://archives.ismir.net/ismir2021/paper/000050.pdf
- Goebl 2001: https://pubmed.ncbi.nlm.nih.gov/11508980/
- Liang pedalling dataset: https://zenodo.org/records/3242149
- PercePiano: https://github.com/JonghoKimSNU/PercePiano ; Profy: https://arxiv.org/abs/2606.10627
- ReaLJam: https://arxiv.org/html/2502.21267 ; Aria-Duet: https://arxiv.org/html/2511.01663

Products:
- Ableton Capture MIDI: https://www.ableton.com/en/live-manual/12/recording-new-clips/
- FL Studio 2026 release notes: https://forum.image-line.com/viewtopic.php?t=341294 ; What's new: https://www.image-line.com/fl-studio/release/2026 ; recording and score logger manual: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/recording_scores.htm ; CC64 missing from dump (forum): https://forum.image-line.com/viewtopic.php?t=281832 ; longer buffer claim (tutorial): https://flstudiomusic.com/how-to-recover-midi-performances-in-fl-studio-using-score-logger/
- Yamaha Full Keyboard / AI Full Keyboard: https://hub.yamaha.com/controlling-styles-with-both-hands-using-full-keyboard-mode/
- UJAM Virtual Bassist: https://support.ujam.com/hc/en-us/articles/360019063979-Virtual-Bassist-Series-Walkthrough ; https://www.ujam.com/blog/ujam-releases-virtual-bassist-2/
- Studio One Follow Chords: https://www.audeobox.com/learn/studio-one/chord-track-guide/ ; https://www.soundonsound.com/techniques/studio-one-chord-track-nashville-numbering
- Logic Session Players: https://support.apple.com/guide/logicpro/chords-and-session-players-lgcp70dd5af3/mac ; https://www.soundonsound.com/techniques/logic-pro-session-players ; Chord ID: https://cdm.link/logic-pro-12-hands-on/
- Band-in-a-Box: https://www.pgmusic.com/bbwin.htm ; https://www.pgmusic.com/bbwin.features.htm
- Scaler 3: https://scalermusic.com/products/scaler-3/ ; Scaler Detector: https://www.kvraudio.com/news/scaler-music-releases-scaler-detector-key-and-chord-detection-plugin-65088
- iReal Pro practice: https://www.irealpro.com/learn/advanced-practicing-techniques/ ; Melodics: https://support.melodics.com/en/articles/6777027-practice-mode
- Soundslice looping help: https://www.soundslice.com/help/en/player/basic/4/looping/
- Chord ai: https://chordai.net/ ; https://apps.apple.com/us/app/chord-ai-play-any-song/id1446177109
- ROLI: https://roli.com/us/product/airwave-learn ; https://roli.com/blog/ai-music-coach-in-the-roli-learn-app ; https://musictech.com/news/gear/roli-ai-music-coach-airwave-first-look/
- SeeMusic: https://www.seemusicapp.com/ ; LumaKeys: https://lumakeys.app/
- Arturia KeyLab 88 mk3: https://www.arturia.com/products/hybrid-synths/keylab-88-mk3/overview ; manual: https://dl.arturia.net/products/keylab-88-mk3/manual/keylab-88-mk3_Manual_1_0_0_EN.pdf
- PianoTrace / TempoPro: https://tempopro.lishiyu.net/en/midi-piano-practice-app/ ; The Ultimate Piano: https://the-ultimate-piano.com/best-piano-practice-app/
- Midiano: https://midiano.com/ ; https://github.com/Bewelge/MIDIano
- Mapping Tonal Harmony Pro: https://mdecks.com/mapharmony.phtml
- Neothesia releases: https://github.com/PolyMeilex/Neothesia/releases

Licences:
- When in Rome README: https://github.com/MarkGotham/When-in-Rome
- Chordonomicon card: https://huggingface.co/datasets/ailsntua/Chordonomicon
- GitHub API `repos/<owner>/<repo>` for: Neothesia, Impro-Visor, JJazzLab, essentia.js, meyda, matchmaker, accompanion, MIDIVisualizer, tonnetz-viz, realchords-pytorch, PercePiano, PM2S, AugmentedNet, idyom, Somax2, POP909-Dataset, functional-harmony, jamulus, sonobus

Local (read only):
- `arsenal/REPLAY.md`
- `arsenal/web/piano/recorder.js`
- `arsenal/web/piano.js` (`setSustain`)
- `research/in-flight/piano-theory-nextgen-2026-09-14/theory-nextgen-spec.md` (lines 139, 383, 400, 402), `design-engine.md` (lines 276, 336), `design-pedagogy.md` (lines 198-199, 394)
- `research/in-flight/piano-jam-2026-09-14/jam-spec.md` (C14, C22, section 15 Q1)
- `research/in-flight/live-sheet-music-2026-09-14/` (`rendering-formats.md`, `transcription.md`, `tempo-meter.md`)
- `research/in-flight/fl-jam-bridge-2026-09-14/fl-jam-bridge-plan.md`
- `research/in-flight/piano-ideas-2026-09-13/panel-synthesis.md` (item 9)
- `research/in-flight/piano-spectacle-2026-09-13/design-loot-feel.md` (line 260)
