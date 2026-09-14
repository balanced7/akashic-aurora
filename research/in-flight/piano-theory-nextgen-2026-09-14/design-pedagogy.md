# Theory display, next gen: what helps an ear player learn

| | |
|---|---|
| Status | Design, 2026-09-14. Pedagogy lens only. No code edited, no server or browser started, nothing installed. |
| Asked for | Daniel, verbatim (Discord, from work): "Do you think we can brush up our chord and scale detection to show things in an even better way? I love where its at now. But I am excited to see what is the next Gen level we can bring it to!" |
| This file answers | Which theory views build Daniel's understanding and which are noise. The order to reveal them. The words to use. How progressions become shapes he recognises in any key. How tension and resolution become visible. How all of this links to the jam cards, chord suggestions and riff reports. How to keep playing light and put the reading after. |
| Built from | `arsenal/web/piano.js` THEORY block and overlay (`drawLabel`, `drawNumbers`, `LAYOUT`, `keyView`, `spellForKey`); `arsenal/web/piano/nashville.js` (conventions, `createKeyTracker`, the diatonic flag, the cadence rules); `arsenal/practice.py` (classes, readings, `GLOSSARY`); commit messages of `5cff2c61` and `de1334bf`; `research/in-flight/piano-jam-2026-09-14/jam-spec.md` (C11, C14, C19, 8.5-8.10, 11.3-11.4, 12, 13.4); `design-ux.md` 9.3 (riff report card); `house-ideas/sunshine.md`, `heimdall.md`, `navi.md`; `research/in-flight/piano-spectacle-2026-09-13/spectacle-spec.md` (D8, 2.3, 4.2, the phrase card); `research/in-flight/piano-suggest-lights-2026-09-14/chord-suggestions.md` and `key-lights.md`. |
| Measured tonight | Read-only scripts in the session scratchpad (`theory-nextgen/measure*.py`) over the six logged sessions. They used the raw chord events (what the live label showed) and `py -m arsenal.practice windows --json`, `history` and `name`. Section 1 has the numbers. |
| Privacy | Counts, chord numbers and number sequences only: no session ids, clock times or transcriptions. Sessions are called S1-S6, oldest first by local start time. The voicings in 1.2 are synthetic test chords, not his. Scratchpad outputs stay in the scratchpad. |

---

## 0. The answer in one screen

1. **Three moments, not one screen.**
   - **Play** is for a glance: the chord, its number, and at most one feel mark.
   - **Rest** is one calm card in the silence after a phrase: one sentence about what he just did.
   - **Study** comes after playing: a single screen in the deck drawer (or chat) with his playing written in numbers, his shapes, the lean line, one question and one thing to try.
2. **While he plays, the page shows fewer and steadier things.** Nearly everything this design adds goes to Rest and Study. Play gets three changes:
   - a steadier chord name, as an option;
   - a number that uses the bass-aware reading;
   - a small "lean and land" mark.
3. **Reveal by the ear, not the textbook:** home, then shapes, then colour, then the floor (bass), then lean and land, then borrowed colour, then doors (key changes), then form. His hands already do every rung. The ladder only orders the *words*.
4. **Plain word first, theory name second.** One shared word list serves the page, chips, cards, riff reports and banners. Examples: "the bright 4 · Lydian"; "pulls to 6m · secondary dominant".
5. **Numbers are the shape; letters are the address.** His own moves become shapes on a shelf, each marked "played in N keys". He already repeats 72 two-chord moves in two or more keys (1.4).
6. **Tension is shown as separate ingredients**: the rub (inside a chord), the lean (between chords), the distance (from the key) and time (how long before landing). Only the lean gets a live mark. In the counts, his leans are sus floats and colour as often as dominant pulls, and he lands on 6m often (1.5). A single "tension meter" would teach the wrong thing.
7. **Fix the names first.** The page's number row and the practice analyser disagree on the chord's number for 24.5% of his chord time. In the chord windows the analyser reads as his signature Lydian 4, the row shows a 4 for 3.5 s of 119.6 s (1.2). Teaching function through a number that contradicts itself would teach wrong shapes.
8. **Budgets:**
   - Play: at most one new learning mark per chord gesture, and no learning text that changes while notes sound.
   - Words: one new theory word per session.
   - Study: three facts, one question and one try come first; the rest sits behind "more".
   - Every added mark stays off the recorded canvas unless he opts in.

---

## 1. What his playing says about how to teach it

These measurements come from six sessions recorded in one day. They show direction, not settled habits. Every threshold later in this file is a first guess, to be tuned with him.

### 1.1 The live chord name changes much faster than the harmony

The page logs a chord event every time the big label changes. A label's "life" is the time until the next change. The harmony windows are the practice verbs' merged chords (arpeggios joined, passing notes ignored).

| Session | Label changes | Per minute | Median label life | Changes under 0.3 s | Labelled time on names that lasted ≥ 1 s | Harmony windows | Median window |
|---|---|---|---|---|---|---|---|
| S1 | 536 | 99 | 0.09 s | 71% | 63% | 169 | 1.22 s |
| S2 | 507 | 98 | 0.30 s | 50% | 60% | 136 | 1.62 s |
| S4 | 376 | 96 | 0.30 s | 50% | 65% | 108 | 1.62 s |
| S5 | 571 | 73 | 0.26 s | 53% | 69% | 173 | 1.64 s |
| S6 | 1,615 | 234 | 0.03 s | 87% | 39% | 194 | 1.10 s |

- The label changes 3.2 to 8.3 times as often as the harmony does.
- In the busiest session, for 61% of the labelled time the name on screen was one that lasted under a second.
- S3 is left out. Its log holds 25 label changes a minute against 73-234 in the others. That fits the covered-tab gap described in commit `5cff2c61`, where chord events were lost before detection also ran off MIDI events (an inference, not verified).
- **For teaching:** a name that lasts 0.03-0.3 s can be seen but not read. While he plays, the chord that teaches is the chord he *means*: the gesture, not each note of the roll. The note chips already show the notes as they arrive. The big name can afford to wait for the gesture.

### 1.2 The number disagrees with the analyser a quarter of the time, and almost always on his signature chord

This compares the page's own number (`detect.number`, which is what the Nashville row drew) with the analyser's bass-aware reading (`number`), using core numbers (degree plus major, minor or sus) and chord windows only.

| | S1 | S2 | S3 | S4 | S5 | S6 | All |
|---|---|---|---|---|---|---|---|
| Chord time where the core number differs | 35% | 25% | 23% | 30% | 26% | 13% | **418 of 1,705 s (24.5%)** |

The most common disagreements, by time:

| Page's number row said | Analyser reads | Seconds |
|---|---|---|
| 1 | 4 | 74.8 |
| 6m | 4 | 54.7 |
| 1 | 6m | 45.3 |
| 6m | 5 | 37.6 |
| 2m | 4 | 34.8 |
| 5 | 4 | 27.6 |

- **The Lydian 4.** The analyser reads 119.6 s of chord windows as a 4 with its #11 (4maj7#11, 4maj9#11, 4maj13#11, 4^6/9(#11)). For 3.5 s of that time the page's number row showed a 4. (The `history` verb's total for 4maj13#11 is larger because it counts differently: bass left out, every window kind included.)
- **The analyser is not ground truth.** This table measures disagreement, not the page's error rate. The next table shows both sides missing.

Known-gap voicings, synthetic, through `py -m arsenal.practice name ... --key "Eb major"`:

| Voicing | Page's namer | Analyser's first reading | What an ear player loses |
|---|---|---|---|
| Ab2 Eb3 G3 Bb3 C4 D4 (maj9#11) | Cm9/Ab = 6m9/4 | Abmaj9#11 = 4maj9#11 | the bright 4 is called a shade (6m) |
| Ab2 Eb3 G3 C4 D4 F4 Bb4 (maj13#11) | Cm11/Ab = 6m11/4 | Abmaj13#11 = 4maj13#11 | the same |
| Bb2 F3 Ab3 C4 Eb4 G4 (a 13sus4 shape) | Fm9/Bb = 2m9/5 | Eb6/9(11)/Bb = 1^6/9(11)/5 (Bb9sus4(13) only third) | the float of a sus 5 is called a 2 or a 1 |
| Bb2 Ab3 C4 Eb4 G4 | Abmaj7/Bb = 4maj7/5 | Ebadd11(13)/Bb = 1add11(13)/5 (Bb9sus4(13) fifth) | the same |
| Bb2 F3 Ab3 C4 D4 Eb4 (dominant 11) | Bb11 = 5^11 | Ab6/9(#11)/Bb = 4^6/9(#11)/5, "the Lydian 4" | here the analyser loses the 5 chord |

**For teaching:**
- A number teaches a feeling: 1 is home, 4 is lift, 6m is shade, 5 leans. When the number is from the wrong family, the feeling word is wrong too.
- The misses cluster on exactly the chords that define his sound: the Lydian 4 and the sus 5.
- The sus 5 is where his growth edge lives (1.5).
- Section 11 puts these fixes ahead of any new teaching surface.

### 1.3 A small family of numbers carries most of his time

Chord windows only.

| | Distinct | Cover half the chord time | Cover 80% | Cover 95% |
|---|---|---|---|---|
| Core numbers (4, 1, 6m ...) | 25 | 3 | 5 | 12 |
| Exact numbers (4maj13#11, 1maj9 ...) | 125 | 12 | 35 | |

- **The top core numbers:** 4 (26%), 1 (24%), 6m (16%), 2m (8%) and 5 (7.5%).
- **For teaching:** the syllabus is his family, not the textbook's list.
  - The five core numbers are the anchor.
  - The 125 exact numbers are colours those five wear.
  - Teach "your 4 wears these colours" rather than 125 chord names.

### 1.4 He already plays the same moves in many keys

These are moves between core numbers, counting chords of 0.5 s or more, with repeats merged, inside one key area. His chord windows span 11 keys.

| | Distinct moves | Played in ≥ 2 keys | Played in ≥ 3 keys |
|---|---|---|---|
| Two chords | 150 | 72 | 42 |
| Three chords | 340 | 97 | 44 |

The most widely travelled:

| Move | Keys | Times |
|---|---|---|
| 1 → 4 | 9 | 42 |
| 2m → 4 | 9 | 19 |
| 4 → 1 | 8 | 42 |
| 6m → 1 | 8 | 29 |
| 1 → 6m | 8 | 24 |
| 4 → 5 | 8 | 23 |
| 6m 1 4 | 6 | 13 |
| 1 6m 1 | 6 | 10 |
| 1 2m 4 | 6 | 7 |
| 1 4 1 | 5 | 13 |
| 4 5 6m | 5 | 8 |

- **Caveat:** key areas are the analyser's. A mis-keyed area would add a key to a move.
- **For teaching:** he does not need to be taught to transpose. He already does it by ear and hand. The lesson is only *what stayed the same*, and the number is that thing.

### 1.5 His tension floats more than it pulls

Chord windows:

| Lean kind | Windows | Seconds | Next chord's root a fifth lower |
|---|---|---|---|
| A dominant-type chord with its 3rd (7, 9, 13 and altered forms), any degree | 43 | 67.4 (4% of chord time) | 10 |
| A sus chord on the 5 | 32 | 55.1 | 10 |
| The analyser's "secondary dominant" class | 12 | 22.7 | |

Cadences from the `history` verb:
- 4 → 1: 29
- 5 → 6m: 11
- 5sus → 1, b7 → 1, and a 5 over a 1 pedal resolving to 1: 1 each

(`chord-suggestions.md` 1.2 counts dominants with their 3rd at about 35 s. It counts only the qualities 7, 9 and 13; this file counts every dominant-type suffix with its 3rd.)

**For teaching:**
- As far as these counts reach, his tension lives in sus chords, the #11 colour and landing on 6m instead of 1. Rubs inside his voicings were not counted here.
- Dominants with their 3rd are 4% of his chord time. Only 10 of those 43 windows were followed by a chord a fifth lower: the pull is new ground for his hands.
- A display that marks only dominants would stay silent through most of his tense-sounding playing. The rub and the float need to be visible too (section 8).

### 1.6 Leaving the key is rare, so it can be an event

By window time:
- diatonic: 87%;
- modal: 1.5%;
- borrowed: 1.4%;
- secondary dominant: 1.1%;
- chromatic: 1.1%.

The rest is single notes, lines, broken chords and bass lines.

**For teaching:** about one chord moment in twenty leaves the key. A quiet mark on those moments is information. A class word on every chord would be wallpaper.

### 1.7 The key is often unsure

- **Time the tracker called its key "unsure":** S1 17%, S2 22%, S3 33%, S4 11%, S5 22%, S6 16%.
- **Time a number was drawn at all:** 80-90%.
- **Key areas per session:** 6, 3, 6, 1, 3 and 4.
- **For teaching:**
  - Live number marks follow the existing dimming.
  - Anything that relies on function (the lean mark, shape recognition) turns off while the key is unsure.
  - Study uses the analyser's key areas. They are decided after the fact, with evidence.

---

## 2. Principles every surface follows

| # | Principle | Where it comes from |
|---|---|---|
| P1 | **Sound, then hands, then name.** Try → Notice → Name. | Sunshine 4 |
| P2 | **Glance while playing, read while resting.** Words that need reading wait for a rest. | 1.1 |
| P3 | **One thing at a time.** One new mark per gesture; one new theory word per session; one note of difference per stretch ("one degree stranger"). | Sunshine 3 |
| P4 | **Numbers are the shape, letters are the address.** | 1.4 |
| P5 | **A name is a handle, not a verdict.** When two names fit, say both ("roof and floor"). | Sunshine 4, card 12.3 |
| P6 | **His moves are the textbook.** Every claim in Rest or Study can be heard: a Hear button on his own moment, or a card. | Sunshine 4, Heimdall 3.3 |
| P7 | **Never teach through a name the screen will contradict.** | 1.2 |
| P8 | **Feelings first, function second:** home/gravity, light/shade, floor, lean/land, rub/release. | Sunshine 4, card 10 |
| P9 | **Progress is what he keeps, not a score.** No percentages, streaks, grades or "best". | riff wording guard (jam-spec 11.4) |
| P10 | **The recorded canvas stays his.** Everything this design adds is glass or DOM, or opt-in on the canvas. Today's look stays reachable. | jam-spec C14, suggestions 3.6 |

---

## 3. The views audited: what builds understanding, what is noise

Verdicts: **keep** (as it is), **steady** (keep, change how it settles), **move** (show it in Rest or Study instead of Play), **quiet** (internal or CLI only). Nothing is removed. Every change is a setting, and today's behaviour stays one click away.

| Element | What it builds for an ear player | Play | Rest | Study | Verdict |
|---|---|---|---|---|---|
| Big chord name (letters) | Ties a sound to the name musicians use | yes | | yes | **steady**: optionally hold each gesture (4.1) |
| Note chips in pitch colours | Which notes make the sound; colour memory per note | yes | | yes | **keep**: the bridge between hands and names, and they update at once while the name waits |
| Interval caption (`MINOR 9TH`, `POWER CHORD`) | Two-note shapes by name | yes (two notes only) | | | **keep** |
| Nashville row (`4maj13#11 in E♭ major`) | Function, and shapes across keys | yes | | yes | **keep**, drawn from the bass-aware reading (11.1) |
| `outside E♭ major` caption | Distance from home | yes | | yes, with its source named ("borrowed from E♭ minor") | **keep** |
| Dimming and "listening for the key" | Honesty about the key | yes | | | **keep** |
| Grand staff | Notation, and the look of the video | yes (unchanged) | | the place to show "the one note that moved" | **keep**; no new teaching on it while playing |
| Rarity banner and reasons | "Unusual for you", with a music reason | as the spectacle spec | phrase card | | **keep**; reason words from the shared word list (6.3) |
| Extended readings ("(reading)" names) | The real function of his lush chords | no (it feeds the number only) | | yes, as roof and floor | **move** |
| Class words (borrowed, modal, secondary dominant, chromatic) | Where a chord comes from | no (the `outside` caption is enough) | one, when it happened | yes | **move** |
| Mode names (Lydian, Dorian, Mixolydian) | Scale colour | no | | yes, only through the riff naming gate (jam-spec 11.3 step 6) | **move** |
| Key areas and modulations | Doors and form | the key caption changes (today) | "new home" | key map | **move** |
| Cadence names (plagal, authentic, deceptive) | How arrivals land | the lean and land mark, no words | | yes | **move** |
| Pedal points, bass lines | The floor | no | | yes | **move** |
| Suggestion chips | What could come next | only while he holds a chord (their restraint rules) | | "kept as card" | **keep**: the only proactive teacher in Play |
| Ghost keys (Try, suggest) | Where the hands go | yes | | | **keep** |
| Riff talking points, question, try | His habits named | | | yes (chat in v1, report card in v2) | **keep** |
| Counts and times ("42 times", a time as m:ss) | Evidence | never | at most one number | yes | **move** |
| Chord cost, runner-up keys, r values | Nothing | | | | **quiet**: HUD and CLI only |
| `^` joiner, `(no3)`, `6/9(#11)/5` spelled out in text | Nothing; a speed bump | never (the overlay already draws superscripts) | never | superscripts; `(no3)` as "no 3rd" | **quiet** |
| Spelling twins (C♭maj9 or Bmaj9) | Nothing for the ear | the key's spelling only | | a one-time note: "same keys as B" | **quiet** |

**The three biggest sources of noise today**
1. The name flickering through rolls and pedalled runs (1.1).
2. Confident numbers from the wrong family on his signature chords (1.2).
3. Theory-first or double-meaning words where a plain word exists (6.3).

---

## 4. Three moments: Play, Rest, Study

### 4.1 Play: a glance

**Goal.** One glance answers "what is this, and where am I", then his eyes can go back to nothing.

**What Play shows (the three changes):**
1. **A steadier name, as a setting.** `Chord name: follow every note (today) | hold each chord`.
   - "Hold each chord" commits one name per harmonic gesture, using the spectacle spec's event boundaries (4.2): pedal lift, bass change, block strike or rest. It shows the richest settled reading of that gesture.
   - While the name holds, the chips keep updating note by note, so nothing feels frozen.
   - The default stays today's until Daniel has tried both (question 1, section 14).
2. **The number from the bass-aware reading** (11.1), so the row says 4 when he plays his bright 4.
3. **One feel mark: lean and land** (8.2). A small chevron after the number when the chord leans, and one size pulse when it lands.

**What Play never shows:** class words, mode names, counts, cadence names, alternative names, anything that scrolls, and anything in the recorded canvas that is not there today (unless he opts in).

**Gates:**
- The key is unsure (`keyView.dim`): the number dims as today, and the lean mark is off.
- A Loop or Try run is active: the label stays his (C11). Lean marks follow his chord in the jam key (8.10). Try's ghosts own the keys.
- He plays fast (6 or more note-ons in 2 s, the suggestion engine's busy rule): no new lean marks.
- **Just play** (one switch): hides every mark this design adds. Today's canvas stays.

**Sketch (9:16, existing boxes):**

```
   y 148-488   Abmaj13♯11                 <- label box (unchanged); name holds for the gesture
               A♭ E♭ G C D F B♭           <- note chips, pitch colours, live
   y 471-601   4maj13♯11  IN E♭ MAJOR     <- Nashville row, bass-aware number
   ...
   y 471-601   5⁷ ›  IN E♭ MAJOR          <- a leaning chord: chevron after the number (glass by default)
   y 471-601   1maj9  IN E♭ MAJOR         <- lands: number and chevron pulse once in size, never brightness
```

### 4.2 Rest: one sentence in the silence

**When:**
- Rest follows the courtesy gate (jam-spec 8.9): 1.2 s with nothing sounding, or 3.0 s with no note-on while only pedal-held notes ring.
- The phrase just played must have produced something the chooser can back with evidence.
- Never in the first 90 s of a session (Sunshine's spill).

**What.** One card of 12 words or fewer, plain words, with a Hear button. A theory name may appear only if it is tonight's word (10). Illustrative:
- "That was your 6m 1 4 again."
- "Same move as before, a new key."
- "The bright 4: the D is doing it."
- "It leaned toward 1 and you went to 6m."
- "Your 4 wore a new colour: add9."

**Chooser**, first match wins:
1. A shelf shape (7.3) in a key he has not played it in tonight.
2. Tonight's word, heard in his playing.
3. A lean that landed, or a surprise.
4. A new exact colour on one of his five core numbers.

**Where.** On the glass, in the banner slot: 9:16 y 478-576, the slot the rarity banner borrows (spectacle D8).
- **Priority:** Legendary banner, then phrase card (Full mode), then rest card. At most one of them in any 60 s.
- **Narrow 9:16 and 16:9:** it takes the glass cue slot and yields to the CLAUDE chip, as the suggestion chips do.
- **REC:** never shown by default.

**Behaviour:**
- Fades in over 0.2 s. The next note-on fades it out over 0.25 s (the phrase card's timing).
- A click opens the matching Study entry or card.

**Rate:**
- At most one a minute.
- After three dismissals in a row with no click, rest cards pause for the session (Sunshine's retreat rule).

### 4.3 Study: reading after playing

**Where:**
- v1: chat, through `practice brief` and `riff`.
- Next: a **Study** view in the deck drawer (DOM, never recorded), built with the V2-B report cards (jam-spec 13.4).
- No new page.

**One screen**, top to bottom:

```
+-- TONIGHT, IN NUMBERS ----------------------------------------------+
| E♭ major                                                           |
| [ 1maj9 ][ 4maj13♯11 ][ 6m11 ][ 4maj9 ][ 5sus ][ 6m9 ][ 1 ] ...     |  core number bold, colour small; width = time
|   E♭maj9   A♭maj13♯11   Cm11                                         |  letters in grey under the numbers
|        ›             ·                    ›──●                       |  lean line: › lean, ● landed, · floated
| D♭ major  (new home: down a whole step)                             |
| [ 4maj9 ][ 5^11/4 ][ 1/3 ] ...                                      |
|                                                                    |
| YOUR SHAPES                                                        |
|   6m 1 4     played 13 times in 6 keys   [Hear yours] [Loop] [Keep] |
|   1 4 1      played 13 times in 5 keys   [Hear yours] [Loop] [Keep] |
|   4 → 5sus   played 15 times in 8 keys   [Hear yours] [Loop] [Keep] |
|                                                                    |
| TONIGHT'S WORD: the bright 4 · LYDIAN                               |
|   Try:    hold your 4 chord and move the top finger between C and D |
|   Notice: which one floats?                                         |
|   Name:   D is the ♯11; musicians call this colour Lydian            |
|   [Hear yours]  [Open the card]                                     |
|                                                                    |
| ONE QUESTION   Did the 5sus want to go home, or were you happy      |
|                letting it float?  [Hear] [go home] [float] [not sure]|
| ONE THING TO TRY   give the 5 its 3rd once, then land     [Try it]   |
|                                                                    |
| more: key map · borrowed and outside · colours by number · floor   |
|       (bass lines, pedal points) · other names for the same notes   |
+--------------------------------------------------------------------+
```

- **Source:** the numbers and counts come from `practice windows` and a key-free habits file (7.3). The shape counts shown are this file's measured examples from 1.4, not a mock of a session.
- **Question and try:** follow the riff rules (jam-spec 11.4) and the wording guard.
- **"more"** holds everything the audit moved: classes, modes, cadence names, pedal points, bass lines, and alternative readings shown as roof and floor ("Cm11 over A♭ = A♭maj13♯11: the same notes").

---

## 5. The reveal order

**The ladder orders the words, not what he may play.** He already plays material from every rung.

A rung "opens" when its theory names start to appear, in second position, in Rest and Study. Play gains almost nothing per rung, and that is the overload answer.

| Rung | The idea, plain | Theory names it unlocks | Play shows | Rest and Study add | His evidence (1.x) | Seed cards (jam-spec 12) |
|---|---|---|---|---|---|---|
| 1 Home | Which chord feels like arriving | tonic, key, the number 1 | the number row (today) | "you came home through the 4" | 1 is 24% of chord time; 4 → 1 29 times | 13 `db-opening`, 15 `open-ending-b7` |
| 2 Shapes | The same move sounds the same in every key | Nashville numbers, transposition | nothing new | shape shelf, "same move, new key" | 72 moves in ≥ 2 keys | 16 `white-keys`, card key selector |
| 3 Colour | The notes that make a chord lush, one at a time | 9, 11, 13, maj7, add9, #11, Lydian | nothing new (the chips show the notes) | "your 4 wears ..." | 25 core numbers wear 125 exact ones | 1 `lydian-four`, 4 `blooming-chord`, 3 `one-note-apart` |
| 4 Floor | The bass changes the name while the hands stay | slash chord, inversion, pedal point, upper structure | the slash in the name (today) | roof and floor, bass lines | not counted here (`practice colors` lists them) | 2 `gospel-five-over-four`, 6 `lament-bass`, 14 `held-sus-five` |
| 5 Lean and land | Some chords want to go somewhere | dominant, sus, resolution, cadence (plagal, authentic, deceptive) | **the lean and land mark** | lean line, landings | dominants with their 3rd 4% of chord time; 5 → 6m 11 times | 10 `float-or-pull`, 11 `lush-two-five-one`, 5 `half-step-slide` |
| 6 Borrowed | A shade from the minor key on the same home | borrowed, parallel key, modal colour, secondary dominant | the `outside` caption (today) | source named, "pulls to 6m" | about 5% of window time outside | 8 `borrowed-four-minor`, 9 `borrowed-b6-b7-home`, 17 `dorian-vamp` |
| 7 Doors | A chord that belongs to two keys lets home move | modulation, pivot chord, relative and parallel keys | the key caption changes (today) | "new home: down a minor third", the door chord named | 1-6 key areas per session; his hinges in `chord-suggestions.md` 1.3 | 7 `minor-third-drop`, 12 `sunrise-ending` |
| 8 Form | A piece has sections and returns | section, return, key plan | nothing | key map across the session | S1-S6 had 1-6 key areas | 12 `sunrise-ending` |

**Opening rule.** A rung opens on any of these:
1. He clicks "show me" on a Rest card or Study entry that belongs to it.
2. He asks about it in chat.
3. His playing contains the rung's thing at least 3 times across at least 2 sessions, and the rung below is open.

Rungs never close.

**On the first night**, rule 3 already opens rungs 1-3 from the log. Rung 4 opens as soon as the floor finding is counted (it is not counted yet). Rung 5 follows it at once, because the lean evidence is already in the log (1.5).

**Two settings:**
- **Names:** `plain | plain + names (default) | full`.
  - "Plain" hides theory names everywhere he reads.
  - "Full" shows every rung's names regardless of the ladder, for the nights he wants the whole map.
- **Just play** (4.1).

**Why this order:**
- **Home before shapes:** a number means nothing until 1 means home.
- **Shapes before colour:** his five core numbers carry 80% of his time (1.3), and his colours are variations on them.
- **Floor before lean:** his leans are mostly slash and sus shapes (1.2, 1.5), so the lean lesson needs the floor first.
- **Lean before borrowed:** borrowed chords are heard as "shade before home", which assumes home and lean.
- **Doors and form last:** they need everything above to make sense.

---

## 6. The words

### 6.1 Rules

1. **On the face of a mark, card, chip or fact:** a plain word, two words at most.
2. **The theory name comes second:** in small capitals, or in brackets after the plain words (the riff wording guard and the seed-card rule already require this).
3. **Never** "wrong", "mistake", "error", "should", "correct", "best", "score" or "%" (jam-spec 11.4). Also never "advanced", "beginner" or "despite" (Sunshine).
4. **Hedges when readings compete:** "one name for this", "we hear two homes".
5. **Counts, not percentages,** and only in Rest (at most one) and Study.
6. **Numbers are drawn with superscripts** as the overlay already draws them. `^`, `(no3)` and cost values never reach his surfaces.

### 6.2 One shared word list

Proposed as a shared fixture (`tests/fixtures/lexicon.json`, served to the page), owned the way the jam contracts are (jam-spec 13.1 rule 3). Every surface's wording receipt checks against it.

| Concept | Plain word (face) | Theory name (second) | Metaphor family | Meaning line (hover, Study) |
|---|---|---|---|---|
| The tonic chord | home | tonic, 1 | home / gravity | the chord that feels like arriving |
| 4-family chords | lift | the 4 chord (subdominant) | home / gravity | moves up and away from home |
| A 5 with its 3rd | pull | dominant | lean / land | leans hard toward 1; the 3rd is the note that pulls |
| A sus chord on the 5 | float | suspended dominant | lean / land | leans softly; it can hang without landing |
| 6m | shade | relative minor (6m) | light / shade | home's shadow: the same notes, a darker centre |
| 4 → 1 | soft landing | plagal cadence | lean / land | the "amen" arrival |
| 5 → 1 | arrival | authentic cadence | lean / land | the strongest landing |
| 5 → 6m | surprise | deceptive cadence | lean / land | sounds like home is coming, then shade |
| 9, 11, 13 on a chord | colour | extensions | light / shade | notes added on top that change the mood, not the job |
| #11 on the 4 | the bright 4 | Lydian 4, #11 | light / shade | the raised note that makes the 4 float |
| The bass under a chord | floor | slash chord, inversion | floor | the lowest note, which can rename the chord above it |
| A held bass under moving chords | held floor | pedal point | floor | one bass note under changing chords |
| A bass walking by step | walking floor | bass line | floor | the floor moves, the hands may stay |
| One chord shape over another bass | roof and floor | upper structure | floor | the same notes read from the bass or from the top |
| A half step inside a chord | rub | dissonance (minor 2nd) | rub / release | two neighbouring notes that shimmer or ache |
| A rub moving to rest | release | resolution | rub / release | the rub steps to a calm note |
| A phrase ending on colour or on the root | question, answer | open and closed phrase ending | breath / space | endings that ask and endings that answer (Heimdall 1.3) |
| A chord from the parallel minor | borrowed colour | borrowed from E♭ minor | light / shade | a shade from the minor key on the same home |
| A secondary dominant | pulls to 6m | secondary dominant (5 of 6m) | lean / land | a chord that leans toward a chord other than home |
| A chord outside the key and its parallel | far outside | chromatic | home / gravity | a note or chord from neither home key |
| One voice moving a half step | half-step slide | chromatic voice leading | rub / release | the smallest move on the keyboard |
| A key change | new home | modulation | home / gravity | home moves |
| The chord that belongs to both keys | door chord | pivot chord | home / gravity | the chord you walk through |
| The same notes, another home | same notes, other home | relative key | home / gravity | C major and A minor |
| The same home, the other mood | same home, other mood | parallel key | light / shade | E♭ major and E♭ minor |
| An alternative best-fit name | another name for the same notes | (the analyser's reading) | | replaces the word "reading" on his surfaces |

**Alignment with vocabularies already designed:**
- The suggestion reason words (home, your move, lift, surprise, pull, borrowed colour, slide, new key, stretch) all appear above with the same meaning. "Pull" there names secondary dominants. Here it also covers the 5 with its 3rd, which is the same idea.
- The riff classes (in the chord, colour, rub, outside) are unchanged.

### 6.3 Word conflicts found across the house

| Word | Meaning in one place | Meaning in another | Proposal |
|---|---|---|---|
| chromatic | `practice.py` class: in neither the key nor its parallel | seed card 12.5's theory name "chromatic voice leading": a half-step move; the suggestion word "slide" | Face words **far outside** and **half-step slide**. "Chromatic" appears only second, with its qualifier. |
| secondary dominant | spectacle 2.3 banner reason: `secondary dominant (leads to Dm)` (theory first) | riff and card rule: plain words first | `pulls to Dm · secondary dominant` |
| Lydian 4 | used as a plain word in cards and in `practice` text | it is a theory name | Face word **the bright 4**; "Lydian" second |
| reading | `practice` glossary: a best-fit name | not a musician's word | **another name for the same notes** |
| colour | riff class: a scale note that is not a chord tone | cards: extensions | One definition: "a note that belongs to the key and is not the chord's plain triad". Both uses fit it. |
| sharp eleven / #11 | banner reason word | chip label | Theory name, fine second; the face word is "the bright note" where a face word is needed |
| float / pull, question / answer, rub / release | card 10, Heimdall, Sunshine | | All kept, each for one layer: rub/release inside a chord, lean/land (float, pull) between chords, question/answer between phrases (section 8) |

---

## 7. Progressions as shapes across keys

### 7.1 What he already has

- **In the hands:** shapes anchored on black keys in E♭, D♭, G♭ and F#.
- **In the ear:** the sound of a move.
- **What he lacks is only the invariant.** A move that feels one way under the hands in D♭ and another in D is the same move. The number is the bridge, and 1.4 shows he already walks it.

### 7.2 Four encodings, quickest to deepest

| Encoding | What he sees | Where | Rung |
|---|---|---|---|
| **Number chips** | `6m 1 4` in every key | row, cards, chips (today) | 1-2 |
| **The home ladder** | each chord as a dot at the height of its root degree (1 at the bottom, 7 at the top, borrowed degrees between the lines), joined left to right, so `6m 1 4` is the same V-shaped line in every key | Study, cards | 2-4 |
| **The fifths ring** (Navi 2.4) | the degrees on a circle in fifths order, so a pull (5 → 1, 2 → 5, 3 → 6) steps one way and a soft landing (4 → 1) the other | Study, rungs 5-7 only | 5-7 |
| **The shape shelf** | named shapes from his own moves, each with "played N times in K keys", Hear yours, Loop (a jam card), Keep | Study, deck Kept | 2+ |

Two pictures, used at different rungs:
- **The ladder** comes first because it matches what the fingers do (scale steps). An ear player can read it with no theory.
- **The ring** waits until lean and land open, because its point is the direction of pull. Before that it is an abstract circle.
- **Neither uses pitch colour.** Pitch colours are his notes and change with the key, which is the opposite of an invariant. Shapes are drawn in the overlay's ivory ink.

### 7.3 Recognising a shape

- **Reading:** settled core numbers from the bass-aware reading (the suggestion engine's `readings.js`, `chord-suggestions.md` 2.2), in the key area.
- **What counts as a shape:** 3 or more chords in order that match a shelf shape, or a top habit that passes the "your move" gate (3 times across 2 sessions).
- **Habit source:** the suggestion design's key-free `habits.json`, which holds counts and numbers only, extended with 3-chord moves. No second builder.
- **Where it shows:** a Rest card ("same move, new key"), and an underline on the Study strip. Never a live mark in Play: recognising a shape takes three chords, and by then the moment to glance has passed.
- **Keys played in** comes from Study's key areas. The live tracker is not trusted for it (1.7).

### 7.4 Colour on top of shape

Study's "colours by number" shows each of his five core numbers with the colours it wore tonight, for example "your 4: maj13#11, maj9, add9, maj9#11". Two lessons at once:
- function and colour are separate axes;
- his signature is a colour on a common function, not a rare function.

The `blooming-chord` card is the hands-on version.

### 7.5 Turning two detection limits into lessons

- **Minor loops shown as the relative major (by design).** Numbering stays as it is. Study asks one question when the home-chord evidence is split: "which chord felt like home?", shown with both numberings side by side (the page already has the Minor setting: tonic or relative). The answer is the relative-key lesson.
- **Dorian vamps numbered in the key of the IV (known gap).** Until fixed, Study marks such a section "two homes heard" and shows no shape counts for it, rather than teaching a wrong shape.

---

## 8. Tension and resolution made visible

### 8.1 Four ingredients, shown separately

| Ingredient | What the ear hears | Detected from (existing code) | Play | Study |
|---|---|---|---|---|
| **Rub** (inside a chord) | two neighbours a half step apart, or a tritone: shimmer or ache | the sounding notes' intervals (`info.notes`) | nothing by default; option: a thin underline joining the two rubbing note chips | rub pairs listed with Hear; "the D rubs against the E♭: that is the bright 4's shimmer" |
| **Lean** (between chords) | the chord wants a particular next chord | the analyser's classes (secondary dominant); `nashville.js` DOMINANT set and cadence logic; spectacle `harmonicRole` rule for secondary dominants; sus chord on the 5 | **the lean and land mark** (8.2) | the lean line: leaned, landed, floated, surprised |
| **Distance** (from home) | outside the key | the diatonic flag; `practice` classes | the `outside` caption (today) | the source named in plain words |
| **Time** (how long before landing) | suspense | window durations | the chevron simply stays | "you let the 5sus float for 15 seconds" (card 14's wording) |

**Why no single tension meter:**
- A meter hides which ingredient is at work.
- His leans are sus floats as often as dominant pulls (1.5). A meter weighted on dominants would sit flat through his floating chords; a meter weighted on rubs would rise on every lush chord and teach "lush = tense".
- A meter is also a score-shaped object (P9).

### 8.2 The live lean and land mark

**When:**
- The settled, bass-aware reading is one of these lean kinds:
  - a dominant-type chord with its 3rd (**pull**);
  - a sus chord on the 5, or a 7sus4, 9sus4 or 13sus4 over the 5 bass (**float**);
  - a secondary dominant (**pull to X**);
  - a diminished passing chord (**slide**).
- The key is "sure" or "fair", locked, or the jam key.
- The chord has been settled for 0.5 s.
- The tracker is not holding a pending key change (`keyView.candidate` is null). This keeps backdoor dominants and the I-I7-IV case out until 11.7 is fixed.

**Look:**

| Kind | Mark after the number | Example |
|---|---|---|
| Pull | a solid chevron `›` | `5⁷ ›` |
| Float | an open chevron `›` at 0.62 alpha, dotted underline | `5sus ›` |
| Pull to X | chevron plus the target number, small | `3⁷ › 6m` |
| Slide | chevron plus a half-step tick | `♯4°7 ›` |

**Land.**
- **What counts:** the next settled chord is the target.
  - For a pull or float: the chord a fifth below (normally 1), or the sus resolving to its 3rd.
  - For a pull to X: X.
  - For a slide: the chord a half step up.
- **What happens:** the new number pulses once in size (1.0 → 1.08 → 1.0 over 200 ms), never in brightness (the house rule for `found`). The chevron fades.

**Surprise:** it leaned, then another chord came. The chevron fades with no pulse. The Rest chooser may name it ("it leaned toward 1 and you went to 6m").

**Budget:** one chevron at a time. None while busy. None in the first 90 s.

**Surfaces:**
- **Default:** glass, projected over the Nashville row's box.
- **Opt-in "also in recordings":** the chevron is drawn in the Nashville layer after the number. While a rarity banner holds that slot (spectacle D8), the chevron hides with the row.

**Honesty:** only these rule-based leans; no probabilities, no "tension score".

### 8.3 Study: the lean line

The Study strip (4.3) carries one lane under the chords: `›` where a chord leaned, `●` where it landed on its target, `·` where it floated to the end of its window, a break where it surprised.

- **Counts line:** "leaned 9 times: landed 3, floated 4, surprised 2". Illustrative; each number is a field in the JSON.
- **Phrases:** one more line pairs phrase endings as question (landed on colour) or answer (landed on the root), from the riff landings (jam-spec 11.3 step 7). This is Heimdall's question and answer pair, read from his own playing.

### 8.4 Games that teach it (links, nothing new)

- **Card 10 `float-or-pull`:** the growth edge (1.5), heard as a, b and c.
- **Card 11 `lush-two-five-one`:** the pull in his colours, with its falling half steps.
- **Sunshine's Tension Tokens:** a Rest card can offer it after a session with three or more floats.
- **Heimdall's question and answer pair cards:** Keep, run on the lean line.
- **The suggestion STRETCH "let the sus land":** `chord-suggestions.md` 6, second case.

---

## 9. How it links to cards, suggestions and riff reports

One moment of his playing can open four doors, and every door uses the same words and the same counts.

| Surface | Role in learning | What this design adds to it | What it takes from it |
|---|---|---|---|
| Page canvas (label, chips, number row) | the mirror | the steady-name setting, the bass-aware number, the lean and land mark (glass by default) | nothing |
| Suggestion chips | the door while he holds a chord | reason words from the shared list. Rung-aware stretch: the STRETCH slot prefers a candidate from the lowest unopened rung (a pull before a borrowed chord) | the `readings.js` twin, `habits.json` and the rest detector |
| Rest card | the notice | new: 4.2 | the banner slot and its priority with the spectacle spec |
| Jam cards | the playground | a rung → card map (section 5 table); "tonight's word" opens its card; **Keep this shape** makes a `moves` card through the existing template route (DATA 2.10, suggestions 5.2) | card text already follows the plain-word rule |
| Riff report (chat in v1, card in v2) | the conversation | two talking-point types proposed to the riff lane: **shape** ("your 6m 1 4, in its sixth key") and **lean** ("leaned 9 times, landed 3"), under the salience rules of jam-spec 11.4 | the three facts, one question and one try layout that Study reuses |
| Rarity banner and phrase card | the celebration | reason words aligned to 6.2; a phrase-card fact "a shape in a new key" when it applies | the slot and the gate |
| `practice` verbs in chat | Claude's side | the glossary chooses words at or below his open rungs, plus tonight's word | `GLOSSARY`, `brief` |
| Key lights (later) | the hands | nothing: lean marks are about chords, not keys, so no light mapping is proposed | |

**One evidence rule.** Every count in a rest card, Study fact, "your move" chip and riff point comes from one of two JSON sources:
- `habits.json`, for moves across sessions;
- the riff or windows JSON, for tonight.

So the same move shows the same number everywhere.

---

## 10. Overload guards

| | Play | Rest | Study |
|---|---|---|---|
| New learning marks | at most 1 per harmonic gesture; none while busy | 1 card, ≤ 12 words, ≤ 1 per minute | everything, behind "more" after the first screen |
| Text that changes while notes sound | the chord name only (and it can hold per gesture) | none (a note-on dismisses the card) | none |
| Numbers and counts | never | at most one | yes |
| Theory names | never new | only tonight's word | second position; rungs at or below open ones, unless Names is `full` |
| During REC | today's canvas only, unless opted in | never, by default | not on the canvas |
| Off switch | Just play | Just play; pauses itself after 3 ignored cards | the drawer stays closed until he opens it |

**Session-level rules:**
- **One new theory word per session.** Chosen from his playing, anchored to one Hear-able moment, taught Try → Notice → Name. Old words are free to repeat.
- **No manufactured findings.** A night with nothing to say shows nothing: "just let it be music" (Sunshine).
- **Advance by desire, retreat at once.** A rung opens on his click or his playing (section 5). When a Rest card is ignored three times, the page goes quiet.

---

## 11. What detection must fix first, for the teaching to be honest

In priority order. Each row names the wrong lesson it teaches today.

| # | Fix | Wrong lesson today | Where it is designed or owned |
|---|---|---|---|
| 11.1 | The Nashville row uses the bass-aware reading, or THEORY gains `maj9#11`, `maj13#11` and `13sus4` | "your bright 4 is a 6m": 116 of 119.6 s of Lydian-4 time (1.2) | `readings.js` twin (`chord-suggestions.md` 2.2); V2-F names (jam-spec 13.4) |
| 11.2 | A per-gesture name commit, as a setting | the name can be seen and not read (1.1) | spectacle P1 `harmonySet` and the event tracker (4.2): reuse it, do not build a second one |
| 11.3 | Name the sus-5 family as 5 chords over the 5 bass (9sus4(13), 13sus4) ahead of 2m9/5, 4maj7/5 and 1add11(13)/5 | "the float is a 2 or a 1": it hides his main tension (1.2, 1.5) | THEORY templates and the analyser's reading costs |
| 11.4 | Dominant 11 in the analyser's readings | "a 5 chord over its root is a Lydian 4" in riff and Study text | `practice.py` (known follow-up in `de1334bf`) |
| 11.5 | Secondary dominants named as such, not "chromatic" | "a pull is an outsider" | `performance.py` (known follow-up in `5cff2c61`) |
| 11.6 | A chord from the old key at a key change named as the door chord, not "borrowed" in the new key | "the door is a borrowed chord" | `practice.py` (known follow-up in `de1334bf`) |
| 11.7 | Backdoor dominant (C C7 F Bb7 C reads as F major); I-I7-IV with a long IV; Dorian vamps numbered in the key of the IV | shapes counted in the wrong key; a lean marked toward the wrong home | `nashville.js`, `performance.py`. Until fixed, lean marks stay off while a key change is pending (8.2) and Study marks such sections "two homes heard" (7.5) |
| 11.8 | Aeolian loops as the relative major (by design) | none, if Study asks the home question (7.5) | no change to detection |

---

## 12. Build shape (for after the jam build lands)

Design only. `piano.js`, `piano.html` and `piano.css` belong to the jam build (J9) and are not touched here.

| Step | Scope | Files (new unless marked) | Exit |
|---|---|---|---|
| T0 Contracts | `lexicon.json` (6.2), the lean-rule table, the rest-card chooser's evidence fields, rung state schema | `tests/fixtures/lexicon.json`, `tests/fixtures/teach/*` (through the conductor) | fixtures validate; wording receipt W1 runs on the seed deck text |
| T1 Names | 11.1 and 11.3 with the V2-F owners; 11.4-11.6 with the practice and performance owners | owners' files, per jam-spec 13.4 | W3 |
| T2 Pure teaching module | `teach.js`: lean and land rules, shape matcher over settled readings, rest-card chooser, rung state; node-tested like `nashville.js`; the gesture commit reuses the spectacle event tracker | `arsenal/web/piano/teach.js`, `tests/teach.test.mjs` | W2, W4, W5 |
| T3 Study data | `practice study` (delegated module, 3-line registration, the `riff` pattern): tonight's strip, shapes, lean line, word of the night; habits builder extended to 3-chord moves | `arsenal/practice_study.py`, habits builder (suggestions S1 owner) | JSON fields for every number in 4.3 |
| T4 Surfaces | the glass lean mark and rest card; the Study tab in the deck | `glass.js` (J8's file) and `deck.js` (V2-B's), sequenced after suggestions S4 and V2-B | W6, W7 |
| T5 Integration | settings (Chord name, Names, Just play, lean mark in recordings) and the render hooks | `piano.js`, `piano.html`, `piano.css`, in their own integration step after J9 | W6-W7 on the page |
| T6 First night | Daniel plays 10 minutes, then reads Study | none | W8 |

Rung state lives in `state/arsenal/jam/teach/rungs.json` (git-ignored), with a localStorage fallback. It never adds an event kind to the practice log, because `performance.validate_event` refuses unknown kinds and drops the whole batch (`chord-suggestions.md` 2.9).

---

## 13. Checks before calling it built

| # | Check | Pass |
|---|---|---|
| W1 | **Wording:** every string he can see (canvas, glass, rest cards, Study, cards, chips, riff render, banner reasons) against `lexicon.json` | 0 forbidden tokens; 0 theory names in first position; 0 `^` or `(no3)` on his surfaces; each rest card ≤ 12 words |
| W2 | **Play budget:** synthetic replays in the style of S1-S6 (note-gap and pedal profile, no real content) through detect, the tracker and `teach.js` | lean marks while busy: 0; marks per gesture ≤ 1; rest cards per minute ≤ 1; the receipt reports label changes per minute with gesture commit on vs off (1.1 is the baseline) |
| W3 | **Honest numbers:** the 1.2 voicings and 40 synthetic Lydian-4 and sus-5 voicings across 12 keys | the number row shows 4 for every Lydian 4 and 5 for every sus 5 (or the chip shows a "screen calls this" line); 0 silent mismatches |
| W4 | **Shapes are key-free:** 40 synthetic progressions × 12 keys | identical shape ids, ladder and ring pictures, and counts in all 12 keys |
| W5 | **Lean rules:** a fixture of V7→I, sus→I, 5→6m, secondary dominants landing and not landing, a backdoor dominant, and I-I7-IV with a long IV | exact marks and land pulses; 0 marks while a key change is pending |
| W6 | **Recording:** REC with every teaching default on, against teaching off | recorded frames MAE 0 (suggestions S4, jam A5 method) |
| W7 | **Isolation:** 60 s of rest cards, lean marks and Study clicks | `sounding`, log events, tracker histogram and rarity inputs unchanged |
| W8 | **First night:** 10 minutes of play, then the Study screen | Daniel says which marks he noticed, which he never looked at, one rest card he liked or disliked, and whether each Study fact matches his memory; his answers go to `state/arsenal/jam/riffs/` |

---

## 14. Questions for Daniel (three, each with a default)

1. **While you play, should the big chord name hold still for each chord you mean, and skip the in-between names of a roll or a run? Or keep reacting to every note, like now?**
   - **Default: unchanged until you try both.** On the first night we switch between them for a few minutes and you pick.
   - The notes under the name keep updating either way.
2. **Would you like a small arrow after the number when a chord wants to go somewhere, with a tiny pulse when you land where it wanted?**
   - **Default: yes, for practice only, never in your recordings** unless you turn it on.
3. **After you play, where would you rather read about what you did: a Study screen in the cards drawer, or chat?**
   - **Default: both.** The page shows tonight in numbers, your shapes, one question and one thing to try. Chat is where we banter about it.

---

## 15. For Vandor, not for Daniel

- **Label versus function is the gating fact.**
  - 24.5% of chord time disagrees at the core number.
  - The Lydian 4 shows a 4 for 3.5 of 119.6 s.
  - Land 11.1 (or V2-F) before the lean mark and rest cards go live. Otherwise the new teaching repeats the wrong family with more confidence.
- **Word conflicts (6.3)** span `practice.py` (the `chromatic` class), seed card 12.5 (`chromatic voice leading`) and the spectacle reason vocabulary (`secondary dominant (leads to Dm)`). A single `lexicon.json` through the J0 contract owner would settle them. The seed deck text only needs "Lydian 4" moved to second position where it appears as a face word.
- **Slot sharing.** The rest card uses the banner slot on the glass. The rarity banner and phrase card own it on the canvas (spectacle D8, still open as Q1). The priority rule in 4.2 needs the spectacle owner's agreement.
- **S3's live chord events** run at 25 changes a minute against 73-234 in the other sessions. That fits the covered-tab gap in `5cff2c61` (unverified). Summaries built from that session's live chord events may undercount; the windows (rebuilt from notes) are unaffected.
- **Counting differences from `chord-suggestions.md`:**
  - Dominant-with-3rd time is 67.4 s here against about 35 s there: this file counts every dominant-type suffix with its 3rd, and that file counts qualities 7, 9 and 13.
  - Move counts differ because this file counts chords only, merges repeats and stays inside key areas.
- **Not measured:** the share of his time on slash chords and pedal points (rung 4's evidence cell); whether a per-gesture name reads as less alive on video (question 1 decides); the ladder thresholds and rest-card rate (W8 tunes them).
- **Nothing is removed.** Every change in section 3 is a setting or a new surface, and today's canvas stays the default for recordings (the "ask before deleting functionality" rule).
- **Privacy check done.** This file holds no session ids, clock times or transcriptions. The windows JSON for S1-S6 and the measurement outputs stay in the scratchpad (`theory-nextgen/`). S1-S6 are the six sessions, oldest first by local start time.
