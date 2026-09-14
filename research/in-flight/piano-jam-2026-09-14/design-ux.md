# Piano jam: the UX (concept deck, lead-sheet strip, ghost keys, riff report)

Status: design, 2026-09-14. Design only: nothing in `arsenal/` was edited, no server or browser was started. This file is
the UX half of the jam round; the card protocol, the verbs and the theory behind a card's text are for the sibling
designs to settle, and where this file needs something from them it says so as a requirement, not a decision.

Daniel, verbatim, tonight:
> "I want us to be able to play in this space, can you make verbs so you can play chord progressions or show loops of
> chords for me to try, I can then riff on that and play with it and we can discuss it"
>
> "so I can click and hear concepts you are describing and have a visual for them, we can make chord templates"
>
> Earlier: "ooooh, can we make a verb for you to be able to play a chord you are curious about or hovering it in the
> viewer?" / "We could have a lot of fun with this!" / "I just play it by feel" / "I know a little bit but not much >__<
> this is intuition and memory"

**Who the UX is for.** A gifted ear player: harmonically advanced, technically intermediate, a beginner at theory names.
Plays in E♭, F, D, G♭ and D♭; lush maj9/m11/13/6-9 voicings over about 2.5 octaves; pedal down most of the time; soft
dynamics with real arcs. So:
- **Sound first, words second.** Every card is one click from being heard. Theory names ride along in small type next
  to plain words, so the names get learned by exposure, never as a gate.
- **His hands are on 88 keys.** Anything he needs mid-phrase cannot need the mouse. The computer keyboard is second
  best; learnable KeyLab pads are the real answer (phase J5).
- **No grades.** A report says what he did and asks why. It never scores a pass, never says "wrong". Outside notes are
  "outside", colour notes are "colour" (the spectacle spec's honesty vocabulary, section 2.3).

**What was read for this design:** `arsenal/web/piano.js` (LAYOUT, overlay, keys, camera, keydown, KEYMAP),
`piano.html`, `piano.css`, `arsenal/web/piano/cues.js`, `arsenal/pianocue.py`, `arsenal/pianocue_voicing.mjs` (header),
`arsenal/practice.py` (findings and CLI), `arsenal/PIANO-V2-SPEC.md`,
`research/in-flight/piano-spectacle-2026-09-13/spectacle-spec.md` (all of it), the ideas panel's conversation rules, and
the two cue receipts (`1-hover.png`, `2-playing.png`). The integration notes named in the brief were not at that
scratchpad path when this was written.

**Privacy.** `research/` is committed to a public repo. Every time, session and moment in this file is a placeholder.
Cards that cite his log, jam records and reports live under `state/arsenal/` (git-ignored) and never leave the machine.

---

## 0. The system in one screen

1. **The deck** is a drawer on the right of the stage (inside `.stage`, so it survives fullscreen), outside the recorded
   canvas. Claude publishes **cards** into it live. A card is a concept you can hear: a title in plain words, one line of
   meaning, the chords in letters and numbers, a key and a tempo, and five buttons: **Play, Show, Loop, Try, Hear me**.
2. **Two surfaces.** The **stage** is the canvas (it is recorded). The **glass** is a transparent layer exactly over it
   (never recorded). Everything Claude adds (its lit keys, ghost keys, the lead-sheet strip, marks on Daniel's notes) is
   drawn on one or the other. **Jam view** picks which: `auto` (default) puts it on the stage while not recording and
   on the glass while recording, so live play looks like a duet and a take stays 100% Daniel unless he chooses `stage`.
3. **One transport.** Loop and Try run on one bar clock with a count-in. Launches and changes land on the next bar line,
   like clips in a DAW's session view. The lead-sheet strip (NOW chord, NEXT chord, bar, beat pips, loop name, key)
   lives in the deck header, becomes a pill when the deck is closed, and is drawn in-frame only in jam view `stage`.
4. **Four identities on the keys.** Daniel live: his pitch colours, trails, sparks (unchanged). Claude played:
   moonlight silver, lighter touch, no trails. Ghost (a target): a moonlight rim with a faint breathing fill. Daniel
   replayed: his pitch colours, desaturated. Pitch colour stays his alone.
5. **Claude never interrupts a phrase.** A sound Claude sends from the terminal waits for a rest; if none comes it
   becomes a **knock** (a pulsing button he can take or leave). His own clicks act at once.
6. **The discussion loop.** Stopping a jam keeps a **jam record** (card, key, tempo, bar clock, when). One click asks
   Claude about it. Claude publishes a **riff report card**: the loop as a lead sheet with his top notes under it as
   degrees, at most three facts, one question anchored to a moment he can hear, one thing to try as a new Try card, and
   answer chips (on purpose / by ear / not sure) that write back to the card.
7. **Templates.** Any card can be **kept** (copied into his own group, editable), and **Keep what I just played** turns
   his last phrase (exact voicings, from the page's own chord commits) into a card Claude can then name and discuss.

---

## 1. Words used in this file

| Word | Meaning |
|---|---|
| Stage | The WebGL canvas. What is on it is what REC records |
| Glass | `#jam-glass`, a 2D canvas with the canvas's exact CSS box, `pointer-events: none`, never recorded |
| Deck | The drawer that lists cards |
| Card | A published concept: title, meaning, chords, key, tempo, actions. Kinds: `concept`, `report`, `kept` |
| Transport | The one bar clock that runs a Loop or a Try |
| Pass | One time through a card's chords while looping |
| Ghost | A key shown as a target without being pressed or sounded |
| Claude's hand | Notes Claude sounds (cue `source: "claude"`) |
| Replay | Notes rebuilt from Daniel's log (cue `source: "replay"`) |
| Rest | 1.2 s with none of his notes sounding, or 3.0 s with no note-on while only pedal-held notes ring (the spectacle spec's phrase rest, reused) |
| Knock | A held Claude action shown as a pulsing button instead of sounding |
| Jam | One run of the transport, from start to stop, with Daniel playing or not |
| Jam key | The key the Nashville row counts from while a card action runs (the card's key) |
| Backing style | How Loop voices a card: `full`, `comp` (bass + shell, top register left free), `bass`, `pad` |

---

## 2. Page layout

### 2.1 Where the deck sits

The deck is `position: absolute; top: 0; right: 0; bottom: 0; width: 380px` inside `.stage` (z-index 3, the HUD's
level; the toast stays z 4 and moves to `right: 392px` while the deck is open). It lives inside `.stage` because
`.stage` is the fullscreen element; anything outside it disappears in fullscreen.

**Overlay or dock**, decided on open, on resize and on framing change:
- Let `margin = (stage width - canvas CSS width) / 2`.
- `margin >= 392 px`: **overlay**. The deck floats in the black margin; nothing reflows. This is the usual 9:16 case on a
  landscape monitor (a 2560x1440 window leaves margins of about 890 px).
- Otherwise, and not recording: **dock**. `fitCanvas()` subtracts the deck width from the stage width, so the canvas
  refits beside the deck. This is the usual 16:9 case, where the staff sits at the right and an overlay would cover it.
- Otherwise, while recording: **overlay**, never a reflow mid-take. The deck gets a "peek" button that slides it to a
  44 px rail.

Closed, the deck is a 28 x 120 px tab on the stage's right edge, vertically centred, reading `CARDS` rotated, with a
count badge for unseen cards.

### 2.2 Wireframe A: 9:16 on a landscape monitor, deck open (overlay)

```
+-- topbar (unchanged: MIDI in, Demo, framing, Colour, Rec audio, REC, Numbers, Minor, Key, Practice log) -------------+
+-----------------------------------------------------------------------------------------------------------------------+
| +HUD------+                     +-- canvas 9:16 (stage) --+ <- glass sits exactly on this box                         |
| | fps 240 |                     | . . TikTok header . . . |                              +-- DECK 380 ---------------+ |
| | key  Eb |                     |                         |                              | NOW  (transport, 5.2)     | |
| +---------+                     |        Ab maj9#11       |                              | LOOP Lament bass . Db 66  | |
|                                 |     Ab C Eb G Bb D      |                              | o . . .  bar 3/4  [Stop]  | |
|                                 |   4maj9#11  IN Eb MAJOR |                              +---------------------------+ |
|                                 |  ====== staff ======    |                              | [ Find a card...        ] | |
|                                 |  ====== staff ======    |                              | Tonight 3 | Moves 9 | ... | |
|                                 |  Ped.                   |                              +---------------------------+ |
|                                 | [strip: jam view stage] |                              | > The Lydian 4 chord      | |
|                                 |    | | columns | |      |                              | > Walking bass, held chord| |
|                                 | ==== rail ============= |                              | v The sunrise ending      | |
|                                 | [][][] keys, ghosts [][]|                              |   (expanded card, 4.1)    | |
|                                 | (pill when deck closed) |                              |                           | |
|                                 +-------------------------+                              +---------------------------+ |
+-----------------------------------------------------------------------------------------------------------------------+
```

### 2.3 Wireframe B: 16:9, deck docked

```
+-- topbar ------------------------------------------------------------------------------------------+
+----------------------------------------------------------------------------+-- DECK 380 -----------+
| +-- canvas 16:9, refit to (stage width - 380) -----------------------------+ | NOW                  |
| | Bb m11 /Gb                                  ===== staff =====            | | ...                  |
| | Bb Db F Ab C Eb                             ===== staff =====            | | [ Find a card...  ]  |
| | 6m11/4  IN Db MAJOR                         [strip, jam view stage]      | | tabs                 |
| |                  | | | | trails | | | |                                  | | cards                |
| | ======================== rail ========================================= | |                      |
| | [][][][][][][][][][][][][] 88 keys [][][][][][][][][][][][][][][][][][] | |                      |
| +--------------------------------------------------------------------------+ |                      |
+----------------------------------------------------------------------------+-----------------------+
```

---

## 3. The deck

### 3.1 Anatomy (top to bottom)

```
+-- DECK -----------------------------------------------+
| NOW ................................................. |  transport header, 5.2 (96 px, grows to 132 in a jam)
|  Claude's hand: listening . voice ready        [...]  |  [...] = deck settings (3.6)
|  last: Em  3m in C major               [Keep as card] |
+-------------------------------------------------------+
| [ Find a card: name, chord, number (4maj, sus, lament) ] 40 px
+-------------------------------------------------------+
| Tonight 3 | Your moves 9 | Try this 4 | Kept 2 | All  |  36 px, segmented
+-------------------------------------------------------+
|  ( 2 new cards  - show )                              |  appears only while he is playing (3.3)
| ┃NEW The sunrise ending                     Eb  72    |  collapsed card, 88 px
| ┃    Minor home, lift to its relative major, land     |
| ┃    in the major home.                               |
| ┃    Ebm9 > Gbmaj9 > Ebmaj9     1m9 > b3maj9 > 1maj9  |
|                                                       |
|  The Lydian 4 chord ...                    (expanded) |  one card expanded at a time (accordion)
|  ...                                                  |
+-------------------------------------------------------+
```

Style: piano.css tokens (`--panel`, `--rule`, `--ink-2`), Archivo for titles, JetBrains Mono for tempo, bars and
times, real flats and sharps in chord names (Noto Music glyphs, as the canvas label), numbers with the suffix as
`<sup>` (`4<sup>maj9♯11</sup>`, `5<sup>7sus4</sup>/1`) so the DOM reads like the canvas row. One new token:
`--claude: #C8DCFF` (moonlight), the same colour Claude's hand has on the keys (6.1), used for Claude-owned UI only
(NEW bars, knocks, the Now header's "Claude's hand" dot). Amber stays the page accent; gold stays Legendary's.

### 3.2 Groups

| Tab | What is in it | Order |
|---|---|---|
| **Tonight** | Cards Claude published in this page session or the last 12 hours, including riff reports | Newest first |
| **Your moves** | Cards about things he already does, each citing moments from his log | Claude's order (a `rank` field), pinned first |
| **Try this** | Ideas he has not played yet: the growth edge (a real V7 with its 3rd, tension and release) | Claude's order |
| **Kept** | His templates: cards he kept, and phrases he captured (4.6) | Last used first |
| **All** | Everything, grouped under small headers | By group |

Default tab on page load: Tonight if it has a card from the last 12 hours, else Your moves. The last tab used is
remembered (`localStorage arsenal.piano.deck.tab`, try/catch).

### 3.3 New cards

- **Deck open, Daniel idle** (no note-on in the last 5 s): the card slides in at the top of its group (180 ms), gets a
  3 px `--claude` bar on its left edge labelled `NEW`, scrolls into view and is selected (not expanded). If its group
  is not the current tab, the tab's count badge ticks up and pulses once.
- **Deck open, Daniel playing:** nothing moves under his mouse. A pill `( 2 new cards - show )` appears at the top of
  the list; clicking it (or the next rest, if he never clicks) inserts them.
- **Deck closed:** the closed tab's badge ticks up; a quiet line appears under the toast position for 6 s:
  `Claude added a card: The sunrise ending  [Open  A]`. No sound, ever, for a new card.
- `NEW` stays until the card is expanded or any of its actions is used. Seen ids are kept in
  `localStorage arsenal.piano.deck.seen` (capped at 500).
- **An updated card** (Claude republished it with a higher `rev`) shows `updated` in `--ink-2` instead of `NEW`. If its
  loop is running, the change lands at the top of the next pass, and the strip says `updated . next pass`.

### 3.4 Search

- One input, filtering as he types across title, meaning, theory name, tags, chord names in the card's shown key, and
  numbers. `4maj` matches `4maj9♯11`; `Ab` matches chords spelled A♭ in the key currently selected on that card;
  `sus` matches `sus2`, `sus4`, `7sus4`; words match tags (`lament`, `gospel`, `borrowed`).
- Accidentals typed as `b`/`#` match `♭`/`♯`.
- Empty result: `No card matches. Ask Claude for one in chat.`
- Focusing the input turns computer-key notes off (the page's handler already skips INPUT targets); `Escape` in the
  input clears it and blurs.

### 3.5 Keyboard shortcuts

The page already uses: `H` HUD, `F` fullscreen, `Space` sustain, `←` `→` octave, and as notes (by physical key) Z S X
D C V G B N J M , L . ; / Q 2 W 3 E R 5 T 6 Y 7 U I 9 O 0 P. The spectacle spec takes `` ` ``. The handler ignores
events with Ctrl, Meta or Alt, and events whose target is an input or select. The free keys used here:

| Key | Action |
|---|---|
| `A` | Open or close the deck (focus stays on the page, so computer keys keep playing) |
| `↑` `↓` | Select the previous or next card in the list |
| `Enter` | **Play** the selected card |
| `K` | **Show** or hide the selected card's ghost keys (K for keys) |
| `\` | **Loop** on or off (launches on the next bar line if a jam is running) |
| `'` | **Try** (count-in, then ghosts in time) |
| `Shift` + `Enter` | **Hear me**: replay the card's first cited moment |
| `-` `=` | Transpose the selected card down or up a half step |
| `[` `]` | Tempo down or up 4 bpm (applies at the next bar) |
| `Esc` or `Backspace` | **Stop Claude**: stop the transport, dismiss ghosts, silence any cue (a local clear) |

- `Space` is never transport: it is the sustain pedal on the computer keyboard, and a DAW habit must not lift it.
- `Backspace` exists because Chrome takes `Esc` to leave fullscreen before the page sees it.
- A repeat (`e.repeat`) never re-triggers an action.
- Pre-existing conflict to flag, not introduced here: PIANO-V2-SPEC gives `S` to the scheme picker in piano-next, and
  `KeyS` is also C♯3 in `KEYMAP`.

### 3.6 Deck settings (the `[...]` in the Now header)

| Setting | Values | Default | Stored as |
|---|---|---|---|
| Jam view | auto / stage / glass (section 7) | auto | `arsenal.piano.jam.view` |
| Claude's voice | built-in / MIDI out to a port / both | built-in | `arsenal.piano.jam.voice` (port id in `.midiOut`) |
| Claude volume | 0-100 | 70 | `arsenal.piano.jam.volume` |
| Duck Claude when I play | on / off | on (Loop and Try; never Play) | `arsenal.piano.jam.duck` |
| Loop backing style | full / comp / bass / pad | comp | `arsenal.piano.jam.backing` |
| Try mode | in time / wait for me | in time | `arsenal.piano.jam.try` |
| Try backing | ghosts only / with bass / with loop | with bass | `arsenal.piano.jam.tryBacking` |
| Count-in | 0 / 1 / 2 bars | 1 | `arsenal.piano.jam.countIn` |
| Ghost labels | off / letters / degrees | degrees for Show, off in Try | `arsenal.piano.jam.ghostLabels` |
| Marks on my notes | off / quiet / teach (6.4) | quiet | `arsenal.piano.jam.marks` |
| Let Claude knock while I play | on / off | on | `arsenal.piano.jam.knock` |

All reads and writes through `safeGet` / `safeSet`, as the page's other settings. Query overrides for receipts, never
persisted: `?jam=auto|stage|glass`, `?deck=open`.

---

## 4. The card

### 4.1 Expanded card

```
+----------------------------------------------------------------+
|┃ The Lydian 4 chord                              YOUR MOVE    |  title (Archivo 700, 17 px) . group tag
|┃ The 4 chord with its raised 4th on top: it floats instead    |  meaning: one line, two at most
|┃ of landing.                                   theory: Lydian |  theory name, small caps, --ink-3
|                                                                |
|   +-------------+    +-----------+                            |  chord chips: hover = ghost, click = hear
|   | Ab maj9#11  |    | Eb maj9   |                            |  name (letters)
|   | 4 maj9#11   |    | 1 maj9    |                            |  number (superscript suffix)
|   |  4 beats    |    |  4 beats  |                            |
|   +-------------+    +-----------+                            |
|   your screen names the first one Cm9/Ab: the same notes      |  "reads as" line, only when the page differs
|                                                                |
|   Key [ Eb v ]   Tempo [-] 72 [+] bpm  [tap]   bars 2 . 4/4    |
|                                                                |
|   [ Play ]  [ Show ]  [ Loop ]  [ Try ]  [ Hear me at 5:22 ]   |  actions (4.2)
|                                                                |
|   You played this at 5:22, 18:40 and 31:10 tonight.  [more]   |  moments (4.5)
|   Why it works  v                                              |  collapsible: 2-3 sentences with his notes
|   [Keep]  voicing [ spread v ]  rolled [ ]   [...]             |
+----------------------------------------------------------------+
```

- **Title** in plain words, never a theory name alone ("The Lydian 4 chord", "The gospel 5 over 4", "Blooming
  chord", "Walking bass under a held chord", "The sunrise ending").
- **Meaning**: one line, what it does to the ear, in his register ("floats", "cloudier sky", "churchy, wants to fall
  home").
- **Theory name**: optional, small caps, muted. This is where names get learned.
- **Chord chips**: the chord name in the selected key, its Nashville number, its length in beats. Numbers never change
  when the key changes; that is the point of numbers, and the card says so the first time he transposes
  (`numbers stay the same in every key`, a one-time hint).
- **Reads-as line**: when `pianocue_voicing.mjs` reports a round trip other than `exact` (`roundtrip.page_name`), the
  card says what the canvas will call it, so the label never surprises him. The page's TEMPLATES has no `maj9#11`, for
  instance, so his Lydian 4 chord reads as a slash chord on screen.

### 4.2 The actions

| Action | Sound | Keys | Canvas label and number row | Ends |
|---|---|---|---|---|
| **Play** | Claude's voice plays the card once, at its tempo, block or rolled | Claude's hand (6.1), on the stage or the glass per jam view | Stage: named as if played, with a small `CLAUDE` caption in the chips line; numbers count from the card's key. Glass: the label stays Daniel's; the Now header names Claude's chord | After the last chord's hold |
| **Show** | none | Ghosts of the selected chord (the first, or the chip he clicked last), held | Unchanged; the Now header reads `SHOWING Ab maj9#11 . 4maj9#11 [Dismiss]` | `K` again, Dismiss, Stop, or another Show |
| **Loop** | The card's chords round and round in the backing style (comp by default: bass and shell under C4, top register left free for him) | Claude's hand for the backing notes | As Play while he is silent; while he plays, the label names what sounds (section 7) | Stop, `\`, or another Loop (swaps at the next bar) |
| **Try** | Count-in clicks, then the Try backing (with bass by default) | Ghosts of the current chord in time, the next chord's ghosts on the last beat (6.3) | His notes as always; numbers from the card's key | Stop or `'` |
| **Hear me** | His own logged notes for that moment (a `replay` cue), at 1x | Daniel replayed (6.1) | Stage: named, with `YOU . 5:22` in the chips line | End of the moment (8 s default) |

- **Chord chips are instruments too.** Pointer over a chip for 250 ms: ghosts of that one chord while the pointer stays
  (silent; this is "hovering it in the viewer"). Click: hear that one chord (a Play of one chip). Shift-click: Show that
  chip (ghost held).
- A click on any action is a user gesture, so it unlocks Claude's voice (`createClaudeVoice.unlock`) before it plays:
  the first click always makes sound. Until the first gesture the Play button carries a small `needs a click` note.
- Buttons `blur()` after a click, as the page's selects do, so the next computer key plays a note instead of pressing
  the button again.
- When the Demo is running, Play, Loop and Try stop it first, with a toast.

### 4.3 Key selector

```
Key [ Eb v ]
     +---------------------------+
     | as written      Eb        |
     | my key now      Db  (auto)|   the page's tracker key, when it has one
     |---------------------------|
     | your keys  Eb  F  D  Gb  Db|   the keys he plays in most, from the log
     |---------------------------|
     | C  Db  D  Eb  E  F         |
     | F# G  Ab  A  Bb  B         |
     +---------------------------+
```

- A card has one tonic. Numbers use tonic numbering with major-scale accidentals (nashville.js), so a card that moves
  from E♭ minor to G♭ major and lands in E♭ major reads `1m9 > b3maj9 > 1maj9` against one tonic, and transposes as
  a whole.
- **Transposing moves the voicing, not the idea:** every note shifts by the interval from the written tonic, taking
  the shift in -6..+5 half steps so the register stays where Claude wrote it (an octave fold keeps the bass at or
  above A0 and the top at or below C8). Names are respelled in the new key by the page's own THEORY; numbers do not
  change.
- `my key now` follows the tracker live while selected, so a card can sit ready in whatever key he drifted into.

### 4.4 Tempo

- `[-] 72 [+]` steps 2 bpm (hold to repeat), `[` `]` step 4. `tap`: four taps set it (the median interval, 40-200 bpm).
- A card's chords carry beats (`4`, `2`, `8`); the meter is 4/4 unless the card says otherwise.
- Changes during a jam land on the next bar line.

### 4.5 Moments (Hear me)

- A card may cite up to three moments from his log, each `{ session, at, seconds }`; the button names the first
  (`Hear me at 5:22`, or `Hear me, Sep 12, 5:22` for an older session) and `[more]` lists the rest.
- The page asks the server for the replay cue (`build_replay_cue` from `pianocue.py`, over the log, read only) and
  plays it locally, so it never broadcasts to other listeners. A moment whose session is gone greys the button with
  `that session is no longer in the log`.
- `Hear me with the loop` appears only on report cards (section 9), where the jam record gives the bar clock.

### 4.6 Kept cards and capture (chord templates)

- **Keep** copies any card into Kept as `kind: "kept"`, owned by Daniel. A kept card's title, meaning, key, tempo and
  chord order are editable in place (click to edit, Enter to save). Chords are edited as text in the chip (`Abmaj9#11`,
  or a number such as `4maj9#11`) and re-voiced by the server's voicing bridge; a chord the bridge cannot voice keeps
  its old notes and shows the bridge's error under the chip.
- **Keep what I just played** (Now header button; KeyLab pad in J5):
  - takes his last phrase, from the overlay's committed chords since the previous rest, at most 8 chords;
  - each chip keeps his exact voicing (the harmonySet notes at the commit's settle) and his chord's name and number;
  - key = the tracker's key (or the locked key); tempo = a rough reading from the commit spacing, labelled `about`;
  - title `Kept at 21:43`, meaning empty, both editable.
  This is the bridge between "intuition and memory" and templates: he plays something, keeps it, and Claude can read
  it back, name it, and publish a concept card about it.
- **Keep as card** on the Now header's `last:` line turns an ad-hoc chord Claude just played from the terminal into a
  Tonight card, so a concept tossed off in chat becomes something he can find again.

### 4.7 A starter deck from what he already plays

Examples of the card text the UX expects (the theory design owns the final wording and the voicings). Numbers use
tonic numbering; display puts the suffix in superscript.

| Group | Title | Meaning (one line) | Chords (key) | Numbers |
|---|---|---|---|---|
| Your moves | The Lydian 4 chord | The 4 chord with its raised 4th on top: it floats instead of landing | Ebmaj9 > Abmaj9#11 (E♭) · Dbmaj9 > Gbmaj13#11 (D♭) | 1maj9 > 4maj9#11 · 1maj9 > 4maj13#11 |
| Your moves | The gospel 5 over 4 | The 5 chord standing on the 4 in the bass: churchy, it wants to fall home | Abmaj9 > Bb11/Ab > Eb/G (E♭) | 4maj9 > 5^11/4 > 1/3 |
| Your moves | Blooming chord | One chord opening: no 3rd, then the 3rd, then the 7th | Ebsus2 > Eb(add9) > Ebmaj9 (E♭) | 1sus2 > 1add9 > 1maj9 |
| Your moves | The half-step slide | Slide one thing down a half step and the colour turns from bright to shadow | F9/A > Fm9/Ab (E♭) · Gm7/Bb > Gbmaj7/Bb (E♭) | 2^9/#4 > 2m9/4 · 3m7/5 > b3maj7/5 |
| Your moves | Walking bass under a held chord | Hold the chord, let the bass step down: the sad staircase | Bbm11 > Bbm11/Ab > Bbm11/Gb (D♭) | 6m11 > 6m11/5 > 6m11/4 |
| Your moves | Down a minor third to a new home | The 6 chord turns major and becomes home: a door into a warmer room | Gbmaj9 > Ebmaj9 (G♭ then E♭) | 1maj9 > 6maj9, which becomes the new 1 |
| Your moves | Borrowed colours | Chords from E♭ minor inside E♭ major: same home, cloudier sky | Abm > Cb > Dbmaj9 > Ebmaj9 (E♭) | 4m > b6 > b7maj9 > 1maj9 |
| Your moves | The sunrise ending | Minor home, lift to its relative major, land in the major home | Ebm9 > Gbmaj9 > Ebmaj9 (E♭) | 1m9 > b3maj9 > 1maj9 |
| Try this | Suspended 5, then the real 5 | Let the sus chord find its 3rd before home: the 3rd is the note that pulls | Bb7sus4/Eb > Bb7 > Ebmaj9 (E♭) | 5^7sus4/1 > 5^7 > 1maj9 |

---

## 5. The transport and the lead-sheet strip

### 5.1 Timing rules

- **One transport.** Bar lines are absolute: `bar0 + n · barMs`, never accumulated, on the `performance.now()` clock the
  cue player uses (its worker timer keeps time when the window is behind the Claude app).
- **Launch quantize.** With nothing running, Loop and Try start after the count-in (default 1 bar). With a jam running,
  a new Loop or Try replaces the current one at the next bar line, shown in the strip as `queued: The Lydian 4 chord .
  bar 1`. Play during a jam also waits for the next beat.
- **Changes** to tempo land on the next bar line; to key, on the top of the next pass (a mid-pass key change sounds
  like a mistake); to a card's `rev`, on the top of the next pass.
- **Count-in**: soft clicks in Claude's voice (a 20 ms sine tick, 2 kHz on beat 1, 1.5 kHz on the others, velocity 60),
  the DOM strip counts `4 3 2 1` large; in-frame only the pips move.
- **Scheduling**: the transport hands the cue player one pass as a `sequence` of steps, and queues the next pass one bar
  before the current one ends, so Stop is never more than a pass of pending steps away from a clean `clear`.
- **Ducking** (Loop and Try, when on): Claude's master gain drops to 0.5 while any of his notes was struck in the last
  0.8 s, and returns over 400 ms.
- **His pedal never touches Claude's notes.** Claude's voice has its own holds.

### 5.2 The strip in the DOM (always available, never recorded)

**In the deck's Now header, during a jam:**

```
+-- NOW -------------------------------------------------------------+
| LOOP  Walking bass under a held chord . Db . 66 bpm       [ Stop ] |  line 1: kind, card, key, tempo
|                                                                    |
|   NOW   Bb m11 /Gb      6m11/4        NEXT  F 7sus4   3 7sus4      |  line 2: NOW at 22 px, NEXT at 15 px, 55%
|   (o)( )( )( )   bar 3 of 4   pass 5          your top: 9          |  line 3: beat pips, bar, pass, his top note
|   [=========================-------------]                         |  pass progress, 3 px
|   Claude [-----o----]  duck [x]   backing [ comp v ]               |
+--------------------------------------------------------------------+
```

- `your top` is the degree of his highest sounding note against the NOW chord (`9`, `#11`, `b3`), updated on each
  note-on, shown for 2 s. It is the smallest possible theory lesson: the name of the note he is singing with.
- In a Try, line 1 reads `TRY` and line 3 adds `found` for 600 ms when he lands a chord (6.3). No counts, no totals.

**The pill, when the deck is closed** (and whenever a jam or a Show is active):

```
( (o)( )( )( )  Bb m11/Gb  >  F 7sus4    bar 3/4    [ Stop ]  [ Cards 2 ] )
```

- 44 px tall, `max-width: min(560px, canvas CSS width - 24px)`, radius 22, `--panel` at 90%, `--rule` border.
- Placement: horizontally centred on the canvas CSS box, 14 px above its bottom edge in 9:16 (over the TikTok caption
  band, which holds only floor garnish); in 16:9, at the canvas box's bottom-right corner (over the top octave, which
  he rarely plays). If the stage has a letterbox of 56 px or more below the canvas, the pill sits in it instead.
- The idle hint hides while the pill shows. `H` does not hide the pill (a running jam must stay stoppable).
- Showing: `( SHOWING  Ab maj9#11  4maj9#11    [ Dismiss ]  [ Cards ] )`.

### 5.3 The strip in the frame (jam view `stage` only)

For duet videos: the backing's NOW and NEXT chords, beat pips, bar and an honest credit line. It is a Canvas2D layer
made with `makeLayer()`, drawn after bloom like the label (`ctx.setTransform(sx, 0, 0, sy, 0, 0)` and `shadowScale`
once the adaptive-resolution patch lands), redrawn only on a chord change, a beat, or a text change. The canvas's big
label keeps naming what sounds; the strip names what the loop is doing.

**9:16 coordinates** (reference pixels, 1080x1920):

| Part | Box | Detail |
|---|---|---|
| Plate | x 180-900, y 1108-1192, radius 18, `rgba(8, 8, 12, 0.72)` | centred on x 540 like the staff; stops 16 px left of the TikTok button column |
| Line 1 | baseline y 1146 | `NOW` chord with `nameRuns` / `suffixRuns` at 40 px, INK; its number with `numberRuns` at 30 px, 0.94 alpha, 18 px after; right-aligned to x 870: `NEXT` chord at 30 px, 0.55 alpha, rising to 0.9 on the last beat before the change |
| Line 2 | baseline y 1178 | 4 beat pips (10 px, 8 px apart) from x 210; then caps 20 px, letter-spacing 0.1 em, `rgba(244, 241, 234, 0.62)`: `BAR 3 . WALKING BASS . D♭ MAJOR . 66 BPM . BACKING BY CLAUDE` |
| Progress | y 1189-1192 (3 px), x 198-882 | fills over the pass |
| Compact form | plate y 1120-1170, one line, baseline y 1154: pips, NOW, `>` NEXT | used during the count-in, in Try "wait for me", and when line 1 overflows twice |

Overflow order for line 1: drop NEXT's number, shrink NEXT to 26 px, drop NOW's number. For line 2: drop the tempo, then
the card name. `BACKING BY CLAUDE` is never dropped while Claude is sounding: on a public clip the viewer must be able
to tell whose notes those are.

Beat pips pulse by size only (1.25x decaying over 120 ms, clock-driven), never by brightness, so no strobe at fast
tempi.

**9:16 collision map for the strip** (existing boxes from `LAYOUT` in piano.js and spectacle-spec 5.6):

| Neighbour | Box | Clearance |
|---|---|---|
| Staff layer | x 110-970, y 500-1100 (bass staff bottom line y 980; ledgers at 1004 E2, 1028 C2, 1052 A1, 1076 F1, 1100 D1) | 8 px below the layer box; 44 px below an A1 notehead |
| Pedal mark | x 177-345, y 990-1086 | 22 px |
| Rarity banner / phrase card | y 478-576 | none shared |
| Nashville row | y 471-601 | none shared |
| E10 hem ribbon | y 950-1150, behind the columns | overlaps 1108-1150: the protect mask holds effect light at ≤ 35% under the plate |
| E4 fountain | y 1170-1370 | overlaps 1170-1192: same protect rule |
| E7 shafts | rail up to y 700 | pass behind the plate: same protect rule |
| Rail / keys | y 1370 / 1370-1590 | 178 px |
| TikTok buttons | x ≥ 916, y 800-1596 | 16 px |
| TikTok caption band | y ≥ 1596 | none shared |

If `drawStaff` records an ink bottom (the counterpart of the spectacle spec's `inkTop`) lower than y 1098, the strip
takes the compact form, which starts at y 1120.

**16:9 coordinates** (reference pixels, 1920x1080):

| Part | Box | Detail |
|---|---|---|
| Plate | x 1240-1824, y 548-628, radius 16 | under the staff, left edge on the staff's; right edge at the 5% title-safe margin |
| Line 1 | baseline y 584 | NOW 34 px, number 26 px; NEXT 26 px right-aligned to x 1800 |
| Line 2 | baseline y 614 | pips 9 px from x 1264; caps 18 px |
| Progress | y 625-628 | |

16:9 neighbours: the staff layer x 1240-1880, y 12-532 (16 px); the label x 50-950 and Nashville row x 50-950 y 332-452
and the banner x ≤ 940 y 344-440 (no horizontal overlap). **Unmeasured:** the 16:9 rail and trail-foot height. The
receipt (11, R-J3) must measure it and require the plate to end at least 60 px above it.

---

## 6. How notes look

### 6.1 Four identities

| Who | Key surface | Glow | Depth | Trails, sparks, coloured spill lights | Label caption (stage) |
|---|---|---|---|---|---|
| **Daniel, live** | unchanged: pitch colour taken into the surface | unchanged `LIGHT` envelope | full | unchanged | none |
| **Claude's hand** | stays ivory (white keys) or black: never pitch-tinted | emissive moonlight `#C8DCFF`, following the same strike and sag envelope, scaled by velocity; capped at 0.75 of Daniel's lift so his notes are always the brightest thing | 60% (a lighter hand) | none (an optional "Claude trails" at 35% gain is a lab setting, off) | `CLAUDE` |
| **Ghost** | not pressed, not lit | rim + faint fill (6.2) | 0 | none | none |
| **Daniel, replayed** | his pitch colour at 55% saturation | 70% of his level | full | trails at half gain, no sparks | `YOU . 5:22` |

- Why moonlight: the pitch palette is gamut-mapped to full saturation all around the hue circle, so no hue is free. A
  cool, low-saturation silver is distinct from every pitch colour and from warm ivory, and it is not gold (Legendary)
  or amber (the page accent).
- **Both hands on one key:** his pitch colour wins; a moonlight rim shows Claude holds it too.
- Claude's and replayed notes never reach the practice log, the key tracker, harmonySet for rarity, the rarity scorer
  or the light budget's "fresh strike" protection (cues.js already carries `meta.source` for this).

### 6.2 Ghost keys

```
 top view of an octave, Show of Ab maj9#11 (Ab C Eb G Bb D) with degree labels on

        R        3        5        7        9       #11
       .--.     .--.     .--.     .--.     .--.     .--.
  ...  |Ab|  C  |  |  Eb |  |   G |  |  Bb |  |   D |  |  ...
       '--'     '--'     '--'     '--'     '--'     '--'
       rim      rim      rim      rim      rim      rim
```

| State | Look |
|---|---|
| **Target** | A rounded-rectangle rim on the key top, inset 6% of the key width, stroke max(2.5 output px, 0.045 u), moonlight at 0.55 linear (black keys 0.7), normal blending, under the bloom threshold. Inner fill moonlight at 10% alpha, breathing 0.92-1.00 at 0.5 Hz. A short bar on the key's front lip, 30% of its width, so the ghost reads from the low 16:9 camera too |
| **Incoming** (Try, next chord) | Dashed rim (dash 0.12 u, gap 0.08 u), 35% alpha, no fill. Appears on the last beat before the change |
| **Hold** (a note in both the current and next chord) | A second, inner rim for the last beat and the first beat after the change: "keep this one down" |
| **Matched** | He presses a ghost key: his key lights as always; the rim contracts to a small bright ring and fades in 300 ms |
| **Other octave** | He plays the right note in another octave: the ghost's rim keeps only its top half until he lands it or the chord changes |
| **Found** | Every chord tone is in his harmonySet (voicing-free, any inversion; the natural 5th is optional when the bridge's `roundtrip.omits` lists it) for 150 ms: all rims pulse once (size, not brightness) and the strip says `found` |

- **Labels on ghosts** (glass only; text on 3D keys aliases and clutters a recording): a small pill above the key's back
  edge, Archivo 700 12 CSS px, moonlight on `rgba(15, 17, 20, 0.8)`. `degrees` shows the note's job in the chord (`R 3
  5 7 9 #11 13`), `letters` shows `A♭3`. Default: degrees for Show, off in Try.
- **On the glass** the same states are drawn in 2D: each ghosted key's rest-pose top face is projected every frame
  (`camera.project` on its four top corners; at most 24 keys, so the cost is a few hundred vector ops) and stroked
  with the same rim, fill and dash rules in CSS pixels x DPR. Claude's pressed keys on the glass are filled
  quads, moonlight at 38%, with a rim at 80%. Replayed notes on the glass are filled quads in his desaturated pitch
  colours.
- **On the stage** ghosts are one instanced mesh of rim quads just above the key tops (a ring texture with an analytic
  `fwidth` edge, so they never alias), precompiled with the spectacle effects.

### 6.3 Try, beat by beat

```
 card: Bb7sus4/Eb (4 beats) > Bb7 (4) > Ebmaj9 (8), 72 bpm, Try in time, backing "with bass"

 beat       c1  c2  c3  c4 | 1   2   3   4   | 1   2   3   4   | 1   2   3   4   5   6   7   8
 clicks     x   x   x   x  |                 |                 |
 bass (C)                  | Eb              | Bb              | Eb
 ghosts                    | Bb7sus4/Eb .... | Bb7 ........... | Ebmaj9 .........................
 incoming                  |             Bb7 |          Ebmaj9 |                     Bb7sus4/Eb
 hold rims                 |       Ab F Bb   |        Bb D F   |                     Eb F Bb
 strip      4   3   2   1  | NOW sus > 7     | NOW 7 > maj9    | NOW maj9 > sus (next pass)
```

(The hold row is computed per change from the voicings: pitch classes in both chords get the hold rim. Here Bb7sus4/Eb
to Bb7 keeps Ab, F and Bb and adds D, the 3rd, the note that pulls toward E♭; Bb7 to Ebmaj9 keeps Bb, D and F.)

- **In time** (default): the transport never waits. `found` flashes when he lands a chord; nothing is counted.
- **Wait for me**: the ghost stays until the chord is found, then the next chord's ghosts come in. No clicks, no clock;
  the strip takes its compact form without pips. After 6 s of waiting, Claude plays the bass note of the waiting chord
  once, softly (velocity 45), as a hint; after 12 s, the whole chord once. Both hints can be turned off.
- **Try backing**: ghosts only (clicks continue through the pass so time stays audible); with bass (Claude plays the bass
  note on each chord's downbeat); with loop (the card's Loop in its backing style under the ghosts).

### 6.4 Marks on his notes over a loop or a Try

While a jam runs, each note he strikes is classified against the NOW chord:

| Class | Rule | Quiet (default) | Teach |
|---|---|---|---|
| **In the chord** | its pitch class is in the NOW chord's voicing | no mark | a 4 px ivory dot under the key front |
| **Colour** | not in the chord, in the card's key scale (or the chord's own scale when the card names one, for a borrowed chord) | a 6 px ivory diamond under the key front | the diamond plus its degree (`9`, `#11`, `13`) |
| **Outside** | neither | a 7 px open ring under the key front | the ring plus its degree |

- Marks are **glass only, always**, whatever the jam view. Keys and trails keep his pitch colours (the sustain meaning
  must not change, and the spectacle rule "colour belongs to the chord" holds), and a video does not need a lesson
  printed under the keys.
- A mark lives while its note sounds and fades 0.6 s after its sound ends. At most 12 marks at once (the newest win).
- The words in the UI are "in the chord", "colour" and "outside". Never "wrong".

---

## 7. Jam view: what goes on the stage and what goes on the glass

| Thing | `stage` | `glass` | `auto` (default) |
|---|---|---|---|
| Claude's hand on the keys | 3D keys, moonlight | glass quads | stage live, glass during REC |
| Ghost keys | 3D rims | glass rims | stage live, glass during REC |
| Ghost labels | glass | glass | glass |
| Marks on his notes | glass | glass | glass |
| Lead-sheet strip | in frame (5.3) and DOM | DOM only | in frame live, DOM only during REC |
| Big chord label while a jam runs | names what sounds: his notes plus the backing | names his notes only | as stage live, as glass during REC |
| Label when only Claude sounds (Play) | Claude's chord, `CLAUDE` caption | unchanged; the Now header names Claude's chord | as stage live, as glass during REC |
| Nashville row's key | the jam key (the card's), unless Key is locked in the top bar | the same | the same |
| Claude's sound in the recorded audio | mixed into the recorded track (the voice's output through a `MediaStreamAudioDestinationNode`, summed with the audio input) | not recorded | not recorded during REC |
| Rarity and the practice log | his notes only | his notes only | his notes only |

- **Stage is a duet video; glass is his solo video with a private coach.** Auto gives him the duet while he practises
  and a clean take the moment he presses REC.
- **REC start in auto** crossfades Claude's things from stage to glass over 250 ms, and the toast says so:
  `Recording you only. Claude's keys and the strip stay on the glass (Jam view: auto).` REC stop crossfades back.
- **The jam key.** While Play, Loop or Try runs (and for 2 s after), the Nashville row counts from the card's key, and
  the top bar's Key select shows `jam: E♭` in its closed state. When the jam ends the previous setting resumes. A key
  locked by hand in the top bar always wins.
- **Claude through MIDI out** (Kontakt or FL on a loopback port): the sound then belongs to his mix and is in any
  recording that captures his interface, whatever the jam view. The deck's settings say this next to the MIDI out
  choice.
- **Honesty on public clips:** in `stage`, `BACKING BY CLAUDE` stays in the strip and `CLAUDE` in the label caption.
  Claude's notes never score rarity, so no banner can ever be earned by Claude's hand.

---

## 8. Claude's courtesy: sound that arrives from the terminal

Cues and card actions Claude sends (`pianocue play`, `progression`, a remote Loop) pass a **courtesy gate** in the page
before the player. His own clicks skip it.

| Remote action | He is in a rest | He is playing |
|---|---|---|
| Sound (play, sequence, Loop, Try) | plays at once | waits up to 20 s for a rest, then plays; if no rest comes, becomes a **knock** |
| Ghost (hover, Show) | appears at once, 400 ms fade | waits up to 8 s for a rest, then fades in anyway (silent) |
| New card | section 3.3 | section 3.3 |
| Clear | at once, always | at once, always |

**The knock:**

```
+-- NOW --------------------------------------------------------+
|  (*) Claude has a chord for you: Gb maj13#11           [ Hear ] |   the dot pulses in --claude, 1 Hz, size only
|      waiting 0:34                                  [ Not now ]  |
+-----------------------------------------------------------------+
pill: ( (*) Claude has a chord for you   [ Hear  Enter ]  [ x ] )
```

- `Enter` or Hear plays it; Not now drops it into Tonight as a card. A knock expires into Tonight after 60 s.
- With "Let Claude knock while I play" off, remote sound always waits silently for a rest.
- A `--now` flag on the verbs (for "play it now" asked in chat) skips the gate; when Daniel is typing to Claude he is
  not playing, so the gate rarely matters then.
- A remote Loop start also shows who started it: `Claude started Loop: Walking bass . [Stop]`.

---

## 9. The discussion loop

### 9.1 The jam record

When a Loop or Try stops (by Stop, a clear, or a swap to another card), the page keeps a jam record:

```json
{ "jam": "j-20260914-214012-3f1a", "session": "<performance session id>", "card": "c-lament-bass", "rev": 3,
  "kind": "loop", "key": "Db", "bpm": 66, "meter": 4, "backing": "comp", "view": "auto",
  "bar0_t_ms": 612400, "stopped_t_ms": 746800, "passes": 11, "count_in_bars": 1, "found": null }
```

- `bar0_t_ms` and `stopped_t_ms` are on the practice log's clock, so any analysis lines his notes up with the loop's bars.
- The record is posted to the server (`state/arsenal/piano/jams.jsonl`) and, once the log accepts the kind, as a `jam`
  event in the session.
- **Cross-build hazard (the same one the spectacle spec names for `rarity`):** `performance.py` rejects an unknown event
  kind with a 400 and drops the whole batch. The log lane adds `jam` to `KINDS` first; the client feature-detects it and
  sends nothing of kind `jam` before then. The jam record route does not depend on it.

### 9.2 Asking

At the end of a jam the strip keeps a closing line for 30 s (and the Now header keeps it until the next jam):

```
( Jam kept: 2:14 over "Walking bass under a held chord", 11 passes   [ Ask Claude ]  [ Loop again ] )
```

- **Ask Claude** marks the record `asked` on the server. Claude learns of it either from a watcher (a
  `pianocue jams --wait` style verb run as a harness-tracked background task) or at Daniel's next chat message
  (`pianocue jams latest`). The button turns into `Asked . report coming` and then `Report ready  [Open]`.
- He can also just say "how was that?" in chat. The record is there either way.

### 9.3 The riff report card

A card of `kind: "report"`, published into Tonight with `NEW`, linked to its jam:

```
+-- RIFF REPORT -----------------------------------------------------+
| Your riff over "Walking bass under a held chord"                   |
| 2:14 . 11 passes . Db . 66 bpm                            21:40    |
|                                                                    |
|  bar     1          2            3            4                    |
|  loop    Bb m11     Bb m11/Ab    Bb m11/Gb    F 7sus4              |
|          6m11       6m11/5       6m11/4       3 7sus4              |
|  you     9  11  5   b3  11       13  9        4 . 5                |  his most-played top notes, as degrees
|                                             [ pass 7 v ]           |  one pass, or "most played"
|                                                                    |
|  What you reached for                                              |  three facts at most, each with a time
|   . the 9 and 11 on the minor chords: most of your top notes       |
|   . a G natural over Bb m11/Gb at 1:12: outside, the 13 of Bb      |
|   . you saved your rise for bar 4 in 6 of 11 passes                |
|                                                                    |
|  One question                                                      |
|   At 1:12 the G natural rubbed against the Gb in the bass.         |
|   Did you want that rub?                                           |
|   [ Hear 1:08-1:16 ]   [ on purpose ] [ by ear ] [ not sure ]      |
|                                                                    |
|  One thing to try                                                  |
|   The same loop, landing your top note on the 3rd of F7 in bar 4   |
|   (A natural): it is the note that turns sus into pull.  [ Try it ]|
|                                                                    |
|  [ Hear pass 7 with the loop ]   [ Loop again ]   [ Keep ]         |
+--------------------------------------------------------------------+
```

- **The lead-sheet lanes** are the card's chords with his top notes underneath as degrees of each chord: a chart of
  what he sang with his right hand, readable without staff notation. A pass selector switches between `most played`
  and any single pass.
- **Facts only**, from numbers the analysis verb computed; each fact carries a time he can hear. At most three.
- **One question**, anchored to a moment he can replay (the ideas panel's rule: open with one question, don't lecture).
- **Answer chips** write his answer back to the card (`answers: [{ q, a, at }]`); the chips stay visible with his
  choice highlighted; Claude reads it on the next turn. Answers add up across sessions into a picture of what he does
  on purpose and what his hands find.
- **One thing to try** is itself a button that publishes and opens a Try card (the same loop, with the one target
  note ghosted on the bar it applies to).
- **Hear pass N with the loop** schedules his replayed notes for that pass and the loop's backing from the jam record on
  one clock: the only place his playing and Claude's backing are heard together after the fact.
- **No score, no percent, no "best".** When the report points to one pass, it says why in plain facts ("pass 7: your
  widest top line").
- **What the analysis must provide** (for the practice lane; the verb name is theirs): per bar, his top notes' degrees
  against the loop chord (mode and per pass); the share of his notes in the chord, colour and outside; outside notes with
  times; the top-line range per pass; velocity per pass (the arc); where he rested; pedal share. Placeholders in the
  wireframe are illustrative only.

### 9.4 How he reaches a report

1. The closing line's `Report ready [Open]` (and `Enter` while it is selected in the pill).
2. Tonight, top, with `NEW`.
3. From chat: Claude names the card by title; `pianocue card open <id>` opens the deck on it (subject to the courtesy
   gate only if it would make sound, which opening does not).
4. Every report links back to its source card (`over: Walking bass under a held chord [open]`) and the source card lists
   its reports (`2 riffs tonight [open]`).

---

## 10. What the UX needs from the other halves

Field names are proposals; the protocol design owns the final shapes.

**A card:**

```json
{ "id": "c-lydian-4", "rev": 2, "kind": "concept", "group": "moves", "rank": 10, "owner": "claude",
  "created_at": "...", "updated_at": "...",
  "title": "The Lydian 4 chord", "meaning": "The 4 chord with its raised 4th on top: it floats instead of landing.",
  "theory_name": "Lydian", "why": "2-3 sentences, optional", "tags": ["lydian", "four chord"],
  "tonic": "Eb", "bpm": 72, "meter": 4,
  "chords": [
    { "text": "Ebmaj9", "number": "1maj9", "beats": 4,
      "voicings": { "full": [39, 46, 55, 58, 62, 65], "comp": [39, 55, 62] },
      "reads_as": null, "omits": [] },
    { "text": "Abmaj9#11", "number": "4maj9#11", "beats": 4,
      "voicings": { "full": [44, 51, 60, 67, 70, 74], "comp": [44, 60, 67] },
      "reads_as": "Cm9/Ab", "omits": [] } ],
  "moments": [ { "session": "<id>", "at": "5:22", "seconds": 8 } ],
  "try": { "target_notes": null, "hint": null },
  "report": null, "answers": [] }
```

- `voicings.full` from the bridge's chosen style, `voicings.comp` from its `shell` style (the Loop default), both in the
  card's tonic; the page transposes by shifting (4.3). `bass` and `pad` are derived in the page (lowest note; `full`
  at velocity 45, held).
- `reads_as` from `roundtrip.page_name` when `roundtrip.match` is not `exact`; `omits` from `roundtrip.omits`.
- The MIDI numbers above are illustrative; the bridge computes the real ones.

**Transport and storage:**
- Cards stored under `state/arsenal/piano/deck/` (git-ignored). Kept cards and answers too.
- `GET /api/piano/cards?since=<rev>` on page load and on every cue-stream (re)connect; a `card` event on the existing
  cue stream for live publishes, updates and deletions (`{ id, rev, deleted }`).
- `POST /api/piano/cards` (Claude publishes; the page posts kept cards and edits), `POST .../<id>/answers`.
- A replay route returning a cue without broadcasting it (4.5).
- A voicing route the page can call when Daniel edits a kept card's chord (the bridge runs server-side).
- `POST /api/piano/jams`, `POST /api/piano/jams/<id>/ask`, and the verb side to wait on asks.
- A remote deck action cue (`deck`: open a card, Play/Show/Loop/Try it) so the verbs can drive the buttons.

**Pre-existing facts this design relies on:**
- Cue notes carry `meta.source`, and the page keeps them out of the log and the key tracker (cues.js header).
- A hover never sounds; `hold_ms: 0` holds until clear (the Show button).
- `createClaudeVoice` supports MIDI out and a built-in synth, with `unlock()` on a gesture.

---

## 11. Build phases and receipts

| Phase | Scope | New files (proposed) | Exit |
|---|---|---|---|
| **J1 Deck and glass** | Deck drawer (overlay/dock), groups, search, NEW handling, Play and Show from cards, chord-chip hover and click, the glass layer with ghost and Claude quads, shortcuts `A ↑ ↓ Enter K Esc Backspace`, the Now header with Claude's caption | `arsenal/web/piano/deck.js`, `piano/glass.js`, CSS in `piano.css`, piano.js hooks | R-J1, R-J2 |
| **J2 Transport** | Loop and Try (in time, wait for me), count-in, backing styles, quantized launches, ducking, the DOM strip and pill, jam key, `\ ' - = [ ]` | `piano/transport.js` | R-J4, R-J5 |
| **J3 Stage** | Jam view auto/stage/glass, Claude's hand on 3D keys, 3D ghost rims, the in-frame strip, REC crossfade, Claude's voice in the recorded audio for stage | piano.js (keys, overlay layer), `piano/jamstrip.js` | R-J3, R-J6 |
| **J4 Discussion** | Marks on his notes, the courtesy gate and knocks, jam records, Ask, report cards with lanes, answers, Try-it cards, Hear pass N with the loop | deck.js, server routes (other lane) | R-J7, R-J8 |
| **J5 Hands** | Keep what I just played, kept-card editing, KeyLab pad learn for Stop / Loop again / Keep that / Hear | deck.js, piano.js MIDI filter for learned pads | with Daniel |

**Piano.js integration points** (after the builds in flight land): `noteOn`/`noteOff` accept a source and route Claude
and replay notes to their looks while keeping them out of `perfLog`, `pcHistory`, harmonySet-for-rarity and the budget's
fresh-strike protection; `overlay.update` takes a label source (his notes, or what sounds); `numberFor` takes the jam key;
`fitCanvas` reads the deck's docked inset (frozen during REC); the keydown handler gains the keys in 3.5 before its
`KEYMAP` lookup; `window.__piano.jam = { deck, transport, view, glass: { layout() }, stats() }`.

**Receipts** (headless, isolated Chrome with the anti-throttling flags and `--mute-audio`, on the builder's own server,
GET only against 8793):

| ID | Check | Pass |
|---|---|---|
| R-J1 | Deck layout at 1280x900, 2560x1440 (9:16 and 16:9), fullscreen, deck open and closed | 9:16 at 2560 wide overlays with no reflow; 16:9 docks with the canvas refit; the deck, pill and glass exist in fullscreen; toast never under the deck |
| R-J2 | Glass alignment: seeded frozen frame, ghosts on 12 keys, compare glass rim centroids with the projected 3D key-top centroids from the stage render | every centroid within 1.5 CSS px at DPR 1 and 1.5, both framings, during a camera follow pan |
| R-J3 | Strip collisions: `__piano.jam.glass.layout()` and the strip's rectangles against the label glyph box, chips, Nashville row, banner, staff ink box, pedal mark and TikTok zones, k = 0.5, 1, 2; a low-bass case (A1, F1) | zero intersections; the low case picks the compact form; 16:9 plate ≥ 60 px above the measured trail foot |
| R-J4 | Transport timing: 100 bars at 72 and 140 bpm, a tempo change and a key change mid-jam, window occluded (worker timer) | step lateness mean ≤ 2 ms, max ≤ 12 ms; zero drift of bar lines against `bar0 + n·barMs`; changes land on the bar / pass top |
| R-J5 | Try found: synthetic harmonySets for each starter-deck chord, all inversions, with and without the natural 5th | `found` fires exactly for voicing-free matches; wait-for-me advances only on found; no counts anywhere in the DOM |
| R-J6 | Clean recording: seeded run of his notes over a Loop with ghosts, jam view auto, 5 s REC; the same run with no jam | every recorded frame MAE 0 against the no-jam run (the canvas holds only his notes); in stage the frames differ and `BACKING BY CLAUDE` is present |
| R-J7 | Honesty: a 60 s Loop with his synthetic notes, then Hear me and a remote play | 0 log events, key tracker changes or rarity scores from Claude or replay notes; his notes all logged; no `jam` event before the log accepts the kind |
| R-J8 | Courtesy: remote play while synthetic notes sound continuously for 25 s, then a rest | nothing sounds during the phrase; a knock appears at 20 s; Enter plays it; remote ghosts appear ≤ 8 s |

---

## 12. Open questions for Daniel (each with a recommended default)

1. **Should Claude's backing be in your recordings?**
   - **Recommended:** Jam view auto. While you practise you see and hear the duet; the moment you press REC, the take is
     only you, and Claude's keys and chords move to a private layer only you can see. For a duet video, switch Jam view
     to stage.
   - Alternative: duet by default in recordings too.
2. **Try: in time, or wait for you?**
   - **Recommended:** in time with a one-bar count-in (what you asked for), with "wait for me" one click away for a new
     shape you want to find slowly.
   - Alternative: wait for me by default.
3. **Which sound should Claude play with?**
   - **Recommended:** its own soft built-in voice, so you can always hear which notes are yours.
   - Alternative: MIDI into FL/Kontakt, so the loop sounds as good as your piano and lands in your mix and recordings.
