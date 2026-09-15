# Commercial practice, jamming and theory tools: what to adapt

- **Date:** 2026-09-14
- **Lane:** products (commercial and popular tools). Research only: no code, servers, browsers, downloads or logins.
- **Question (Daniel, Discord):** how to make the piano the ultimate practice and jamming tool. Which similar
  projects have features worth taking? How can chord accuracy improve? What other detections or analysis would be
  cool to show?
- **Method:** web search and fetch, 2025-2026 sources, about 45 queries. Every claim links its source in section 9.
  Descriptions are my own summaries, and quotes are at most a short phrase.
- **Not re-proposed:** anything already in `jam-spec.md`, `suggest-lights-plan.md`, `practice-along-plan.md`,
  `theory-nextgen-spec.md` or `spectacle-spec.md`. I checked headings, section 0 and section 2 of each, plus a
  keyword sweep. Where a product only confirms a planned feature, the backlog (section 6) marks it **confirms** so it
  is not counted as new.
- **Honesty flags:**
  - Hooktheory, Plugin Boutique and the iReal Pro news page returned HTTP 403 to the fetcher. Details for those come
    from search snippets and reviews.
  - Prices are as the cited pages reported them. Aggregators (Subger and similar) are marked *(aggregator)*.
    "Not checked" means I did not verify a price this pass.
  - No vendor publishes chord-recognition accuracy numbers, so accuracy comparisons with our namer are not possible.

---

## 0. In one screen

**The house rule these products run into.** Pedagogy P9 (`design-pedagogy.md` 198) and Sunshine's house ideas
already rule out streaks, grades, percentages and red error states for Daniel. Almost every learning app's
stickiness is built from exactly those. So this lane takes the **feedback loops** (hear it, try it, get told
something true, try again slightly harder) and leaves the **scores**. Section 3 sorts every mechanic into adopt,
adapt or refuse.

**The ten best steals, ranked by value to an ear player who jams and makes videos:**

| # | Steal | Seen in | Lands in |
|---|---|---|---|
| 1 | **Loop me.** Play 2-8 bars; they loop, exactly as played, under the bar clock, and he plays over himself. | Scaler 3 (record + multi-bind loops), Ableton capture, hardware loopers | jam transport + practice log (`Hear me` on repeat) |
| 2 | **The band follows his chords.** Bass (and later pads) take the chord he is holding, landing on the next beat. | Logic Session and Synth Players following the Chord Track; Studio One Follow Chords (Narrow, Parallel, Bass) | `groove.js` + `band` voicer, fed by the committed reading |
| 3 | **Around the keys.** A card or loop moves to a new key each pass (up a 4th, down a half step, or through his keys). | iReal Pro key cycling | jam run option (key already changes at the top of a pass) |
| 4 | **Speed that is earned.** Try starts slow and adds a few BPM after each clean pass, up to the card's tempo. | Melodics Auto BPM (+10 when performing well), Soundslice speed training, iReal Pro auto tempo increase | jam run option; "clean" judged by the riff alignment |
| 5 | **Songs that use this progression.** When his loop matches a well-known progression, name it and a few songs built on it. Strong TikTok material. | Hooktheory Trends and TheoryTab | new offline table + a caption source; licensing check first (7.1) |
| 6 | **Voicing shape label.** A second line saying *how* the chord is voiced: shell, rootless, quartal stack, open 10ths, cluster on top. | Chord ai (claims voicing and position recognition) | theory-nextgen reader output → HUD, then the Lesson view |
| 7 | **Melody-on-top balance.** Is the top voice of his chords louder than the inner voices? A real pianist skill, readable from velocity. | ROLI AI Music Coach's "dynamic" feedback dimension (camera-based there; ours is MIDI-only) | `practice riff` fact + a Study-view readout |
| 8 | **Moment to FL.** Any log moment becomes a `.mid` file for FL Studio, and FL 2026's own Chord Panel re-detects it: a free second opinion on our names. | Scaler and Captain drag-to-DAW MIDI; FL Studio 2026 Chord Panel detection | `py -m arsenal.practice moment --mid` (new flag) |
| 9 | **Offline 4K re-render from the log.** Replay a take from the practice log at a fixed timestep into a perfect-frame video, instead of capturing live. | SeeMusic (4K renders, faster than realtime on modern hardware), LumaKeys 4K export | spectacle recording plan; check against `spectacle-spec.md` 3.4 |
| 10 | **KeyLab mk3 Chord mode as a jam partner, zero code.** Capture his Gbmaj13#11 and play it from one key with the left hand while the right hand solos. | Arturia KeyLab mk3 Chord, Scale and Arp modes (hardware he owns) | a deck card that teaches the setup; log guard (2.5) |

**Chord accuracy, in short (section 4).** Commercial detectors win on three things we can copy:
- vocabulary tiers the user picks (Moises Easy, Medium and Advanced);
- context from the whole song and its beat grid (Logic Chord ID, Yamaha Smart Pianist, Band-in-a-Box Audio Chord
  Wizard);
- easy correction (Chordify, Logic, Scaler).

Our MIDI namer already beats what we can verify of theirs on raw note-reading. The remaining gains are:
- a beat-grid prior while a jam or a song is running;
- a Daniel lexicon that his one-tap corrections write into;
- voicing labels.

**Cool detections (section 5).** Beyond what is already planned, the strongest additions are:
- the progression's famous-song family;
- harmonic rhythm ("one chord per bar", "changes every 2 beats");
- the voicing shape;
- top-voice balance;
- pedal-change timing against chord changes (legato pedalling);
- roll versus block onset spread.

No product surveyed does the last two from MIDI. That is our opening.

---

## 1. What already exists or is planned (so nothing below re-proposes it)

| Capability | Where |
|---|---|
| Pedal- and arpeggio-aware chord name, Nashville numbers from a steady key tracker, grand staff, practice log, moonlight keys, ghosts, glass layer | live: `arsenal/web/piano.js` (`detect` at line 160, `logChord` 1899, `midiRank`/`bindMidi` 2607-2657) |
| Offline analysis verbs `sessions`, `all`, `brief`, `borrowed`, `colors`, `moment`, `windows`, `harmony`, `analyze`, `list`, `riff` | live: `arsenal/practice.py` (+ `practice_riff.py`) |
| Loop parsing, key estimate, bass lanes, swing, humanise | live: `arsenal/band.py`, FL band in `arsenal/fl/` |
| Cards, deck, Play/Show/Loop/Try/Hear me, bar clock, grooves `hold`/`ballad`/`pulse`, backings `full`/`comp`/`bass`, courtesy gate, riff reports, Keep | jam-spec v1 |
| Tempo ramps, call and response, "wait for me" Try, `.mid` export card action, FL as clock, MIDI out, glass marks on his notes (in chord / colour / rub), follow-me tempo | jam-spec v2 |
| Next-chord chips (theory, his habits, growth edge), near voicing, key-light LED strip via WLED | suggest-lights plan |
| Now Playing via SMTC, song key and BPM from loopback audio, follow key and tempo, count-in on the song's beat | practice-along plan |
| Chord grammar reader (`maj13#11`, altered dominants, rootless, quartal, polychord), `ALSO` line, harmonic windows, 28 scales, function captions, key ring, Lesson view | theory-nextgen spec |
| Rarity tiers, stage effects, reveal in the rest, adaptive resolution, recording pipeline | spectacle spec |

---

## 2. The survey

Each block gives what stands out, why people keep coming back, the price model, and **Take** (what fits our stack,
concretely). **Take: none** means nothing for us.

### 2.1 Harmony brains (songwriting and theory tools)

#### Hooktheory Hookpad + Trends + TheoryTab
- **Stands out:**
  - A chord palette organised by scale degree, with borrowed chords and modes a click away.
  - A melody guide that colours melody notes as consonant or dissonant against the current chord.
  - Next-chord suggestions ranked by popularity across a database of tens of thousands of songs.
  - Trends: click a chord and see what songs usually do next, plus the list of songs that share the progression.
  - Aria, a generative add-on, suggests chords and melodies.
- **Data access:** a public Trends API returns nodes with a chord id, a probability and a `child_path`. You append
  the path to walk a progression; for example, after IV the I chord has probability 0.324 in their example.
  Access needs a Hooktheory account and a bearer token.
- **Why it sticks:** the "what comes next" question is always one click away, and the answer is social proof ("this
  is what songs do").
- **Price:** free tier. Sources disagree on paid plans: $7.99/mo or $199 lifetime per one 2026 aggregator, and
  $4.99/mo, $49/yr or a one-time purchase per another. Aria is $14.99/mo on top.
- **Take:**
  - (a) **"Songs with this progression"** (steal 5). A small offline table of well-known progressions in Nashville
    numbers (1-5-6-4, 6-4-1-5, 1-6-4-5, 2-5-1, 4-5-3-6, 1-b7-4 …), each with a plain name and a few famous songs.
    `harmony.js` already produces the numbers, so matching a committed loop of 3-4 windows is cheap. Showing it as a
    Nashville-row caption on a sure match makes a clip-worthy moment.
  - (b) A **"what most songs do"** source for suggestion chips, beside theory, habits and growth edge. Only from a
    table we are allowed to hold (7.1).
  - (c) The **melody guide** confirms jam v2 glass marks. Nothing new.

#### Scaler 3 (Scaler Music / Plugin Boutique) + Scaler Detector
- **Stands out:**
  - A standalone app as well as a plugin, redesigned as Browse, Create and Arrange pages.
  - Detects chords, keys and scales from MIDI **and audio**, then offers compatible chords.
  - A context-aware next-chord engine and a dynamic circle of fifths.
  - Motions turn chords into basslines, arpeggios and performance phrases.
  - Bind to Keyboard gives one-finger chords. Keys Lock keeps playing in scale.
  - Multi-Bind loops several lanes at once for live jamming.
  - Records chord triggers and Keys Lock performances as editable MIDI.
  - Hosts third-party instruments and exports MIDI by drag and drop.
- **Scaler Detector** (Oct 2025) is a separate plugin, $9 or free with Scaler 3. It lists matching scales **ranked by
  goodness of fit**, and any detected chord can be clicked to play or assigned to a key.
- **Reviewer caveats:** the interface is busier than v2, and there is no hardware MIDI out.
- **Why it sticks:** it never leaves you stuck. There is always a next chord, a phrase, or a way to play it with one
  finger.
- **Price:** $99 one-time ($70 intro); upgrade $39 ($29 intro).
- **Take:**
  - (a) **Loop me** (steal 1). Multi-Bind looping is the closest commercial version of "loop what I just did and
    let me play over it".
  - (b) **Moment to FL** (steal 8). Drag-to-DAW MIDI is table stakes.
  - (c) The ranked scale list confirms theory-nextgen `scales.js`. The one delta is to *show the ranking reason*
    (which of his notes fit or rub) in the HUD.

#### Captain Plugins Epic (Mixed In Key)
- **Stands out:** five linked plugins (Chords, Melody, Deep bass, Beat, Play) that stay harmonically compatible
  because they share one progression. "Pianistic Playing" turns block chords into triads, extensions, arpeggios and
  bass notes. There are humanise controls (space, strum, swing), MIDI import, and song tabs.
- **Why it sticks:** a whole band from one chord line.
- **Price:** $99 one-time; upgrade $39.
- **Take:** confirms that the jam backing should share one chord source across bass, comp and pad. That is already
  the jam design. The "pianistic" arrangement idea supports the v2 `arp` and `swell` grooves. Nothing new.

#### Steinberg Cubase Chord Assistant (Cubase 14/15)
- **Stands out:**
  - Proximity mode places suggestions on a map. The further a chord sits from the reference chord, the more complex
    it is.
  - Suggestions are coloured green (common) through orange and red (adventurous, or not fitting).
  - Cadence mode builds progressions from cadences.
  - Click to audition, drag to a chord pad.
- **Why it sticks:** it is spatial. You see "safe" and "brave" at a glance.
- **Price:** part of Cubase (not checked).
- **Take:** a **two-axis layout** for suggestion chips: distance equals voice movement, colour equals how common.
  suggest-lights already has reason words, so this is a small UI delta for the Study view, not the play surface.

#### PreSonus Studio One (Chord Track, harmonic editing)
- **Stands out:** Detect Chords from audio events and Extract to Chord Track from MIDI. Tracks set to Follow Chords
  re-pitch to the chord track in three modes:
  - **Narrow:** each note goes to the nearest note of the target chord.
  - **Parallel:** the whole part shifts by the root interval.
  - **Bass:** like Parallel, but the lowest note goes to the target chord's bass.
  - Changing a chord updates every following track.
- **Price:** not checked (product naming may have changed; not verified).
- **Take:** **the three follow rules are exactly the vocabulary steal 2 needs.** A groove pattern written once
  (in `groove.js`) is re-pitched per committed chord by Narrow (pads, comp), Parallel (riffs) or Bass (bass lane).
  `band.py`'s `_nearest_in_range` is already the Narrow primitive for one voice.

#### Apple Logic Pro 11 → 12 (Session Players, Synth Player, Chord ID)
- **Stands out:**
  - Keyboard Player styles (block, broken, arpeggiated, pads) with left and right hands separately switchable,
    playing range, voicing complexity, grace notes, dynamics and humanise.
  - Bass and Keyboard Players follow the global Chord Track, so several players stay in sync.
  - Logic 12 adds Synth Player (bass and chord pads that follow the Chord Track) and **Chord ID**: AI analysis of
    audio or MIDI that writes the progression, including the harmonic rhythm, into the Chord Track.
  - CDM's hands-on found it impressive but imperfect on dense material, and easy to clean up.
  - 12.3 (June 2026) improved detection on solo guitar and piano, inversions, and 7th, maj7 and 6th chords.
- **Why it sticks:** the "band that listens to your chords" loop, with **intensity** and **complexity** as the two
  knobs.
- **Price:** Mac app (not re-checked this pass).
- **Take:**
  - (a) Steal 2, with Logic's two knobs, *complexity* and *intensity*, as the only controls. The jam groove already
    has a seed and humanise, so complexity maps to groove density and intensity to velocity and register.
  - (b) **Harmonic rhythm** as its own detected quantity (section 5).
  - (c) Apple's 12.3 notes show that inversions and 6ths are the industry-wide hard cases. They belong in the
    theory-nextgen corpus as a named stress set.

#### Ableton Live 12 (MIDI Tools, keys and scales) + 12.3
- **Stands out:**
  - Scale awareness runs through clips and devices. With a scale on, pitch parameters work in scale degrees rather
    than semitones.
  - Transformations (Connect, Ornament …) and Generators (Rhythm, Seed, Shape, Stacks, Euclidean). Stacks builds
    chords or progressions from root, inversion and 15 chord types within the scale.
  - 12.3 (Nov 2025) adds **local stem separation** powered by MusicAI (the Moises team) running offline, plus
    bouncing groups.
- **Price:** Suite tier needed for stems (not re-checked).
- **Take:**
  - (a) "Distance in scale degrees" confirms our Nashville-first approach.
  - (b) Offline stem separation is now a mainstream DAW feature. For practice-along it means "mute the song's
    piano and play the part yourself" is a realistic later option, with the model download needing Daniel's OK
    (7.3).

#### Image-Line FL Studio 2025 → 2026 (Daniel's DAW)
- **Stands out:**
  - The Chord Progression Tool has a bassline generator.
  - Chord Stamp works top-down (the clicked melody note gets a chord under it) or bottom-up, with voice-leading.
  - The Chord Panel **detects notes and chords in the piano roll**.
  - Loop Starter, Text to Chord Progression, and Gopher, an assistant that in 2026 can change the project.
  - Rebuilt FLEX and cloud backup.
- **Price:** Daniel owns it.
- **Take:**
  - (a) **Moment to FL** (steal 8). FL's own detector re-reading our `.mid` is a free, independent oracle for our
    names. Run a manual spot check with Daniel present, never automated.
  - (b) Top-down Chord Stamp is the "harmonise my melody note" idea. For the page it is a suggestion variant: he
    holds a right-hand top note, and the chips offer chords *under* it. That is new relative to suggest-lights,
    which starts from the held chord.

#### Songtive Piano Companion
- **Stands out:** a chord and scale dictionary with reverse lookup from a MIDI keyboard. It shows intervals, degrees,
  fingering and the other chords in the key, and has a progression builder. Recent additions are chord flashcards
  with spaced repetition, daily goals and streaks.
- **Price:** freemium plus PRO (not checked).
- **Take:** spaced-repetition review of *his own kept chords* is interesting (section 3, adapt). Reverse lookup is
  what we already do.

### 2.2 Backing bands and accompanists

#### iReal Pro
- **Stands out:**
  - A lead sheet that is also a band. There are 50 styles (plus 40 as purchases), with selectable instruments
    (piano, Rhodes, guitars, drums, vibes).
  - Thousands of free community charts and a chart editor.
  - Tempo change, section looping, transposition, **automatic tempo increase** and **key cycling** for focused
    practice.
  - Piano, guitar and ukulele chord diagrams and scale suggestions for improvising.
  - Export to PDF, MusicXML, audio or MIDI.
- **Why it sticks:** it is the practice routine jazz players already have ("12 keys, 5 BPM faster each chorus"),
  built in.
- **Price:** one-time per platform, e.g. $21.99 on Android.
- **Take:** steals 3 and 4. Both are small additions to a jam run: a run field `cycle: {interval: 5|-1|"his",
  every: "pass"}` and `speed: {start: 0.7, step_bpm: 4, gate: "clean"}`. The key change already lands at the top of
  a pass (jam-spec C3), so key cycling reuses that path.

#### Band-in-a-Box 2026 (PG Music)
- **Stands out:**
  - Type chords and a band plays them. RealTracks are recorded studio musicians (222 new in 2026).
  - An intelligent Soloist generates solos.
  - The **Audio Chord Wizard** extracts chords, tempo, bar lines, key and tuning from an audio file.
  - Practice features: take over the piano part while it plays bass and drums; on-screen notation.
- **Why it sticks:** a real-sounding band in any style, from a chord chart.
- **Price:** Pro from $99; large content packs cost more.
- **Take:**
  - (a) The **Soloist** is the call-and-response direction jam v2 already names. It confirms the idea; there is no
    new mechanic.
  - (b) **"Take over the piano part"** means the backing drops its comp and keeps bass and drums the moment he
    plays chords. Jam already ducks; the delta is **auto-drop the comp lane while he is comping**, keeping bass and
    drums. That is a cheap and musical rule.
  - (c) The Audio Chord Wizard confirms that the practice-along v2 "read the song's chords" should be offline,
    whole-song and bar-lined (section 4).

#### Jamzone
- **Stands out:** a very large catalogue of studio-recorded backing tracks with separate stems. You can mute
  instruments, change pitch and tempo, loop sections, see scrolling chord charts synced to the audio, and simplify
  chords to your level.
- **Price:** subscription (not checked).
- **Take:** "chords adapted to your skill level" is the vocabulary-tier idea (section 4). Nothing else.

#### Metronaut (Antescofo) and MyPianist
- **Stands out:** accompaniment that **follows the player's tempo** in real time over a known score, so expressive
  rubato works. The cursor waits for the right note.
- **Price:** subscriptions (not checked).
- **Take:** jam-spec v2 "follow me" only takes the loop tempo from his first bars. Score-following shows the next
  step: **continuous tempo follow** inside a run, meaning the bar clock re-estimates from his onsets each bar with
  a clamp. That needs the v2 rhythm calibration first. Park until after the J-waves; note it as the only
  accompanist mechanic we don't have.

#### Google DeepMind Lyria RealTime (API) and Magenta RealTime (open weights)
- **Stands out:** "live music models" (arXiv 2508.04651, Aug-Nov 2025). Continuous streaming generation, steered live
  by text or audio prompts. Lyria RealTime is an API (it powers MusicFX DJ); Magenta RT has open weights.
- **Take:** none now. It is an audio texture bed you steer with words, not a harmony-aware band: it does not know
  Daniel's chords from MIDI. A download or API key would need Daniel's approval anyway. Worth one experiment later
  as an **ambient pad bed prompted by the detected key and mood**, never as the jam band.

### 2.3 Song-audio tools (practising along with recordings)

#### Moises (MusicAI)
- **Stands out:**
  - Stem separation (vocals, drums, bass free; finer splits paid).
  - **Chord detection in three levels, Easy, Medium and Advanced**, synced to bars and beats.
  - AI key detection with one-tap transposition of the chords to all 12 keys.
  - A Smart Metronome click that follows the song even after speed changes.
  - Count-in of up to 16 clicks, section looping, a speed changer, lyrics, and shared setlists.
  - It runs on phone, web and desktop, and now powers Ableton's stems.
- **Price:** Free (5 uploads/mo), Premium about $3.99/mo, Pro about $9.99/mo *(2026 review)*.
- **Take:**
  - (a) **Vocabulary tiers** (section 4.1).
  - (b) Smart Metronome confirms the practice-along beat-synced count-in.
  - (c) Setlists: skip.

#### Chordify
- **Stands out:** chords for any song from a deep network. The Toolkit adds **live chord detection that checks you
  are playing the right chords**, a chord trainer, and advanced chords (7ths, sus4).
- **Price:** Premium + Toolkit from about $2.25/mo *(vendor page snippet)*.
- **Take:** "check you played the chord" confirms Try's `found` ghost state. It also shows that simple chord charts
  sell: **advanced chords are the paid tier**. That supports showing Daniel's richer names as the default and simpler
  names as a tier.

#### Chord ai
- **Stands out:** real-time chord recognition from the microphone, with beats, BPM, key and lyrics. The pro tier
  covers half-diminished, dim7, 6/9/11/13 and jazz chords. It claims **slash chords and voicing and position
  recognition**, "the first app" to do so by its own account.
- **Price:** freemium plus pro (not checked).
- **Take:** steal 6, the **voicing shape label**. We have the exact notes from MIDI, so we can do it honestly and
  more precisely than any audio app.

#### Capo (SuperMegaUltraGroovy)
- **Stands out:** slow down to 25% without pitch change, named loop regions (Verse, Chorus), and chord detection
  that now covers inversions (v4.5, June 2025).
- **Price:** not checked.
- **Take:** named loop regions become **named moments** in the practice log ("the Db opening"). jam-spec
  `template save-from-moment` is close; the delta is a *name on the moment itself* for `practice moment`.

#### Yamaha Smart Pianist (Audio to Chord / Audio to Score)
- **Stands out:** analyses songs in your music library into chord charts, with tempo, key and **song sections**
  (verse, chorus). On Clavinova CSP and CVP-800/900 it makes a piano accompaniment score and streams the key lights.
  Yamaha says complex or loosely defined harmony gives weaker charts.
- **Price:** free app; the good parts need Yamaha hardware.
- **Take:** Yamaha's candour ("harmonically complex songs work less well") is the model for our confidence words.
  Section detection feeds a practice-along v2 "loop the chorus".

#### Klangio Piano2Notes / Transcription Studio
- **Stands out:** audio to MIDI, MusicXML and sheet music, including isolating the piano inside a band recording.
  Reviewers say it is good on clean audio and needs fixes on dense material.
- **Take:** for the practice log, none; we already have MIDI. For content, "turn a song's piano into falling notes"
  is what LumaKeys also does. Skip unless Daniel wants covers from audio.

#### Songsterr and Soundslice
- **Songsterr:** tab and notation that scrolls in sync with the playhead, speed control, loops, solo and mute,
  pitch shift, sync with the original audio, and AI transcription. Plus costs $9.90/mo.
- **Soundslice:**
  - Notation synced to video or audio; click a note to jump there.
  - Drag across notes to make a loop that **snaps to the nearest note, rest or barline**.
  - Improved slowdown and **speed training** that raises the speed each pass.
- **Take:** loop snapping becomes a rule for Loop me (steal 1): a captured loop's ends snap to the nearest bar line
  of the detected tempo, or to the nearest gesture boundary when there is no tempo. Speed training confirms steal 4.

### 2.4 Learning apps and their game loops

#### Melodics (keys, pads, drums)
- **Stands out:** short lessons (10-15 minutes a day by design) and exercises for muscle memory. Practice Mode has a
  BPM slider, loops, **Wait Mode**, and **Auto BPM** (+10 BPM when you perform well, up to the track tempo).
  Stars, streaks and challenges; difficulty kept in a flow band.
- **Price:** Standard $99.99/yr, Premium $149.88/yr *(retailer/aggregator)*.
- **Take:** Auto BPM (steal 4). Stars and streaks: refuse (P9).

#### Yousician
- **Stands out:** listens for pitch and timing and scores each session in stars. Session goals can be set in stars
  or **minutes**. Streaks count **weeks** played, not days. There are challenges and level-matched competition.
- **Price:** one instrument $19.99/mo or $119.99/yr; Premium+ covers five instruments *(aggregator)*.
- **Take:** counting weeks instead of days, and minutes instead of scores, is the least toxic version of a streak.
  Even that sits under P9; see section 3.

#### Simply Piano (JoyTunes)
- **Stands out:** learn a few bars, then play longer sections **with a backing track and singer**. MIDI or
  microphone input (MIDI is more reliable), three-star rating, 5-minute personalised workouts, weekly streak.
- **Price:** about $119.99/yr *(review sites)*.
- **Take:** "the backing arrives when you're ready" is the Try → Loop ladder we have. Nothing new.

#### Flowkey
- **Stands out:** wait mode, looping a highlighted section, one hand at a time, and real-pianist video of hands.
- **Price:** $19.99/mo, about $10/mo annually, lifetime $329.99.
- **Take:** wait mode confirms jam v2 "wait for me". Nothing new.

#### Skoove
- **Stands out:** AI listens through the microphone; lessons adapt to how you're doing.
- **Price:** $19.99/mo or $149.99/yr.
- **Take:** none beyond confirmation.

#### Playground Sessions
- **Stands out:** green for correct, red for wrong; a 0-100% score split into correct, close and off; tours for
  rookie, intermediate and advanced.
- **Price:** under $20/mo, with a lifetime option.
- **Take:** refuse the red and the percentage. **"Close"** is interesting: a middle class between right and wrong.
  Our riff note classes (colour, rub, passing) are the richer, non-judging version.

#### Piano Marvel
- **Stands out:**
  - Prepare mode (notes only, it waits) and Assess mode (notes and rhythm, micro-assessments every practice).
  - **Slicing** a piece: whole, minced (one hand, short segments) or chopped (short segments one after another).
  - Monthly practice goals and consecutive days.
  - SASR, an adaptive sight-reading test over 90 levels that ends after three pieces under 80%.
- **Price:** not checked.
- **Take:** **slicing for cards.** A long card (the lament bass, the lush 2-5-1) can Try in slices: bar pairs, then
  half, then whole. It is a Try option, not a grade. SASR: skip (he plays by ear).

#### Pianote / Musora
- **Stands out:** the lesson video *is* the practice session. Synced notation and waveform, tempo control, loops,
  hand-separated song breakdowns, a practice tracker with daily streak.
- **Price:** not checked.
- **Take:** **"the video is the practice session."** A deck card could carry a short recorded demo (Daniel's own
  kept take) with loop and tempo. That is jam v2 "Hear pass N" territory; it confirms the idea.

#### ROLI Learn + Piano M + Airwave + AI Music Coach
- **Stands out:**
  - Airwave, a camera stand over the keys, tracks 27 hand joints at 90 fps.
  - Feedback on five dimensions: posture, position, harmony, rhythm and dynamics.
  - Air gestures control sound.
  - The AI Music Coach (beta in Feb 2026, open to all Airwave users by mid-2026) **watches the hands, listens to
    the voice and answers aloud**, adapting pace and focus. MusicTech's hands-on said it works surprisingly well.
  - Lit keys on ROLI keyboards.
- **Price:** Piano M $249; Airwave £299; Learn from about $8.33/mo annual (US) or £13/mo, £70/yr (UK press).
- **Take:**
  - (a) The **five dimensions** are a good checklist for riff facts. We can read three of them from MIDI:
    harmony, rhythm and dynamics. Dynamics gives steal 7.
  - (b) The **spoken coach** is what Claude already is in chat. The steal is *voice in the room*: an optional
    text-to-speech line for one riff fact after a run. Needs a TTS path. Park and ask (Q3).
  - (c) Hand tracking: none (no camera plan).

#### PianoVision (Meta Quest)
- **Stands out:** mixed-reality falling notes over your real keyboard, hand tracking, a learning engine that splits
  songs into sections, timing and accuracy metrics, an AI teacher named "Ludwig", a Plus library of 10,000+ songs,
  and multiplayer.
- **Price:** one-time Basic; the Plus subscription price was not public in the review found.
- **Take:** none now (no headset). The note is that ghost keys over real keys is where XR went, and our glass layer
  is the 2D cousin.

#### ToneGym and EarMaster
- **Stands out:** ToneGym gamifies ear training (intervals, chords, progressions) with leaderboards and "Olympics".
  EarMaster has a deep curriculum with MIDI keyboard or microphone answers.
- **Take:** **play-back ear training from his own log.** The page plays a two-chord move Daniel himself played last
  week; he finds it on the keys, and the answer is his own moment. Sunshine's rule is prediction, never a quiz, so
  there are no points: the "answer" is the moment replaying. EarMaster's "answer on the MIDI keyboard" is the
  mechanic.

#### Modacity, Andante and Tonic (practice journals and social practice)
- **Stands out:**
  - Modacity: lists, timers, notes, recordings, deliberate-practice prompts, a drone, and **every session ends with
    a clear next step**. Annual from $9.17/mo.
  - Andante: a timer, metronome and recorder, session logging with **mood and focus**, and streaks.
  - Tonic (Ray Chen): **live practice studios** where others listen, XP, quests and a community. Free.
- **Take:**
  - (a) A clear next step confirms riff's "one thing to try".
  - (b) **Mood tag on a session** is a one-tap, optional word stored in session meta ("dreamy", "restless"). It
    later lets `practice sessions` say "your dreamy nights live in Db". Cheap and personal.
  - (c) Live studios: park; privacy and courtesy questions.

### 2.5 Hardware (what Daniel owns, and what the light-bar makers do)

#### Arturia KeyLab 88 mk3 (owned)
- **Stands out:**
  - **Chord mode** captures a played chord and re-triggers it transposed from any key, with spread, voicing and
    strum.
  - **Scale mode** forces played notes to a root and scale.
  - The arpeggiator has up, down and a programmable random order and timing.
  - The modes combine, e.g. chord plus scale keeps jazz chords diatonic.
- **Take:** steal 10, as a deck card that teaches the setup. Two guards:
  - (1) Chord and Scale modes change the MIDI that reaches the page, so the practice log records the *generated*
    notes. A session meta note (`controller_mode`) or a HUD warning when the note pattern looks machine-transposed
    keeps `practice` stats honest.
  - (2) The existing MIDI echo guard (`midiRank`/`bindMidi`) is unaffected.

#### Native Instruments Kontrol S MK3 (reference)
- **Stands out:** a multicolour Light Guide over the keys that shows scales, chords, key switches and phrases. Play
  Assist covers scale, harmoniser, chord and arp modes, plus white keys mapped to any scale.
- **Take:** colour semantics for the suggest-lights LED strip: **one hue family per role** (scale member, chord
  tone, suggestion target, key switch). This is a note for suggest-lights phase 4, not new work.

### 2.6 Visualizers and content tools

#### Synthesia
- **Stands out:** falling notes, hands separate, melody practice that waits, finger-number hints, lit-keyboard
  support, any MIDI file.
- **Price:** one-time $8-39.
- **Take:** none new.

#### SeeMusic (Visual Music Design)
- **Stands out:**
  - Live play or MIDI/MusicXML import, turned into 3D falling notes, colour, light, particles and "Saber" effects.
  - **One colour per pitch class.**
  - **Align your own camera footage** with the visualisation.
  - A built-in MIDI editor to tidy a performance.
  - **4K render, faster than realtime** on modern hardware.
- **Price:** subscription; a 2023 report says the monthly price rose sharply (current price not checked).
- **Take:** steal 9 (offline re-render) and **camera-plus-visualiser composite** for TikTok. Both are content
  features that fit `arsenal/fl/vfx` and the spectacle recording plan. A light **tidy pass before render** (fix a
  stray note in a replay, never in the log) is the MIDI-editor steal.

#### LumaKeys (Mac, 2026)
- **Stands out:** a self-taught-pianist app that turns solo piano **audio into MIDI**, then falling notes with loop,
  slow-down and hand isolation, a piano roll, recording, and 4K export with your own AU/VST3 instruments.
- **Price:** free tier; Pro $69 until 2026-10-15, then $99.
- **Take:** confirms that the market for an ear player is "learn from recordings, then post a video". Our unique
  angle is *theory reading of your own playing*, which LumaKeys does not claim.

#### Rousseau-style videos
- **How they are made:** MIDI from the piano, After Effects animation, and LEDs driven by an Arduino from the
  piano's MIDI out. Free tools such as Piano VFX, and SeeMusic, recreate the look.
- **Take:** confirms the suggest-lights WLED direction and the SeeMusic offline-render steal.

---

## 3. What makes them sticky, sorted against our doctrine

| Mechanic | Who | What it does for the player | Verdict for Daniel | Why |
|---|---|---|---|---|
| Stars and scores per run | Melodics, Yousician, Simply Piano, Playground | clear "better or worse" | **Refuse** | P9; improvising has no right notes |
| Red and green notes | Playground, Piano Marvel | instant error signal | **Refuse** | P9 and Sunshine; our note classes (in chord, colour, rub, passing) replace "wrong" |
| Daily streaks | Simply Piano, Musora, Andante, Piano Companion | habit pressure | **Refuse** | P9; Spotify policy also bars streaks over a Spotify track (`spotify.md` 112) |
| Weekly count of nights played, no loss state | Yousician (weeks, not days) | gentle rhythm | **Adapt, ask** (Q2) | Only as a *calendar of sounds*: which nights he played and what he kept, with no counter and no "broken" state |
| Wait mode | Flowkey, Synthesia, Melodics, Metronaut, Piano Marvel Prepare | learn notes without tempo stress | **Confirms** | jam v2 "wait for me" |
| Earned speed (Auto BPM, speed training) | Melodics, Soundslice, iReal Pro | the challenge rises only when you're ready | **Adopt** (steal 4) | invisible difficulty: no number shown, only the tempo creeping up |
| Key cycling | iReal Pro | the real jazz practice routine | **Adopt** (steal 3) | turns one card into twelve nights |
| Slicing | Piano Marvel | chunking long material | **Adopt** as a Try option | no grade involved |
| Micro-assessments each practice | Piano Marvel | continuous, invisible measurement | **Confirms** | riff facts after every run |
| Clear next step at session end | Modacity | ends the session with momentum | **Confirms** | riff "one thing to try" |
| Adaptive difficulty band (flow) | Melodics, Skoove, PianoVision | never too hard or too easy | **Confirms** | suggest-lights growth-edge chip |
| Backing arrives as you improve | Simply Piano | reward is *sound*, not points | **Confirms** | Try → Loop ladder |
| Spoken coach | ROLI AI Music Coach | feels like a teacher in the room | **Adapt, ask** (Q3) | one TTS line per run, opt-in |
| Mood and focus log | Andante | self-knowledge | **Adopt** (cheap) | personal, not judged |
| Spaced review of learned items | Piano Companion flashcards | retention | **Adapt** | "sounds from your shelf you haven't played in 3 weeks" as a Tonight card, never a quiz |
| Social live rooms, leaderboards | Tonic, ToneGym, Yousician | belonging, competition | **Park** | privacy; not asked for |
| One-finger chords | Scaler Bind, Captain Play, KeyLab Chord mode, NI Play Assist | play beyond your hands | **Adopt via hardware** (steal 10) | he owns it |
| Band that follows your chords | Logic, Studio One, Captain, BiaB | instant jam | **Adopt** (steal 2) | the core jamming desire |

**The pattern behind the stickiest products.** Every sticky loop rewards the player with *sound* (a band joins, the
tempo rises, a chord you couldn't play is now under one finger) or with *a true fact about you* (Modacity's next
step, Andante's mood history). Points are a thin layer on top. For Daniel we build the two rewards and skip the
layer.

---

## 4. Chord accuracy: what the products teach

Background: commercial detectors mostly work from **audio**, which is much harder than our MIDI case. None publish
accuracy numbers. theory-nextgen's measured table (71/71 synthetic fixtures, 24/24 of his vocabulary) is already
beyond anything a vendor claims verifiably. So the lessons below are about **presentation, context and correction**
more than raw note-reading.

### 4.1 Vocabulary tiers are a user choice, separate from detection quality
- **Evidence:** Moises offers Easy, Medium and Advanced chord levels. Chord ai puts advanced chord types in pro.
  Chordify's Toolkit adds 7ths and sus4. Jamzone adapts chords to the player's level.
- **Lesson:** the same detection shown at different depths is a feature people pay for.
- **For us:** Daniel is learning names, so a **name depth** setting could help his lesson clips:
  - *plain* = triad or 7th plus slash bass;
  - *full* = today's next-gen names.
- **Caution:** theory-nextgen cut "four presets" (decision D4). This is one binary for the hero label only, and
  `ALSO` already carries the second name. Recommend: **not now**; revisit with the Lesson view (TN11), where a
  simpler name is a teaching choice.

### 4.2 Harmonic rhythm and the beat grid are part of detection
- **Evidence:** Logic Chord ID detects how often chords change as well as what they are. Moises, Band-in-a-Box's
  Audio Chord Wizard and Smart Pianist all detect bars first and chords per bar.
- **For us:** when a **jam run** is playing (a bar clock exists) or **practice-along** has a confident beat phase,
  add a **beat-grid prior** to the harmonic window: a commit that lands within about 120 ms of a beat, or on the
  bar, needs less settle time than one mid-beat. With no grid, today's 250 ms settle stays.
- **Invariant check:** this uses the transport's *clock*, not Claude's cue notes, so jam-spec C11 ("cue notes never
  reach `detect()`") holds.
- **Receipt to write:** on the six replay sessions, time with no name and core agreement with the grid prior on a
  synthetic 72 BPM grid versus off.

### 4.3 Context from the song beats cleverness on the chord
- **Evidence:** Smart Pianist, Moises, Chordify and Band-in-a-Box analyse the **whole song offline**, bar-lined, and
  cache it. Yamaha says outright that harmonically complex songs come out worse, and Logic's reviewer found dense
  material imperfect.
- **For us:** confirms practice-along's plan that song chords are v2 and must be **offline per song, bar-lined and
  cached**, never a live frame-by-frame guess. When a song chart exists, its chord at the current bar becomes a
  prior for naming Daniel's MIDI: prefer the reading that shares the song chord's root or function. That is the
  "which reading" tie-break theory-nextgen lacks when two readings score close.

### 4.4 Ranked readings with visible reasons
- **Evidence:** Scaler Detector ranks scales by goodness of fit. Cubase colours suggestions by how common they are.
- **For us:** theory-nextgen already ranks readings in the HUD with plain reasons. The only delta is to **colour the
  reason** (green "his bass note is the root", amber "root missing"). Small, HUD-only.

### 4.5 Correction is a first-class loop
- **Evidence:** Chordify and Moises let users fix charts. Logic's detections are meant to be edited. Scaler lets you
  click and reassign a detected chord.
- **For us:** theory-nextgen **deferred** "reading picker and pins" because pins split the screen from the log.
  Products argue for bringing the *correction* back in a different shape: **"call it this" writes to a Daniel
  lexicon**, not to the screen.
  - Store: `state/arsenal/piano/lexicon.json`, keyed by a transposition-invariant voicing key: bass interval plus
    the sorted set of upper intervals.
  - Effect: once he has called a shape `13sus4`, every transposition of that exact shape reads that way everywhere,
    so screen, log, rarity and suggestions agree. That removes the reason pins were deferred.
  - The frozen test corpus is untouched; lexicon entries are *his* overrides and are listed by
    `py -m arsenal.practice brief`.
  - Needs Daniel's OK and the conductor's (it changes a frozen-corpus neighbour).

### 4.6 Voicings deserve names too
- **Evidence:** Chord ai says it recognises voicing and position.
- **For us:** from MIDI we know the exact voicing, so a **voicing shape label** (steal 6) is honest:
  - *shell* (root, 3rd, 7th);
  - *rootless A or B*;
  - *quartal stack*;
  - *open 10th* (left hand);
  - *cluster on top* (a 2nd in the top three voices);
  - *spread*;
  - *drop 2*;
  - *upper structure* (a triad over a dominant shell).

  The rules are tiny interval tests on the reader's output. Show it in the HUD first; later it becomes a Lesson-view
  line and a riff fact ("7 of your 9 Gb chords were cluster-on-top voicings").

### 4.7 The stress cases are the same everywhere
- **Evidence:** Logic 12.3's release notes call out inversions and 6th, 7th and maj7 chords as improved.
  Capo's newest engine advertises inversions.
- **For us:** add a named **stress set** to the theory-nextgen corpus review queue: 6 versus m7 inversions
  (C6 = Am7/C), sus versus 11, and add9 versus 9. These are known cross-industry confusions, and they belong in the
  corpus, through the conductor.

---

## 5. Detections and displays worth adding (from products, or gaps no product fills)

Each item gives its source, the surface, and whether it is new. Surfaces follow the house rule: the recorded canvas
stays clean unless a spec already owns the slot.

| Detection | Source | What it shows | Surface | Status |
|---|---|---|---|---|
| **Progression family** | Hooktheory Trends / TheoryTab | "1-5-6-4 · the pop axis · heard in …" when a committed loop matches | Nashville-row caption on a sure match (needs caption priority slot, theory-nextgen 3.2) + HUD | **new** |
| **Harmonic rhythm** | Logic Chord ID | "one chord per bar", "changes every 2 beats", "your changes speed up into the ending" | HUD; riff fact | **new** |
| **Voicing shape** | Chord ai | shell / rootless / quartal / open 10th / cluster on top / upper structure | HUD → Lesson view; riff fact | **new** |
| **Top-voice balance** | ROLI "dynamic" dimension | top note's velocity versus the mean of the inner voices per chord; "your melody sings over the chord" | riff fact; Study readout | **new** |
| **Pedal-change timing** | no product seen (gap) | whether he lifts the pedal just after the new chord strikes (clean legato) or before (a gap) or late (a smear); median offset in ms per session | riff fact; practice verb | **new**, MIDI CC64 + onsets already in the log |
| **Roll versus block** | no product seen (gap) | onset spread of a chord gesture: block (< 30 ms), rolled (30-150 ms), arpeggiated; "you roll your 4 chords, block your 5s" | riff fact; spectacle already treats these as one event | **new** (the event model exists; the *label* is new) |
| **Harmonise my top note** | FL Studio 2026 Chord Stamp (top-down) | hold a right-hand melody note and the chips offer chords under it | suggestion variant (suggest-lights, after SG8) | **new** |
| **Scale fit reasons, coloured** | Scaler Detector, Cubase colours | why a scale ranks: his notes that fit or rub | HUD | small delta |
| **Song sections** | Smart Pianist, Moises | verse and chorus markers on a practice-along song; "loop the chorus" | practice-along v2 panel | new to practice-along |
| **Mood of the night** | Andante | one optional word per session, and where his moods live (keys, tempos) | session meta; `practice sessions` | **new** |
| **Named moments** | Capo named regions | "the Db opening" stored on the moment | `practice moment --name` | **new** (small) |
| **Continuous tempo follow** | Metronaut, MyPianist | bar clock re-estimated from his onsets inside a run | jam transport v3 | **parked** (needs v2 rhythm calibration) |
| Melody guide colouring | Hookpad | consonant or dissonant marks on his notes | jam v2 glass marks | confirms |
| Next-chord probabilities | Hookpad, Scaler, Cubase | chips | suggest-lights | confirms |
| Wait mode, loops, count-in | Flowkey, Synthesia, Melodics, Moises | | jam v1/v2, practice-along | confirms |

**Why the two gaps matter.** Pedal timing and roll-versus-block are *lush-pedalled-harmony* skills, exactly
Daniel's style, and no app surveyed reads them. Learning apps grade note accuracy because that suits beginners.
Our log already records CC64 and onsets, so these are pure `practice.py` work.

---

## 6. Ranked integration backlog (for Vandor)

Cost: S = under a day of one lane, M = a wave slot, L = a multi-wave feature. Status: **new** = not in any current
spec; **delta** = a change to a planned feature; **confirms** = planned already (listed only in sections 2-5).

| # | Item | Products | Lands in (files / verbs) | Cost | Conflicts and guards | Status |
|---|---|---|---|---|---|---|
| B1 | **Loop me**: capture the last 2-8 bars from the log; loop them exactly under the bar clock; ends snap to bar lines (or gesture bounds with no tempo) | Scaler multi-bind, Soundslice snap, loopers | jam transport run kind `loop_me` replaying the log slice (like Hear me); `practice moment` supplies the slice | M | Replay notes are **his**, so they must not re-enter `detect()` or the log (same rule as cue notes, jam C11); jam view `auto` moves them to glass during REC | new |
| B2 | **Band follows my chords**: the committed reading drives bass (Bass rule) and comp (Narrow rule), landing on the next beat; auto-drop the comp lane while he comps (BiaB) | Logic, Studio One, Captain, BiaB | `groove.js` (a pattern re-pitched per chord), `band` voicer; reading from theory-nextgen `harmony.js` | L | One-beat lag is honest; say so in the Now header; no tempo guessing (needs a run tempo) | new |
| B3 | **Around the keys**: run field `cycle` (interval 5, -1, or "his keys"; every pass) | iReal Pro | jam run schema 4.3, top-of-pass key change path (C3) | S | Card transposition fixture A4 extends to cycled runs | delta |
| B4 | **Earned speed**: run field `speed {start, step_bpm, gate:"clean"}`; clean = riff alignment shows the chord tones landed in each bar | Melodics, Soundslice, iReal Pro | jam run + tempo map step changes (9.1) | S-M | No number shown to him beyond the bpm already in the Now header | delta |
| B5 | **Moment to FL**: `py -m arsenal.practice moment <t> --mid out.mid`, with chord names as MIDI marker text | Scaler, Captain drag-to-DAW; FL 2026 Chord Panel | `practice.py` `moment` verb | S | Read-only on the log; writes one file where Daniel names it | new |
| B6 | **Voicing shape label** | Chord ai | theory-nextgen `chordread.js` output → HUD line | S | HUD only first (no canvas) | new |
| B7 | **Pedal timing + roll/block + top-voice balance** as riff facts and a `practice` verb (`touch`) | ROLI dimensions; gaps | `practice_riff.py` facts; new verb in `practice.py` | M | Wording guard P9: facts with times, never grades | new |
| B8 | **Progression family** caption and table | Hooktheory | new `progressions.json` (our own list of common progressions, plain names, a few song examples we write ourselves) + caption source | M | Licensing (7.1); caption priority below key change | new |
| B9 | **Daniel lexicon** ("call it this") | Chordify, Logic, Scaler editing | `state/arsenal/piano/lexicon.json`; reader consults before ranking | M | Revives a deferred theory-nextgen item in a new shape; conductor plus Daniel | delta (to a deferred item) |
| B10 | **Beat-grid prior** for the harmonic window during runs and along | Logic, Moises, BiaB | `harmony.js` settle rule | S-M | Receipt on six replay sessions (4.2); clock, not cue notes | new |
| B11 | **Slices for Try** (bar pairs → half → whole) | Piano Marvel | jam Try option | S | none | new |
| B12 | **Offline re-render from log** at fixed timestep, 4K; camera composite | SeeMusic, LumaKeys | spectacle recording plan; `arsenal/fl/vfx` | M-L | Check against spectacle 3.4 first; the adaptive-resolution work applies | new (verify) |
| B13 | **KeyLab Chord-mode card** + `controller_mode` session meta and HUD warning | Arturia, NI | deck seed card; `log.js` session meta | S | Log honesty for `practice` stats | new |
| B14 | **Harmonise my top note** chips | FL Chord Stamp | suggest-lights engine variant | M | After SG8 | new |
| B15 | **Mood word** per session | Andante | session meta; `practice sessions` column | S | Optional, never prompted during REC | new |
| B16 | **Ear play-back from his log** (the page plays his own past move; he finds it) | EarMaster, ToneGym | deck card kind "Find it"; uses Hear me | M | Sunshine: prediction, not a quiz; no points | new |
| B17 | **Shelf review** (kept sounds not played in 3 weeks become a Tonight card) | Piano Companion spaced repetition | deck Tonight tab | S | no counters | new |
| B18 | Continuous tempo follow | Metronaut, MyPianist | jam transport | L | After v2 rhythm calibration | parked |
| B19 | Spoken coach line (TTS) after a run | ROLI AI Music Coach | riff output → TTS | M | Q3; no voice during REC | parked (ask) |
| B20 | Local stem separation for practice-along ("mute the song's keys") | Moises, Ableton 12.3 | practice-along v3 | L | Model download needs Daniel's approval; never on Spotify audio under Route S | parked |

**Suggested order.**
1. Right after jam v1 lands: B5, B6 and B13. They are small, need no page surgery in the jam files, and give Daniel
   something to try this week.
2. With jam wave 2: B3, B4 and B11 (run fields).
3. Its own wave: B1 (Loop me), because it touches transport and log rules.
4. With the rhythm work: B7 and B10.
5. After suggest-lights SG8: B2 (the band follows) and B14.
6. Content wave: B8 and B12.

---

## 7. Risks, licensing and refusals

### 7.1 Data licensing (progression family, next-chord probabilities)
- Hooktheory's Trends API needs an account login and a bearer token. I could not read the terms (403).
- **Do not** build on their API or copy their database without Daniel reading the terms.
- The safe path is **our own table** of common progressions described in Nashville numbers. The progressions
  themselves are not protected expression; song examples should be few and written by us.

### 7.2 Proprietary content
- RealTracks, Jamzone stems, Musora videos and Hookpad's database are the products. We take **mechanics** (follow
  rules, key cycling, slicing), never content or trade dress.
- Public videos should not name product features ("Scaler-style") on screen.

### 7.3 Downloads and accounts
- Stem separation models, Lyria or Magenta RT, and TTS voices all need Daniel's explicit approval before any
  download, API key or account.

### 7.4 Spotify
- Practice-along's policy edges (analysis, games, recording) apply to anything here that touches a playing Spotify
  track. B20 is local files only.

### 7.5 Doctrine
- Section 3 refuses scores, streaks, red notes and percentages (P9, Sunshine).
- Anything touching streak-like rhythm is behind Q2.

### 7.6 Unverified items
- Prices marked aggregator or not checked.
- PianoVision Plus price unknown.
- Studio One's current naming and price not verified.
- SeeMusic current price not verified.
- Whether spectacle 3.4 already plans an offline re-render (B12): check before claiming it is new.

---

## 8. Questions for Daniel (three, each with a recommended default)

1. **Loop me or band-follows-me first?** Both are jamming features:
   - Loop me = you play 4 bars and play over yourself;
   - band follows = bass and chords join whatever you hold.

   **Default: Loop me first.** It is cheaper, and it uses your own sound and timing, so it feels like you from the
   first night.
2. **A calendar of your nights, with no counters?** A small month view showing which nights you played and the one
   sound you kept each night. It has no streak number and no "broken" day. **Default: no** (P9). Say yes only if
   you'd like to see it.
3. **Should Claude ever speak one line out loud after a loop** (like ROLI's coach), instead of only in chat?
   **Default: no.** Chat stays the place, and nothing speaks while you record.

---

## 9. Sources

Harmony brains
- Hooktheory Trends: https://www.hooktheory.com/trends
- Hooktheory Trends API docs: https://www.hooktheory.com/api/trends/docs ; API walkthrough: https://pappubahry.com/misc/piano_diaries/hooktheory_api/ ; MCP wrapper (auth details): https://github.com/gabguerin/hooktheory-mcp
- Hookpad: https://www.hooktheory.com/hookpad ; pricing: https://www.hooktheory.com/hookpad/pricing ; review: https://producelikeapro.com/blog/hooktheory-hookpad-review/ ; aggregator pricing: https://ai.toolsinfo.com/tool/hookpad
- Scaler 3: https://scalermusic.com/products/scaler-3/ ; what's new: https://help.pluginboutique.com/hc/en-us/articles/35864679857684-What-s-new-in-Scaler-3 ; MusicTech: https://musictech.com/news/gear/plugin-boutique-scaler-3/ ; review: https://audioblob.com/scaler-3-review-and-first-impressions/
- Scaler Detector: https://www.kvraudio.com/news/scaler-music-releases-scaler-detector-key-and-chord-detection-plugin-65088 ; https://bedroomproducersblog.com/2025/10/29/scaler-detector/
- Captain Plugins Epic: https://mixedinkey.com/captain-plugins/ ; FAQ: https://mixedinkey.com/faq/captain-plugins-epic-faq/ ; Epic 7: https://mixedinkey.com/captain-plugins/version-7/
- Cubase Chord Assistant: https://www.steinberg.help/r/cubase-pro/14.0/en/cubase_nuendo/topics/chord_pads/chord_pads_chord_assistant_c.html ; proximity: https://steinberg.help/cubase_pro/v11/en/cubase_nuendo/topics/chord_pads/chord_pads_chord_assistant_proximity_c.html
- Studio One Chord Track: https://www.audeobox.com/learn/studio-one/chord-track-guide/ ; https://www.soundonsound.com/techniques/studio-one-chord-track-nashville-numbering
- Logic Session Players: https://support.apple.com/guide/logicpro/session-players-overview-lgcpbf624405/mac ; chords and players: https://support.apple.com/guide/logicpro/chords-and-session-players-lgcp70dd5af3/mac ; analyse chords: https://support.apple.com/guide/logicpro/analyze-chords-audio-midi-regions-logic-pro-lgcp4993e80c/mac
- Logic Pro 12: https://cdm.link/logic-pro-12-hands-on/ ; https://weraveyou.com/2026/01/logic-pro-12-launches-ai-synth-player-chord-id-smart-music-tools/ ; 12.3: https://synthanatomy.com/2026/06/apple-logic-pro-12.html
- Ableton Live 12 MIDI Tools: https://www.ableton.com/en/live-manual/12/midi-tools/ ; keys and scales FAQ: https://help.ableton.com/hc/en-us/articles/11425083250972-Keys-and-Scales-in-Live-12-FAQ ; generators: https://www.soundonsound.com/techniques/ableton-live-12-midi-generators
- Ableton Live 12.3: https://www.ableton.com/en/blog/live-12-3-is-here/ ; https://cdm.link/ableton-live-12-3-guide/
- FL Studio 2026: https://blog.dubspot.com/fl-studio-2026-whats-new ; https://dawzone.com/fl-studio-2026-new-features-flex-gopher-and-workflow-updates ; FL 2025: https://blog.dubspot.com/fl-studio-2025-strong-update-with-game-changing-creative-tools
- Piano Companion: https://www.songtive.com/products/piano-companion

Backing and accompaniment
- iReal Pro: https://www.irealpro.com/ ; App Store: https://apps.apple.com/us/app/ireal-pro/id298206806 ; buying: https://www.irealpro.com/learn/buy-ireal-pro/ ; Android price: https://www.appbrain.com/app/ireal-pro/com.massimobiolcati.irealb
- Band-in-a-Box 2026: https://www.pgmusic.com/bbwin.htm ; features: https://www.pgmusic.com/bbwin.features.htm ; Sweetwater: https://www.sweetwater.com/store/detail/BIAB26ProW--pg-music-band-in-a-box-2026-pro-for-windows
- Jamzone: https://www.jamzone.com/piano.html ; review: https://geekazine.com/cool/review/jamzone-backing-tracks-built-for-real-musicians/
- Metronaut: https://metronautapp.com/what-is-metronaut
- MyPianist: https://symposium.music.org/64-1/item/11623-harmony-at-your-fingertips-mypianist-an-ai-powered-piano-accompaniment-application.html
- Live Music Models (Lyria RealTime, Magenta RT): https://arxiv.org/abs/2508.04651 ; https://magenta.withgoogle.com/magenta-realtime

Song-audio tools
- Moises features: https://moises.ai/blog/latest/moises-features/ ; 2026 review (pricing): https://sunowatermark.com/blog/moises-ai-review-2026/
- Chordify Toolkit: https://chordify.net/premium-plus-toolkit ; subscriptions: https://support.chordify.net/hc/en-us/articles/360002273238-What-are-the-subscription-options
- Chord ai: https://chordai.net/ ; App Store: https://apps.apple.com/us/app/chord-ai-play-any-song/id1446177109
- Capo: https://supermegaultragroovy.com/products/capo/ios/
- Yamaha Smart Pianist: https://hub.yamaha.com/pianos/p-digital/smart-pianist-version-2-0/ ; audio to score: https://hub.yamaha.com/pianos/p-digital/getting-the-most-out-of-audio-to-score/
- Klangio Piano2Notes: https://klang.io/piano2notes/
- Songsterr Plus: https://www.songsterr.com/plus ; review: https://www.guitarchalk.com/full-songsterr-review/
- Soundslice: https://www.soundslice.com/features/ ; speed training: https://www.soundslice.com/blog/215/introducing-speed-training/ ; looping: https://www.soundslice.com/blog/199/introducing-enhanced-slowdown-and-perfect-looping/

Learning apps
- Melodics Practice Mode: https://support.melodics.com/en/articles/6777027-practice-mode ; how it works: https://melodics.com/how-it-works ; plans (retailer): https://www.sweetwater.com/store/detail/MelodicsStdMon--melodics-standard-plan-monthly ; aggregator: https://subger.com/en/us/service/melodics
- Yousician: https://americansongwriter.com/yousician-piano-review/ ; gamification: https://trophy.so/blog/yousician-gamification-case-study ; pricing (aggregator): https://subger.com/en/service/yousician
- Simply Piano: https://www.musicradar.com/reviews/simply-piano-review ; pricing: https://www.pianostartguide.com/simply-piano-review/
- Flowkey: https://www.pianodreamers.com/flowkey-review/
- Skoove: https://pianoers.com/skoove-review/
- Playground Sessions: https://www.musicradar.com/reviews/playground-sessions-review ; https://smarterlearningguide.com/playground-sessions-review/
- Piano Marvel: https://pianomarvel.com/en/feature/sasr ; practice mode: https://pianomarvel.com/en/feature/practice-mode ; review: https://www.pianodreamers.com/piano-marvel-review/
- Musora / Pianote: https://www.musora.com/the-new-musora-app ; https://www.musora.com/piano
- ROLI Airwave: https://roli.com/us/product/airwave-learn ; AI Music Coach: https://musictech.com/news/gear/roli-ai-music-coach-airwave-first-look/ ; https://roli.com/blog/ai-music-coach-in-the-roli-learn-app ; Learn membership: https://roli.com/us/product/learn-membership ; NAMM 2025: https://www.musicradar.com/music-tech/midi-controllers/namm-2025-rolis-piano-is-a-larger-keyboard-for-use-with-its-airwave-hand-tracking-hardware-and-music-learning-software-but-is-it-large-enough ; Piano M: https://techcrunch.com/2025/01/23/roli-releases-a-49-key-educational-keyboard-and-generative-ai-play
- PianoVision: https://www.pianovision.com/features/ ; 2.0: https://mixed-news.com/en/piano-vision-update-2-0/ ; review: https://pianoers.com/pianovision-review/
- ToneGym: https://www.tonegym.co/ ; ear training overview: https://sonofield.com/blog/best-ear-training-apps-2026
- Modacity, Andante, Tonic: https://pract.is/blog/modacity-alternatives-practice-apps-for-serious-musicians ; https://andante.app/ ; https://www.jointonic.com/

Hardware
- Arturia KeyLab 88 mk3: https://www.arturia.com/products/hybrid-synths/keylab-88-mk3/overview ; review: https://musictech.com/reviews/controllers/arturia-keylab-mk3-review/ ; https://www.musicradar.com/news/arturia-keylab-mk3
- NI Kontrol S MK3: https://blog.native-instruments.com/kontrol-s-series-mk3/ ; scale manual: https://docs.native-instruments.com/ni-tech-manuals/kontrol-s-mk3-manual/en/scale

Visualizers and content
- Synthesia: https://www.synthesiagame.com/ ; https://latouchemusicale.com/en/synthesia/
- SeeMusic: https://www.seemusicapp.com/ ; price report: https://pianoandsynth.com/seemusic-skyrockets-monthly-subscription-by-450-with-nothing-new-to-see/
- LumaKeys: https://lumakeys.app/ ; comparisons: https://lumakeys.app/piano-app-comparisons
- Rousseau-style: https://newwestsymphony.org/rousseaus-hypnotic-piano-visualizations/ ; Piano VFX alternatives: https://alternativeto.net/software/piano-vfx/
