# LCD capability map, probe plan and context-engine sketch: the synthesis (verbatim)

Workflow run wf_05ceb8e4-91d (task w34xc5hn9), 2026-10-24. Research only: nothing was sent to the KeyLab.
Daniel (verbatim, 2026-10-24): "can't we make our own context aware engine that borrows from the default script? perhaps we can make it better. what can we write to the LCD? what are the full functionalities afforded us there?"
Local scratch paths shortened; third-party code was read for facts only.

---

# KeyLab screen and our own FL engine: synthesis for Daniel, 2026-10-24

**The short answer.**
- **The screen shows ready-made layouts, not pixels.** We pick a layout by its number. Then we fill its slots with text, colour, a bar from 0 to 127, or a picture number. The keyboard has 108 built-in pictures. We cannot draw our own.
- **Two layouts are proven on your keyboard:** the two-line page and the one-line popup.
- **Many more are known from code or from another owner's tests.** That includes a real 7-line scrolling list with a big picture beside it.
- **Fourteen layouts are still blank on the map.** Part B is a plan to try each one with a single message while you watch.
- **Yes, we can build our own engine, and make it better than Arturia's.** Arturia's script only asks "which of four windows is in front?" It knows 16 knob settings for about 30 FL plugins. It also repaints the whole screen, about 40 messages at a time, on almost every change in FL. FL tells a script far more than that. Part C sketches our engine.
- **Two decisions are yours, early:**
  1. Should we update FL from 26.1.3 to 26.1.7 or later? That update fixes a freeze that can happen when a script sends screen messages.
  2. May we add a loopback MIDI port? That is the pipe that would carry messages between FL and the hub.
- **Nothing was sent to the keyboard**, and nothing was changed anywhere.

**Words used below.**
- *Frame*: one message to the screen.
- *Field*: a labelled slot inside a frame.
- *SysEx*: the long message type the keyboard uses for its screen and lights.
- *Hub*: our program on the PC that runs the keyboard.
- *Probe*: a one-message test you watch and answer.

**How sure each fact is.**
- **OURS**: seen on your keyboard, and a repo receipt says so.
- **TODAY**: you saw it today (from the brief). No receipt has been filed yet.
- **CODE**: read from a named file.
- **OTHER UNIT**: read from saxofonbrian's MIT-licensed protocol document. Its author measured it on his own KeyLab mk3. That is stronger than code, but it is not your keyboard.
- **GUESSED**: worked out from names or patterns only.
- **UNKNOWN**: no source gives the fields.

---

## A. The LCD: everything we can write

### A.1 How a screen frame is built

**The envelope.** Every frame is `F0 00 20 6B 7F 42 | 00 02 04 | <screen id> | <fields> | F7`.
- OURS: the envelope was used live (surface map Y1).
- CODE: `KL3Display.py:22`.

**Fields.** A field is a tag byte, then its value, then `00`. A value is one of three kinds:
- a number, 0 to 127;
- a colour, exactly 3 bytes R G B, each 0 to 127;
- ASCII text.

**Fields are optional.** Arturia's own Ableton script sends fewer fields than its FL script does (CODE, Live `midi.py:19-37`).

**Copy Arturia's exact field set.** Extra or missing fields made about 1 frame in 30 fail on another unit. Matching Arturia's set fixed it (OTHER UNIT).

**An unknown tag stops the parser for the rest of the frame.** The firmware's own error text says so: "unknow parameter ... stopping parser" (CODE, firmware 1.5.0 strings). So each probe in Part B starts with the fewest fields.

### A.2 Every screen id

FL's own list of ids is `ScreenId.py:26-74`. I re-checked it, and it runs 0 to 46.

**What Arturia's FL script really draws.** I grepped every caller: 10, 11, 12, 13, 23, 24, 27, 28, 29 and 31, plus the labels 1-8. Its call to id 9 has no matching branch in `KL3Pages.SetCenterPage`, so it sends nothing.

| Id | What it draws | Fields | Evidence | Most impressive use |
|---|---|---|---|---|
| 0 | Screen-wide property | `00` colour | CODE (FL `KL3Display.py:91-99`), never called by anyone. What it does: UNKNOWN | Maybe a global tint (GUESSED) |
| 1-8 | Screen-button labels (1-4 above the screen, 5-8 below, in Arturia's numbering) | `00` style 0-11, `01` line, `02` colour type, `03` small picture, `04` RGB, `05`/`06` text (`07` from MainStage) | CODE (`KL3Buttons.py:62-90`, re-checked). The label colour also lights the button: OTHER UNIT | Eight coloured tabs that light their own buttons |
| 9 | "Clear labels" | UNKNOWN | Nobody uses it. FL's call to it is dead | Skip it. Clear each label instead (A.4) |
| 10 | One line | `00` text, `01` colour type, `02` RGB | CODE (FL draws it: "No Selection") | A status word in colour: REC, LIVE |
| 11 | One line, inverted | Same as 10 | CODE (FL's mixer page) | Track name as a coloured banner |
| 12 | Two lines, one colour per line, **stays up** | `00`/`01`/`02` for line 1, `03`/`04`/`05` for line 2 | **OURS** (no flicker, a 60 ms colour cycle, 2026-10-22) | A living home page: chord, key, BPM |
| 13 | Two lines, inverted: the home page in FL, Bitwig and Ableton | Same as 12 | CODE. FL repainting it with the pattern name: TODAY | Channel name in the channel's colour |
| 14 | Two lines, **big type** | Same as 12 | CODE. Defined in FL, never drawn by anyone | A big chord name |
| 15 | Big picture + one line | `00` text, `01` large picture | CODE. Defined, never drawn | Instrument picture + preset name |
| 16 | Big picture + two lines | `00`, `01`, `02` picture | CODE. Defined, never drawn | Plugin card: picture, plugin, preset |
| 17 | By its name, two pictures + two lines | UNKNOWN | Nothing seen | A "from → to" scene card (GUESSED) |
| 18 | By its name, a carousel of instrument types | UNKNOWN | Nothing seen | A sliding picture picker (GUESSED) |
| 19 | By its name, a carousel of instruments | UNKNOWN | Nothing seen | The same, with 44 instrument pictures |
| 20 | **List title, one column, 7 lines** | `00` title, `02` `<hi> <lo>` item count | OTHER UNIT (re-checked in the doc: 7 lines, "a line shows 34 characters") | A scene, preset or chord-history list |
| 21 | List: add an item at the bottom, or move the cursor | `00` text, `01` large picture, `02` 2 bytes (first byte: 0 = white, anything else = blue), `03` `<hi> <lo>` index. `03` alone moves the cursor | OTHER UNIT | Scrolling with the dial |
| 22 | List: add an item at the top | Same as 21 | OTHER UNIT | Scrolling up |
| 23 | One-line popup, gone after about 1 s | `00` text | **OURS** ("Hello Daniel flashed for 1 second") | "Saved", "Bank 9-16" |
| 24 | Two-line popup | Same as 12 | CODE (FL draws it while Rewind or Fast-forward is held) | "Scene: Tunnel / 128 BPM" |
| 25 | Three-line popup | Same as 24, plus `06`/`07`/`08` | CODE (Bitwig and Ableton draw it; FL never does) | A three-line notice |
| 26 | Popup: picture on the left + one line | `00` text, `01` picture | CODE. Defined, never drawn by FL | A picture toast |
| 27 | Popup: picture on the left + two lines | Same as 24, plus `06` picture | CODE (FL's Metronome and Step cards) | A "Tempo 128" card with the metronome picture |
| 28 | Knob readout: name, value, bar | `00` **value** text, `01` **name**, `02` bar 0-127, `03` colour type, `04` RGB | CODE (FL draws it) | "Glow 64%" with a bar |
| 29 | Fader readout | Same as 28 | CODE. **Draws only while skin touches the fader** (paper blocks it): OTHER UNIT | Touch to peek |
| 30 | General popup, **draws with no touch** | `00`, `01`, `02` bar, `04` RGB | CODE (defined, FL never calls it). Drawing without touch: OTHER UNIT | A live bar: level, beat phase, tension |
| 31 | Big picture on top + two lines (the "Connected" card) | Same as 24, plus `06` picture | CODE (FL draws it at start-up) | A title card on scene change or project load |
| 32 | By its name, rename (text entry) | UNKNOWN | Nothing seen. The firmware has a rename menu | Low payoff. May be interactive (GUESSED) |
| 33 | By its name, curve editor | UNKNOWN | Nothing seen. The firmware has velocity and aftertouch curve menus | An envelope picture, if the host can feed it (GUESSED) |
| 34 | Pitch wheel | UNKNOWN | OTHER UNIT saw "popup with half-filled bar and arrows" (Arturia family only) | A centre-split bar: pan, pitch bend, hue shift |
| 35 | Parameter gauge | UNKNOWN | OTHER UNIT saw "empty bar with arrows" (Arturia family only) | A gauge |
| 36 | By its name, pictures on both sides | UNKNOWN | Nothing seen | "From → to" pictures |
| 37 | Welcome screen | UNKNOWN | OTHER UNIT saw "welcome screen" in both families | **Caution**: the keyboard's own welcome page lets its buttons switch modes |
| **38** | Boot | **Never send** | Our gate refuses it (`screen.py:88, 158, 396`, re-checked) | None |
| 39 | Colour picker | UNKNOWN | OTHER UNIT saw "colour picker" (DAW family) and "colour palette at top left, unexplored" (Arturia family) | Show the scene palette |
| 40 | **List with a big-picture panel on the right** (the browser) | `00` title, `02` count. Then items through 21/22, **each with `01` picture** | OTHER UNIT | **A preset or scene browser with pictures** |
| 41 | Keyboard picture, popup version | UNKNOWN | OTHER UNIT saw "grey keyboard icon at top with heading" (DAW family) | Split point, key range |
| 42 | Keyboard picture | UNKNOWN | OTHER UNIT saw "grey keyboard icon in middle" (DAW family) | Same as 41 |
| **43, 44** | Pedal calibration, bootloader | **Never send** | Our gate refuses them | None |
| 45 | By its name, three lines that stay up | UNKNOWN | Nothing seen | A three-line home page |
| 46 | By its name, two small lines | UNKNOWN | In the Arturia family an empty frame "clears screen" (OTHER UNIT) | A compact status |
| *47* | *(not in FL's list)* A keyboard with coloured key range | UNKNOWN | OTHER UNIT, both families | The scale marked on a piano picture |
| *49-52* | *(not in FL's list)* Two-column list, 5 lines (MainStage) | `31` setup, `32` add, `33` add at top, `34` heading. Tags as reported by the screen lane from the protocol document; I did not re-check them | OTHER UNIT. Probably needs firmware 1.5 or later (GUESSED) | Chord │ numeral history |

### A.3 The pictures

**Large pictures, 86 of them (numbers 0-85).** Used in 15, 16, 26, 27, 31 and in list items under 40. Source: FL `images_sub_enums.py:4-90` (CODE).
- **0**: Arturia logo.
- **Types, 1-15**:
  - 1 Bass, 2 Brass/Winds, 3 Drums, 4 Electric Piano, 5 Keys
  - 6 Lead, 7 Organ, 8 Pad, 9 Piano, 10 Sequence
  - 11 Sound Effects, 12 Strings, 13 Template, 14 Vocal, 15 Default
- **Instruments, 16-59**:
  - 16 ARP 2600, 17 Acid, 18 Analog Lab, 19 Augmented Brass, 20 Augmented Grand Piano, 21 Augmented Strings
  - 22 Augmented Voices, 23 Augmented Woodwinds, 24 B-3, 25 Buchla Easel, 26 CMI, 27 CP-70
  - 28 CS-80, 29 CZ, 30 Clavinet, 31 DX7, 32 Emulator II, 33 Farfisa
  - 34 Jun-6, 35 Jup-8, 36 Korg MS-20, 37 Matrix-12, 38 Mellotron, 39 Mini
  - 40 MiniFreak, 41 MiniBrute, 42 Modular, 43 OP-Xa, 44 Piano, 45 Pigments
  - 46 Prophet-5, 47 Prophet-VS, 48 Prophet, 49 SEM, 50 SFZ Engine, 51 SQ80
  - 52 Solina, 53 Stage-73, 54 Synclavier, 55 Synthi, 56 Vox Continental, 57 Vocoder
  - 58 Wurli, 59 Default
- **UI symbols, 60-85**:
  - 60 Ableton, 61 Arp Chance, 62 Arpeggiator, 63 Arturia logo, 64 Bitwig, 65 Chord
  - 66 Cog, 67 Controls, 68 Cubase, 69 DAW, 70 Delete, 71 FL Studio
  - 72 Firmware update, 73 Logic Pro, 74 Metronome, 75 MIDI, 76 Pads, 77 Pencil
  - 78 Progression, 79 Reset, 80 Scale, 81 Transpose −, 82 Transpose neutral, 83 Transpose +
  - 84 Trash, 85 User
- **Use FL's numbers, not Bitwig's.** Bitwig's list leaves out MiniBrute, so every number from 41 on is shifted by one (CODE, Bitwig `CenterIcons.java`).

**Small pictures, 22 of them (0-21), for button labels (tag `03`).** Source: FL `images_sub_enums.py:92-114` (CODE).
- 0 Blue hand
- Arrows: 1 default (up), 2 down, 3 left, 4 right
- 5 Armed audio, 6 Armed MIDI, 7 Cubase monitor
- 8 GUI (FL), 9 GUI
- 10 Mute
- 11 Open (a down arrow), 12 Open 2 (play, or a right arrow)
- 13 Solo, 14 Stop
- 15 Check, 16 Delete
- 17 Heart, 18 Heart (liked)
- 19 Mixer
- 20 Search, 21 Search (on)

### A.4 The hard limits

**No raw pixels, no uploaded images, no fonts.**
- No integration we read has such a command: FL, Bitwig, Ableton, Analog Lab's definitions, MainStage, or two sweeps of every id up to 0x3F.
- The firmware loads its pictures by number from a built-in image file.
- Evidence: CODE (missing in every source). Strictly, this is proven only that far.

**Characters.**
- **Plain ASCII only, codes 32 to 126.**
- FL's script turns a whole line into ".Undefined text." if any character is outside ASCII. That is the script's rule (`KL3Display.py:26-47`, re-checked).
- What the keyboard itself shows for other bytes: UNKNOWN.
- A `00` byte ends a field, so it cannot appear inside text.

**Line length.**
- **31 characters is FL's own cut, not the keyboard's limit.** FL keeps 28 characters and adds "..." (`KL3Display.py:36-37`, re-checked).
- Arturia's Ableton script uses 17 characters on line 1 of screen 13, 30 on line 2, and 21 on popup line 2.
- Lists show 34 characters (OTHER UNIT).
- The true limit for each layout on your keyboard: UNKNOWN.

**Upper case: an open conflict.**
- FL's script upper-cases lines 2 and 3 itself (re-checked).
- Our README (line 51) says "the firmware" does it. Nothing proves that.
- Probe L1 in Part B settles it. It matters for "Am" versus "AM".

**Colour.**
- RGB, 0 to 127 per channel, one colour per line, plus one colour for a readout bar.
- Lists have no RGB. Item text is white or blue only (OTHER UNIT).
- A label's colour also lights its button (OTHER UNIT).
- Screens 15, 16, 23 and 26 have no colour fields.

**Popup time.**
- About 1 s (OURS for 23).
- No field sets the time. The only way to hold a popup is to send it again (FL does this; CODE).

**Speed.**
- **One frame every 60 ms, about 16 a second, is OURS.**
- 20 to 40 ms: UNKNOWN. The probe `lcdspeed` already exists for this.
- Two screen frames sent back to back can collide and one gets lost. A 60 ms queue fixed it (OTHER UNIT).
- Send each frame as one whole message (OTHER UNIT).
- **A burst of about 36 messages froze your keyboard (OURS).** Our governor allows at most 12 per 100 ms. Our screen writer adds "only when changed, newest wins, at most one frame per 0.1 s" (`screen.py`, re-checked).

**Brightness.**
- It is a device setting from 0 to 100, not a screen field (CODE, MIDI Control Center device file).
- The keyboard darkens after 5 minutes of no use. Whether our frames count as use: UNKNOWN. This matters for long sets.

**One painter at a time.**
- FL's script repaints the screen about 40 messages at a time on almost every FL refresh (CODE, `device_KL3.py`: `if flags not in [4,4096]`, re-checked).
- You saw it paint over us with the pattern name: TODAY.

**The list hazard.**
- In list 40, every item needs a picture.
- Otherwise each fader readout stalls the keyboard's own MIDI output for about 60 ms in every 100 (OTHER UNIT, re-checked in the doc).

**How to clear a label.**
- Send `00 00 00 | 04 00 00 00 00 | 05 00` (OTHER UNIT).
- A label with an empty text field (`00 02 00 | 04 <rgb> 00 | 05 00`) lights the button and shows no text.

### A.5 The top 8 most impressive things we could do

Ranked by how striking each would look, adjusted for how likely it is to work.

| # | What you'd see | Layouts | What it needs |
|---|---|---|---|
| 1 | **A picture browser.** A 7-line scrolling list of scenes or presets. The big picture on the right changes as the dial moves (Pigments, Piano, Drums...) | 40 + 21/22 | Probes L2 and L3 passing on your keyboard. A picture on every item (the stall hazard). Dial wiring. FL's script quiet: our own script, or FL closed |
| 2 | **A living home page.** Chord, key, BPM and scene, each line in its own colour, breathing on the beat. A big chord name on 14 | 12 / 13 / 14 | 12 already works (OURS). Probe L1 for mixed case. One probe for 14. Owning the screen while FL runs |
| 3 | **Eight coloured tabs that light their own buttons.** Scene palette on the buttons, with toggle and tab styles showing on/off | Labels 1-8 | Probe L6 (does a label light its button?) and L7 (settles the LED conflict) |
| 4 | **Touch-to-peek bars.** Touch a fader and see "Glow 64%" with a bar. An always-on bar for audio level or tension | 29 / 28, 30 | Probes L4 and L5. The existing `screens` probe must have your finger on the fader for 29 |
| 5 | **Title cards with big pictures.** FL logo on project load, the instrument picture on plugin focus, the metronome on a tempo change | 31, 16, 27, 15 | One probe for 16 and one for 15 (never drawn by anyone). A small map from plugin name to picture |
| 6 | **Keyboard pictures.** The current scale or split point marked on a piano drawing | 41, 42, 47 | Their fields: either Arturia's Cubase script (a download) or probes. 47 may need newer firmware |
| 7 | **A centre-split bar and a gauge** for things that swing both ways: pan, pitch bend, hue shift | 34, 35 | Field probes. Seen only in the Arturia family so far |
| 8 | **A two-column list,** chord │ numeral history, or parameter │ value | 49-52 | Firmware 1.5 or later (GUESSED) and a probe |

**Also worth a look:**
- 39 might show a colour palette.
- In Arturia mode, the same frames with `00 01 04` draw on a second, separate page. But the keyboard shows one mode at a time, and only a physical press switches modes (OTHER UNIT).

---

## B. The probe plan for the unknown screens

**Rules for every probe.**
- Run it in a later session, after you say go.
- Close FL first, so its script cannot repaint. Our tool then holds the DAW connection with `--connect`. That is the setup where you saw our frames show.
- Send one frame per question. Leave at least 60 ms between frames; in practice you will take seconds to answer.
- Everything goes through `ScreenWriter`. It already refuses 38, 43 and 44, and anything that is not a `00 02 04` screen frame.
- The receipt records your words. Today's `screen-20261023-012612.json` shows the frame but not your answer.
- **Getting the screen back:** send a known-good screen 12 frame ("OK"). Popups clear themselves. If a page sticks, press Back. A power cycle is the last resort.

Every frame below is `F0 00 20 6B 7F 42 00 02 04` + what is shown + `F7`. Text is ASCII.

### B0. Free first steps (nothing sent)

1. **Read the firmware version** on the keyboard's own settings screen, or in MIDI Control Center. Ids 47 and 49-52 probably need 1.5 or later.
2. **Read Arturia's other scripts**, with your yes for the downloads:
   - the Cubase script (3.77 MB);
   - the Logic script (654.5 KB).

   They may hold the real fields for 17-19, 32-36, 41, 42, 45 and 46. That would turn guesses into facts before we send anything.

### B1. Proven on another keyboard: prove them on yours (biggest payoff)

| Order | Probe | Frames, one per question | Your question |
|---|---|---|---|
| 1 | L2, list (20/21) | a) `14 │ 00 "SCENES" 00 │ 02 00 0A 00` b) `15 │ 00 "Tunnel" 00 │ 02 00 00 00 │ 03 00 00 00` (repeat for a few items, indexes 01, 02 and so on) c) cursor only: `15 │ 03 00 02 00` | A title? Items? A box on the 3rd item? |
| 2 | L3, picture browser (40) | a) `28 │ 00 "TYPES" 00 │ 02 00 09 00` b) `15 │ 00 "Bass" 00 │ 01 01 00 │ 02 00 00 00 │ 03 00 00 00` (types 1-9, **always with `01`**) c) cursor `15 │ 03 00 04 00` | Does the picture on the right change with the cursor? |
| 3 | L1, case | `0C │ 00 "Am vi in Db" 00 │ 01 01 00 │ 02 7F 7F 7F 00 │ 03 "Am vi in Db" 00 │ 04 01 00 │ 05 00 6C 7A 00` (needs a raw frame; `screen.f2l` upper-cases line 2) | Is line 2 lower case? |
| 4 | L4, popup with no touch (30) | `1E │ 00 "64%" 00 │ 01 "TEST" 00 │ 02 51 00 │ 04 00 6C 7A 00` | A bar popup, without touching anything? |
| 5 | L5, fader readout (29) | `1D │ 00 "64%" 00 │ 01 "TEST" 00 │ 02 51 00 │ 03 01 00 │ 04 00 6C 7A 00`, once untouched, then once while your finger rests on fader 1 | Only while touching? |
| 6 | L6, label lights its button | `08 │ 00 02 00 │ 04 7F 00 00 00 │ 05 00` (a red light, no text) | Did that button light red? |
| 7 | L7, LED path | LED id 28 in the light family, with `00 02 03` and then `04 02 03` | Which one lights it? Note: this is **not** a screen frame. It goes through the LED sender and the governor, not `ScreenWriter` |

### B2. Defined in FL but never drawn by anyone

| Order | Id | Frame to try (FL's own fields) | Your question |
|---|---|---|---|
| 8 | 14 big | `0E │ 00 "Gbmaj7" 00 │ 01 01 00 │ 02 7F 7F 7F 00 │ 03 "IV IN DB" 00 │ 04 01 00 │ 05 00 6C 7A 00` | Bigger letters? How many fit? |
| 9 | 16 | `10 │ 00 "PIGMENTS" 00 │ 01 "INIT" 00 │ 02 2D 00` (picture 45) | The Pigments picture + two lines? |
| 10 | 15 | `0F │ 00 "Bass" 00 │ 01 01 00` | Picture + one line? |
| 11 | 25, 26 | `19` with 24's fields plus `06 "LINE 3" 00 │ 07 01 00 │ 08 7F 7F 7F 00`; `1A │ 00 "Hello" 00 │ 01 4A 00` (metronome) | A three-line popup? A picture toast? |

### B3. Seen drawn on another keyboard, fields unknown

**Step one for each:** send the id with no fields (empty fields are what the other owner's sweep sent).

**Step two:** try the closest known grammar, shown below.

| Order | Id | Step two (GUESSED from the nearest known layout) | Your question |
|---|---|---|---|
| 12 | 34 | Knob fields: `22 │ 00 "+12" 00 │ 01 "PITCH" 00 │ 02 60 00`, then the same with `02 20 00` | Does the bar move from the centre, right then left? |
| 13 | 35 | `23 │ 00 "64%" 00 │ 01 "GAUGE" 00 │ 02 51 00 │ 03 01 00 │ 04 00 6C 7A 00` | Does a gauge fill? |
| 14 | 41, 42, 47 | Empty first. Then `00 "SPLIT" 00 │ 01 3C 00` (middle C) | Is any key marked? |
| 15 | 39 | Empty first. Then `00 7F 00 00 00` | Which palette? Does red appear? |

### B4. Never seen: the full guesses

| Order | Id | Frame to try (GUESSED) |
|---|---|---|
| 16 | 17 | `11 │ 00 "PIANO" 00 │ 01 "KEYS" 00 │ 02 09 00 │ 03 05 00` (two pictures, two lines) |
| 17 | 36 | `24`, same fields as 17 |
| 18 | 45 | `2D` with 25's fields (`00` to `08`) |
| 19 | 46 | `2E` with 12's fields |
| 20 | 18, 19 | Empty first, then `00 "Bass" 00 │ 01 01 00` (15's fields) |

### B5. Last, with care: these may be the keyboard's own pages

| Order | Id | How to probe it |
|---|---|---|
| 21 | **0** (screen-wide property) | `00 │ 00 7F 00 00 00`, then ask "did anything change colour?" How to undo it is UNKNOWN; screen 12 or a power cycle |
| 22 | **37, 32, 33** (welcome, rename, curve editor) | Empty frame only. **Touch nothing** while it shows: 37 may switch modes, and 33 may edit a stored velocity curve (GUESSED). Then send a screen 12 frame |

Arturia-mode (`00 01 04`) and LED-family probes need their own strict gate. Do not loosen `ScreenWriter` to allow them.

---

## C. The context-aware engine: design sketch v1

### C.1 What Arturia's script does, and what we borrow, context by context

All CODE from FL's `KL3*.py` (the context lane read them). I re-checked the refresh test, the Loop button and the plugin list.

| Context | Arturia does (keep the good idea) | We do better |
|---|---|---|
| **Channel rack** | Screen 13: channel name in its colour, plus "Pattern n". Dial = next or previous channel. Dial click opens the plugin | Same screen, change-only. Add the preset name and step page |
| **Instrument plugin** | Knobs and faders follow a fixed map of 16 parameters for ~30 FL plugins, always on the *selected channel* | Follows the **focused** plugin, including VSTs. Our own map data for FL plugins, automatic pages of 8 for the rest, the dial turns pages, labels name the page. *A mode, not the default; see C.4* |
| **Effect window** | Nothing. It still moves the selected synth | Knows the focused effect (`ui.getFocusedFormID`, `mixer.getActiveEffectIndex`) and controls it in plugin mode |
| **Mixer** | Screen 11: "n - track name" in the track colour. Faders and knobs = volume and pan of strips 1-8; they **jump**. Bank of 8 by holding button 2, stopping at strip 120 | Same name banner, plus dB and pan. Faders stay unbound (your ruling). Banks beyond 120 |
| **Browser** | Dial browses, screen shows the item and tab | Same, later a native list (screen 20) if L2 passes |
| **Playlist, piano roll** | Nothing new on screen | Bar : beat, tempo, loop mode, snap |
| **Transport row** | Play, stop, record, tap, metronome, rewind/fast-forward, save, undo/redo | **Keep, with FL in charge (your ruling).** Loop is loop-*record* in Arturia's script (`FPT_LoopRecord`, `KL3Process.py:646`): you choose |
| **Pads** | Pads 1-8 **always** write steps into the selected pattern. Pads 9-12 pick the step page | Steps only in a chosen step-sequencer mode with a lit tab. Otherwise the hub owns the pads (D7) |
| **Touch** | Touching a knob or fader shows its parameter (28/29) | Shows **whatever that control is bound to**: an FL link ("Reverb Mix 40%"), a hub binding ("Glow 64%") or "free" |
| **Start-up** | Card 31: "<project> / Connected" with the FL picture | Keep. Add the project title on every load |

**What else we do better:**
- **Test each refresh flag one at a time.** Arturia compares the whole number to exactly 4 or exactly 4096, so it repaints on almost every refresh.
- **Paint only what changed, with a clear order.** Each context has a resting screen. Popups sit on top for their time, then the resting screen returns. Arturia instead repaints everything and turned its own popups off.
- **Name your FL links on the screen** (`device.getLinkedParamName` and `getLinkedValueString`).
- **Show FL's own hint text** (`OnSendTempMsg`), as Image-Line's Mackie script does.
- **Turn non-ASCII names into ASCII** (`screen.ascii_clean`) instead of showing ".Undefined text.".
- **Leave Arturia's bugs behind:**
  - Three missing commas fuse four plugin names into one, so BassDrum, Fruit kick, MiniSynth and PoiZone get no preset buttons (`KL3Plugin.py:135-138`, re-checked).
  - Quantize hides the piano roll.
  - The dial closes every plugin window.
  - The Play LED follows the song position, not whether the song is playing.

### C.2 The architecture

```
KeyLab DAW port ──► FL: device_AuroraKeyLab.py (ours, thin)
   (shared, OURS)      transport → FL · builds the context record · runs FL commands
        │              paints only in "FL drives" mode (its own governor)
        └─────────► Hub (arsenal/keylab): modes, screen compositor, lights,
                       bindings, the one governor; the only painter in "Aurora drives"

FL script ◄── "Aurora Link" loopback MIDI port ──► Hub
              context reports (changed fields only, < 1000 bytes)
              heartbeat hub → script every 0.5 s · commands hub → script
```

**The FL side.**
- It replaces Arturia's script on the DAW port only. Arturia's files stay untouched, and switching back is one dropdown (D8 R8.7).
- Arturia's MIDI-port script can stay, to keep forwarding to Arturia plugins.

**The context record.**
- Built from `OnRefresh` (one flag at a time), `OnDirtyChannel`, `OnDirtyMixerTrack` and `OnSendTempMsg`.
- A slowed-down `OnIdle` acts as a safety net. Its real rate is disputed (10 to 50 ms, and one report of it never firing), so we measure it.
- Guard against feedback loops: reading parameter names can cause a false "focused window" refresh (NI's script hit this).
- Preset names arrive one tick late.

**Faders.**
- By default the script leaves fader events unhandled, so FL's own **Link to controller** works. That matches your words "so I can link them to whatever".
- The hub binds them only when you ask.
- Touching a fader tells you which side owns it.

**The link.**
- MIDI only. Sockets and threads are reported blocked inside FL's Python, and file access is disputed.
- There is **no loopback port on this machine today** (context lane, seen today). Adding one needs your OK.

**Fallbacks:**
1. **Hub silent for 2 s:** the script paints a basic FL view ("FL drives"), and hands back when the hub returns (D8 R8.5).
2. **No loopback at all (design A):** the script does everything itself, and the hub stays off the screen. One possible link-free switch: a screen-button press seen by both sides. That needs a check that the hub receives DAW-port input while FL has the port open. P1 proved only the *output* side is shared.

### C.3 Risks

1. **FL freezes.**
   - Bug #22368 is **fixed** in your build, 26.1.3 (re-checked in FL's local WhatsNew).
   - The live risks are #22604 ("freeze when a script sends a sysex message") and #22725 / #22689 (freeze and crash in GlobalTransport). They were fixed in **26.1.7, 1 Oct 2026** (re-checked on the Image-Line forum).
   - Arturia's script already does both, every day.
   - My recommendation, your call: update before we ship.
   - Our design cuts the exposure: in "Aurora drives" the FL script sends **no** screen SysEx, because the hub paints through the shared port.
   - The P23 drill must test bursts of SysEx and GlobalTransport calls specifically.
2. **Two painters on one screen.** FL's repaint covers ours (TODAY). Only one writer per mode is allowed, and the screen shows which one is live (R8.3).
3. **Bursts.**
   - About 36 messages froze the keyboard (OURS).
   - Arturia sends about 40 per refresh and has not been reported to freeze. Why: UNKNOWN (maybe spacing).
   - Every sender goes through 12 per 100 ms (R8.4).
4. **FL API traps** (CODE, NI's and Maddy Guthridge's scripts):
   - "Operation unsafe at current time" errors;
   - effect changes FL does not report;
   - VSTs report 4240 parameters, so list the named ones once and keep the list.
5. **Licences.** Arturia's enum files say "all rights reserved"; UCS is GPL; the stubs are LGPL. We take facts only, and write our own code (R8.1).

### C.4 Disagreements to settle with you

**Knobs by default.**
- Your words covered faders: "the fades for mixer is dumb, i want them unassociated".
- D8 R8.2, a draft you have not yet approved, makes **knobs** unbound by default too, with "knobs follow the focused plugin" as an optional binding.
- The context lane wanted knobs to follow the plugin by default.
- I kept D8's wording. Your call.

### C.5 The first three slices

**Slice 1: a quiet replacement (design A, no loopback needed)**
- **What it is:** `device_AuroraKeyLab.py` with:
  - transport to FL;
  - faders and knobs left unhandled;
  - pads not writing steps;
  - connect on load, disconnect on unload;
  - one resting screen (13: channel + pattern);
  - flags tested one at a time, change-only, governed.
- **Before it ships:** P23 on every FL call it makes, and your FL-version decision.
- **Acceptance:**
  - (a) A checksum list shows Arturia's folder unchanged after install and after uninstall. Switching back is one dropdown.
  - (b) You press each transport button and FL responds (video).
  - (c) Fader 1 does nothing until you link it in FL. Then it moves the linked control.
  - (d) Pads 1-8 change no steps.
  - (e) The send log shows 0 frames while nothing changes, and never more than 12 per 100 ms.
  - (f) A 30-minute session with no freeze.

**Slice 2: the context record and resting screens**
- **What it is:**
  - a window decode that includes effects;
  - plugin name and preset;
  - a resting screen for each context;
  - popups with timers;
  - FL's hint text;
  - touch-to-peek that names FL links.
- **Acceptance:**
  - (a) A scripted walk through the channel rack, mixer, playlist, piano roll, browser and an effect window. The right screen shows each time (your eyes plus the logged record).
  - (b) Touching a fader linked to an FL control shows that control's name and value.
  - (c) For 10 s after a focus change, refreshes settle (no loop).
  - (d) After a preset change, the new name shows within 2 ticks.
  - (e) An accented track name shows cleaned, not ".Undefined text.".

**Slice 3: the link and the handoff (design C; needs the loopback and your OK)**
- **What it is:**
  - the Aurora Link port;
  - context reports;
  - the heartbeat;
  - the hub composing chord/scene plus FL context;
  - "FL drives" as the fallback.
- **Acceptance (D8.2):**
  - (a) With the hub running, the screen shows chord, BPM and FL's channel name.
  - (b) Kill the hub: within 2 s the script paints FL's view. Restart the hub: it hands back.
  - (c) A monitor log shows frames from only one writer at a time, and the screen names the live writer.
  - (d) With FL open, a fader moves a First Light setting through the hub.

**Slice 4 candidate:** the picture browser for presets and plugin pages, once L2 and L3 pass.

---

## Checks, corrections, and where the two research lanes disagreed

**What I re-checked myself:**
- FL's `ScreenId.py` list.
- Which ids FL's script really draws (grep of every caller).
- The refresh test, `flags not in [4,4096]`.
- `FPT_LoopRecord` on the Loop button.
- The missing commas in the plugin list.
- FL's text rules (`KL3Display.py:26-47`).
- The label tags (`KL3Buttons.py:62-90`).
- Our `screen.py` gate and encoders.
- The P1 receipt.
- The FL changelog lines for 26.1.3.
- The 26.1.7 forum fix list.
- The protocol document's list, touch, label, LED and pacing facts.

**Where the two lanes disagreed:**
1. **Lists 20-22 and 40.** The context lane said "never drawn by anyone". The screen lane said they are worked out on another keyboard. **The screen lane is right**: the document measured them. They are still unproven on yours.
2. **Line length.** The context lane said "31 characters a line". **That is FL's own cut, not the keyboard's limit.** Each layout's real limit is unknown.
3. **Id 9 "clear all".** The context lane and surface map row Y6 list it as usable. Its fields are **unknown**, and FL's call to it sends nothing.
4. **Screen-button lights.** FL and Bitwig address them as LED ids 21-28. The other owner found no response there. **Unresolved until probe L7.**

**Corrections the repo needs** (not made; research only):
- Surface map **Y5** says FL draws 0, 14, 15, 16, 25, 26 and 30. **It never calls them.**
- Surface map **Y8** is out of date. 20, 21, 22 and 40 are worked out on another keyboard, and 34, 35, 37, 39, 41 and 42 have been seen drawn. Ids 47 and 49-52 also exist.
- README line 51 credits the upper case to the firmware. It is FL's script.
- W266 and D8 call #22368 a 26.1.3 bug. **It is a 26.1.3 fix.** The live risks are #22604, #22725 and #22689.
- Probe `screens` draws 29 with nothing touched, so it can wrongly read "not seen".
- Today's two observations need receipts.

**Lane reports, full text:**
- `<session scratchpad>/lcdctx/lcd-report.md`
- `<session scratchpad>/lcdctx/context-report.md`

**Key local sources:**
- `C:/Users/L5/Documents/Image-Line/FL Studio/Settings/Hardware/Arturia KeyLab mk3/`
- `E:/AI-Setup/arsenal/keylab/screen.py`
- `E:/AI-Setup/arsenal/keylab/README.md`
- `E:/AI-Setup/arsenal/keylab/probe.py`
- `E:/AI-Setup/research/reviewed/keylab-liberation-2026-10-22/keylab-full-surface-map-2026-10-23.md`
- `E:/AI-Setup/docs/library/design/20261022_a16-d8-fl-script-handoff_3384d8.md`

**Web sources:**
- The protocol document: github.com/saxofonbrian/keylab-mk3-sysex @6321b072a1
- FL 2026.1.7 fixes: forum.image-line.com/viewtopic.php?t=342646
