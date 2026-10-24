# The KeyLab mk3 LCD in full: the screen lane's report (verbatim)

Workflow run wf_05ceb8e4-91d (task w34xc5hn9), 2026-10-24. Research only: nothing was sent to the KeyLab.
Daniel (verbatim, 2026-10-24): "can't we make our own context aware engine that borrows from the default script? perhaps we can make it better. what can we write to the LCD? what are the full functionalities afforded us there?"
Local scratch paths shortened; third-party code was read for facts only.

---

Report written to <session scratchpad>/lcdctx/lcd-report.md (full text below).

# The KeyLab 88 mk3 screen, in full: every way to drive it, and what each screen id takes

> Lane report, 2026-10-24, written for Daniel's question: "what can we write to the LCD? what are the full
> functionalities afforded us there?" Research only. **Nothing was sent to the keyboard**, nothing in the repo or in
> Image-Line's folder was changed, and no file was downloaded. GitHub sources were read as text over the network and
> nothing was saved. Two Arturia guide PDFs were saved automatically by the web-fetch tool into the session's
> tool-results folder and read there.
> No third-party code is copied here. Byte layouts and numbers are facts, and each one cites where it came from.

## The answer in one minute

The screen draws **firmware layouts, not pixels.** We pick a layout by its number (the "screen id") and fill in
tagged fields. A field can carry ASCII text, a 0-127 number (a bar position, an icon number, a style), or an RGB
colour with 0-127 per channel. On this machine and in public sources, that adds up to:

- **Pages that stay up**: one line, two lines, two big lines, an inverted look for each, and an icon with one or two
  lines (ids 10-16). Line 1 and line 2 each get their own colour on the colour layouts.
- **Popups over the page** that go away by themselves: one, two or three lines, an icon on the left with one or two
  lines, a big icon on top with two lines (the "Connected" card), and a general-purpose popup (ids 23-27, 30, 31).
- **Live parameter readouts** with a name, a value and a 0-127 bar for knobs and faders (ids 28, 29). On another
  user's unit the fader readout appears **only while a finger is on the control**. A centre-split bar
  (pitch wheel, id 34) and a gauge (id 35) were seen drawn in a sweep on another user's unit.
- **Real scrolling lists**: 7 visible lines with a cursor box and a scrollbar, items pushed in at the top or the
  bottom, about 34 characters per line, white or blue text per item, and an optional icon panel that shows the
  highlighted item's big icon (ids 20, 21, 22, 40). Recent firmware also has a 5-line two-column list
  (ids 49-52, from Arturia's MainStage script). None of this is in FL's script. It is fully worked out in an
  MIT-licensed community document measured on a KeyLab 88 mk3.
- **Eight screen-button labels**, each with a style (plain, toggle, tab, icon), a small icon, an RGB colour and up to
  two or three short text lines. The label's colour also **lights that button's LED**.
- **108 built-in pictures**: 86 large icons (Arturia logo, 15 instrument types, 44 Arturia instruments, 26 UI symbols)
  and 22 small ones for labels (arrows, mute, solo, arm, play, stop, heart, search, mixer and so on).
- **Device pictures seen in sweeps but not yet mapped**: a welcome screen (37), a colour palette or picker (39), and
  three keyboard drawings (41, 42, 47).
- **A second canvas**: while the keyboard is in Arturia mode, the same kind of frames with family byte `01` instead
  of `02` draw on Arturia mode's own page, with no Analog Lab running.

What we **cannot** do:

- Draw raw pixels, upload images or choose fonts. No such command exists in any integration, and the pictures are
  baked into the firmware's assets image.
- Set how long a popup stays up. No source has a timeout field.
- Dim the screen from a live frame. Brightness (0-100) is a device setting, not a screen field.

The safe frame rate seen so far is one screen frame per 60 ms. Two screen frames sent back to back can collide on
the device.

---

## How to read the confidence labels

Every fact carries one of three labels:

- **CONFIRMED**: seen on Daniel's unit, with a repo receipt. Only a few screen facts are this strong.
- **READ FROM CODE**: read from a named file. This covers code (Arturia's FL, Bitwig, Ableton and Analog Lab files,
  and strings in the firmware image) and written protocol documents. When a document says its author **measured** a
  fact on their own KeyLab mk3, the label says "(measured on their unit)". That is stronger than code, but it is
  still not our unit.
- **GUESSED**: inferred from names or patterns. Nothing observed backs it.

There are two kinds of gap below: a field layout nobody has published (UNKNOWN), and two sources that disagree
(CONFLICT).

## Sources (what was read, where, under what licence)

| Short name | Where | Licence and status |
|---|---|---|
| FL | `C:/Users/L5/Documents/Image-Line/FL Studio/Settings/Hardware/Arturia KeyLab mk3/` (KL3Display, KL3Pages, KL3Buttons, KL3Return, KL3Navigation, KL3Process, KL3Plugin, KL3Connexion, ScreenId, images_sub_enums, LedId, ParamId, IntegrationPatchId, device_KL3) | Arturia's own script. Files say "Copyright (c) 2024 Arturia" and carry Ray Juang's MIT headers. Read in place. |
| Bitwig | github.com/bitwig/bitwig-extensions @ `1a5951b95e` (2025-10-26), `src/main/java/com/bitwig/extensions/controllers/arturia/keylab/mk3/` | MIT (repo licence). This is the official Bitwig extension for the KeyLab mk3. |
| Live | github.com/chiakibeats/AbletonLive12.1_MIDIRemoteScripts @ `2c04903d6e`, `KeyLab_mk3/` (display.py, midi.py, elements.py, mappings.py) | Decompiled from Ableton Live 12.1. The bytecode timestamp is 2025-03-17. Some bodies are partial. The repo has no licence, so it is read for facts only. A second decompile (gluon/AbletonLive12_MIDIRemoteScripts @ `e83d5192f3`) has only 3 of the files. |
| SB-doc | github.com/saxofonbrian/keylab-mk3-sysex @ `6321b072a1`, `keylab-mk3-sysex.md` | MIT. A reverse-engineered KeyLab 61/88 mk3 screen protocol. Its sources are Arturia's MainStage `config.lua`, an Analog Lab MIDI log and the author's own hardware. Every claim is marked measured, code, unverified, guess or rejected. |
| SB-live | github.com/saxofonbrian/KeyLabLive @ `b7100d7cbc`, `KeyLabLive/keylab_screen.py` | MIT. A working Ableton Live script that draws lists and readouts with this protocol. |
| AL | `C:/ProgramData/Arturia/Analog Lab V/resources/controllers/` (`controllers.prefmidi.xml`, `controllers-common.prefmidi.xml`, `browser/KeyLab mk3-generated.xml`) and class or method names in `C:/Program Files/Common Files/VST3/Analog Lab V.vst3` | Arturia's own Analog Lab definitions. Read in place. |
| FW | `C:/Users/L5/Downloads/KeyLab3_FW__1_5_0.kl3` (firmware 1.5.0, built 2026-05-06; a zip holding a gigadevice, an iochip and an assets image for each of the 49 / 61 / 88) | Printable strings only, from the 49's image (offsets below). The same parser strings appear in the 88's image (for example `unknow screen Id in SysEx42 Display` at 0x58efb0). |
| MCC | `C:/ProgramData/Arturia/MIDI Control Center/Resources/KeyLab3 88.json` | Arturia's device definition. |
| Guides | The FL DAW User Guide PDF in FL's folder (6 pages; nothing about the screen), the MainStage and Logic integration guides (dl.arturia.net), the KeyLab mk3 user manual (manualslib summary) | Arturia's. |
| Repo | `arsenal/keylab/screen.py`, `arsenal/keylab/README.md`, `research/reviewed/keylab-liberation-2026-10-22/keylab-full-surface-map-2026-10-23.md`, `state/arsenal/keylab/receipts/screen-20261023-012612.json` | Ours. |

**Not read** (each needs a download, which needs Daniel's yes): Arturia's **Cubase script**
(`KeyLab_mk3_Cubase_Daw_Integration_Script_1_1_0.zip`, 3.77 MB; Cubase MIDI Remote scripts are JavaScript),
the **Logic Pro script** (`KeyLab_mk3_Logic_Pro_Daw_Integration_Script_1_1_0.zip`, 654.5 KB), the **MainStage
script** (`KeyLab_mk3_Mainstage_Daw_Integration_Script_1_1_0.zip`, 1.07 KB, whose `config.lua` SB-doc already read),
and the **newest firmware 1.5.1** (2026-10-16, 7.2 MB). All are listed on
arturia.com/support/downloads-manuals/product/keylab-88-mk3. The Cubase script is the most likely place to find the
field layouts nobody has published yet. No Studio One, Reaper or Pro Tools script exists on that page.

---

## 1. How a screen frame is built

### 1.1 Envelope and families

- Every frame is `F0 00 20 6B 7F 42 | 00 <patch> 04 | <screen id> | <fields> | F7`.
  - The envelope is **CONFIRMED** (README "Envelope" and "Screen" rows, 2026-10-22).
  - The layout is **READ FROM CODE**: FL `KL3Dispatch.py` send_to_device and `KL3Display.py:22`; Bitwig
    `display/SysExBuilder.java:8`; Live `midi.py:8-10`.
- The byte `04` is the "display" parameter: `eParamId.eDisplay = 4` (FL `ParamId.py`). The other parameters are
  0 properties, 3 set LED, 5 connection, 6 bank, 7 program and 8 soft connection. **READ FROM CODE.**
- `<patch>` picks the world. FL `IntegrationPatchId.py` lists 1 Arturia, 2 DAW and 13 V Collection.
  - **`00 02 04` (DAW) is the one we use.** **CONFIRMED** (2026-10-22 receipts).
  - **`00 01 04` (Arturia)**: Analog Lab sets `patchid_global="1"` with `type="lcd" version="3" subcommandid="4"`
    (AL `controllers.prefmidi.xml:204-209`). **READ FROM CODE.**
  - **`00 0D 04` (V Collection)**: the V Collection instruments' copy sets `patchid_global="13"` with the same lcd
    action (AL `controllers-common.prefmidi.xml:216-221`). That this frame draws: **GUESSED**.
- The families are isolated. Frames for one are ignored while the other's page is on screen, in either order. The
  family follows the keyboard's mode (Prog + screen button), and no SysEx switches modes. **READ FROM CODE**
  (SB-doc:40-46 and 58-74, measured on their unit). Our README agrees that no SysEx switches modes.

### 1.2 Fields

- A field is `<tag> <value bytes> 00`.
- The firmware parser knows three value types, from its error strings: numbers ("Numerical param is too short"),
  colours ("Color param is too short") and strings ("Couldn't parse string parameter").
- On an unknown tag it gives up on the rest of the frame: "unknow parameter in display / button / screen properties
  / append prepend of SysEx42 Display, stopping parser...". An unknown screen id gets "unknow screen Id in SysEx42
  Display". **READ FROM CODE** (FW 0xc2218-0xc2400). What the screen then shows (the fields parsed so far, or
  nothing): **GUESSED**.
- **Number**: one byte, 0-127. List indexes and lengths take two bytes, high byte first (`<hi> <lo>`, 14 bits).
  **READ FROM CODE** (SB-doc:383-385; SB-live `_len_bytes`, `keylab_screen.py:236-239`).
- **Colour**: exactly three bytes R G B, each 0-127. FL halves 8-bit colours (`KL3Return.py:485-499`). Live, Bitwig
  and SB do the same. **READ FROM CODE.**
- **String**: ASCII bytes, ended by the field's `00`. A NUL inside a string therefore ends the field early.
  **READ FROM CODE.**
- **Fields are optional and order is mostly free.**
  - Arturia's own Live script never sends the colour-type tags: it sends tags 00, 02, 03 and 05 on two-line screens,
    and 00, 01, 02 and 04 on readouts (Live `midi.py:19-37`).
  - FL always sends them. Bitwig numbers tags by position and skips a number when an icon is absent
    (`SysExBuilder.java:29-55`).
  - **READ FROM CODE.** SB-doc warns that extra or missing fields "make parsing fragile". It saw roughly 1 frame in
    30 fail until it copied Arturia's exact field set (SB-doc:254-261, measured on their unit).
- The largest frame the device accepts is **UNKNOWN**. The firmware has a "Sysex message was too long" check
  (FW 0xb33f0).

### 1.3 What the firmware calls its pages

The firmware's widget manager holds five page kinds: `kl3::GenericFullscreen`, `kl3::EmptyScreen`, `kl3::BigPopup`,
`kl3::SmallPopup` and `kl3::WidePopup`, with `max_page_size = 284` (FW 0xc0eb4-0xc117c). It also has list logic
("Current page is not a list, append cancelled", "No list setup before list append or prepend", "Not 2 list setup
before title change", FW 0xbef10, 0xc2388, 0xc2424) and image loading by index ("Couldn't load image with index",
"Widget's size and the icon's size are different", "unknow icon", FW 0xc1e64, 0xc1e84, 0xc0de4). **READ FROM CODE.**
Which screen id uses which page kind: **GUESSED**.

---

## 2. Every screen id, one by one

Tags are hex. "c-type" is the colour-type byte. The screen-id list is FL `ScreenId.py:26-74`; the firmware has
more, see 47-52.

| Id (hex) | FL name | What it draws | Fields | Who uses it | Timing, colour, icon | Confidence |
|---|---|---|---|---|---|---|
| 0 (00) | eScreenProperties | Screen-wide properties | `00` colour (3 bytes) | Defined in FL (`KL3Display.py:91-99`) but **never called**: no SetCenterPage(0,...) caller. Bitwig and Live never use it. The firmware has its own parser for it (FW 0xc22f4) | Meaning **UNKNOWN**. A global accent or background colour is a **GUESS**. It is not brightness (see 5.3) | READ FROM CODE (fields); meaning GUESSED |
| 1-8 | eButton5-8 = 1-4, eButton1-4 = 5-8 | Screen-button labels | See section 6 | FL, Bitwig, Live, AL, SB | Colour also drives the button LED | READ FROM CODE; LED effect measured on their unit |
| 9 (09) | eButtonsClear | Clear labels | **UNKNOWN**. The firmware has "unknow button to clear" (FW 0xc177c) | Nobody. FL's "clean" helper sends a different frame and is never called (`KL3Navigation.py:359-360` has no caller) | (none) | Grammar UNKNOWN. Use SB's per-label reset (section 6) |
| 10 (0A) | eScreen1L | One line, full screen | `00` text, `01` c-type, `02` colour | FL "No Selection" with c-type 0 and black (`KL3Return.py:470-474`) and at `KL3Navigation.py:283`. Bitwig names it and never draws it | Stays up | READ FROM CODE |
| 11 (0B) | eScreen1LInverted | One line, inverted | Same as 10 | FL `KL3Return.py:359` | Stays up. What "inverted" looks like: **GUESSED** (inverse video, a colour band) | READ FROM CODE |
| 12 (0C) | eScreen2L | Two lines, full screen, a colour per line | `00` line 1, `01` c-type, `02` colour, `03` line 2, `04` c-type, `05` colour | FL `KL3Navigation.py:291`; our `screen.py` live readout | **Stays up, no flicker; a 60 ms colour cycle rendered cleanly** | **CONFIRMED** (README, 2026-10-22: "beautifully, flawlessly rendered, 0 ficker!") |
| 13 (0D) | eScreen2LInverted | Two lines, inverted. The main "home" page of all three DAW scripts | Same as 12. Live sends only `00 02 03 05` | FL channel and pattern page (`KL3Return.py:460-468`); Bitwig track and scene page (`ContextScreen.java:330-334`); Live home page (`display.py:126`, `midi.py:27-29`) | Live caps **line 1 at 17 characters and line 2 at 30** (`display.py:12-13`), Arturia's own choice for this layout. Line 1 carries the track colour | READ FROM CODE |
| 14 (0E) | eScreen2LBig | Two lines, big type | Same as 12 | FL defines it (`KL3Display.py:166-180`) and never calls it. Bitwig names it and never uses it | Large type. How many characters fit is **UNKNOWN** | READ FROM CODE (fields); never seen drawn |
| 15 (0F) | eScreenLI_1L | Large icon on top + one line (Bitwig `TOP_ICON_1_LINE`) | `00` text, `01` large icon | Defined in FL, never called. Bitwig names it | No colour fields: FL takes a colour and drops it | READ FROM CODE |
| 16 (10) | eScreenLI_2L | Large icon on top + two lines (Bitwig `TOP_ICON_2_LINES`) | `00` line 1, `01` line 2, `02` large icon | Defined in FL, never called | No colour fields | READ FROM CODE |
| 17 (11) | eScreen2LI_2L | By its name, **two large icons + two lines** | **UNKNOWN**. Following 16, `00` line 1, `01` line 2, `02` icon 1, `03` icon 2 is a **GUESS** | Nobody. The SB sweep reports nothing visible for 0x11 with empty fields | (none) | UNKNOWN |
| 18 (12) | eTypeCarousel | By its name, a scrolling **carousel of instrument types** | **UNKNOWN** | Nobody in any source read. The names match Analog Lab's "browse by Type" and "browse by Instrument". The large-icon set has exactly those two families: types 1-15 and instruments 16-59 | That it scrolls a row of type icons with a name under the centre one is a **GUESS**. Today's Analog Lab draws its Types and Instruments filters as **lists with an icon panel** instead (SB-doc:587-590, from an Analog Lab log), so the carousels may be legacy (**GUESSED**) | UNKNOWN |
| 19 (13) | eInstrumentCarousel | Carousel of instruments | **UNKNOWN** | Nobody | As 18 | UNKNOWN |
| 20 (14) | eScreenListSetup | **List title, one full-width column, no icon panel** (Analog Lab's GENRES list). Also opens or resets a list | `00` title text, `02` `<hi> <lo>` total item count, which frames the cursor and scrollbar. A title sent alone **resets** the list | Analog Lab (in `00 01 04`); SB-live in `00 02 04` (`keylab_screen.py:320-324`) | **7 visible lines, about 34 characters per line, cut not wrapped.** In this list the top-row labels cost no lines | READ FROM CODE (SB-doc:357-460 and 596-619, measured on their unit; SB-live). Firmware: "No list setup before list append or prepend" |
| 21 (15) | eScreenListAppend | **Push an item in at the bottom**; also moves the cursor | Item: `00` text, `01` large icon (needed with title 40, see below), `02` two bytes whose first byte is the text colour (0 white, anything else blue; the second byte has no visible effect), `03` `<hi> <lo>` the item's index. **Cursor only**: `03 <hi> <lo>` alone | Analog Lab; SB-live (`keylab_screen.py:327-352`) | **The firmware never scrolls by itself.** The view shows the last 7 items pushed. To scroll, push one item at the end you move toward, then send the cursor. The cursor number is not the screen line: the firmware puts the box on line 4, except near either end of the list (SB-doc:431-454 gives the formula) | READ FROM CODE (measured on their unit). Firmware: "Current page is not a list, append cancelled" |
| 22 (16) | eScreenListPrepend | Push an item in at the top | Same as 21 | SB-live | Once switched off a button LED during a sweep (SB-doc:459-460, not retested) | READ FROM CODE (measured on their unit) |
| 23 (17) | eScreenPopup1L | One-line popup | FL: `00` text only (FL takes a colour and never sends it) | FL snap, route and similar hints (`KL3Navigation.py:157-184`); Bitwig names it | **Goes away after about 1 s** | **CONFIRMED** ("Hello Daniel flashed for 1 second", README 2026-10-22) |
| 24 (18) | eScreenPopup2L | Two-line popup | As 12, tags `00`-`05` | FL "Track Position / Bar n Step m", repainted on every idle tick while Rewind or Fast-forward is held (`KL3Return.py:285-293`); Bitwig "Arrangement / ...", "Launcher / Clip Quantized" (`KeylabMk3ControllerExtension.java:167-184`); Live 2-line notifications, line 2 capped at 21 characters (`display.py:14, 81`) | Times out by itself (FL keeps repainting it). How long: **UNKNOWN**, about 1 s is likely (**GUESSED** from 23) | READ FROM CODE; README groups 24 and 25 with 23 but quotes a receipt for one popup only |
| 25 (19) | eScreenPopup3L | Three-line popup | As 24, plus `06` line 3, `07` c-type, `08` colour | Bitwig "Mixer Control / Track 1 - 8 / Main encoder to offset" (`ContextScreen.java:295-301`); Live "Mixer Control / range / HOLD TO OFFSET" (`display.py:96, 102`) | Popup | READ FROM CODE |
| 26 (1A) | eScreenPopupLI_1L | Popup: icon on the left + one line (Bitwig `POP_SCREEN_1_LINE_LEFT_ICON`) | `00` text, `01` large icon | Defined in FL, never called. In the Arturia family the SB sweep saw "popup, right-aligned text", which fits a left icon | Popup | READ FROM CODE |
| 27 (1B) | eScreenPopupLI_2L | Popup: icon on the left + two lines | `00`-`05` as 24, `06` large icon | FL Metronome, Tap Tempo, Step Position, controls cards (`KL3Navigation.py:198-265, 324-333`); Bitwig device name with an icon (`ContextScreen.java:314-316`) | Popup. **The only popup FL draws with an icon** | READ FROM CODE |
| 28 (1C) | eScreenKnob | **Knob readout**: name, value text and a 0-127 bar | `00` **value text**, `01` **name**, `02` bar 0-127, `03` c-type, `04` colour. FL notes the swapped order: "Line 1 and 2 inverted to respect the order in popup". Live and Analog Lab leave out `03` | FL plugin and pan readouts (`KL3Process.py:783-793`, `KL3Navigation.py:73-80`); Bitwig on touch (`TouchControl.java:43-45`); Live (`midi.py:19-21`) | Arturia's colour is (0, 108, 122), "Analog Lab blue". Probably drawn only while a finger is on a control, like 29 (**GUESSED**). SB found 28 used for faders "made things worse, lag and more missing updates" (SB-doc:315-317) | READ FROM CODE |
| 29 (1D) | eScreenFader | **Fader readout** | Same as 28 | FL, Bitwig (`TouchSlider.java:30-32`, which sends `0x1C + 1`), Live, SB-live | **Draws only while skin is on a fader or knob.** The touch sensor is capacitive: a fingernail or paper gives no touch CC and no readout. Sent with nothing touched, nothing appears (SB-doc:212-219; SB-live `keylab_screen.py:164-167, 184-193`). Arturia's Live script sends about 44 readouts a second without trouble (SB-doc:333-334) | READ FROM CODE (measured on their unit) |
| 30 (1E) | eScreenPad | **"Pad" popup, the general-purpose one** | `00` value text, `01` name, `02` 0-127, `04` colour. FL sends `03 04` before `02` (`KL3Display.py:341-353`); SB sends `00 01 02 04` | Defined in FL, never called. SB-live uses it for every message it raises on its own (`keylab_screen.py:192-193, 272-283`) | **Draws whenever it is sent, no touch needed** (measured on their unit). Whether the colour field does anything is unverified (SB-doc:303-304). Bitwig's enum calls 0x1E "POP_UP_FADER", but its code never uses that entry | READ FROM CODE |
| 31 (1F) | eScreenPopupFull | **Big icon on top + two lines**: the "Connected" card | `00`-`05` as 24, `06` large icon | FL "<project> / Connected" with the FL icon 71 (`device_KL3.py:91-100`); Bitwig "Bitwig / Connected" with icon 64 (`MidiProcessor.java:139-143`); Live "Ableton Live / Connected" with icon 60 (`display.py:77`) | Popup | READ FROM CODE |
| 32 (20) | eScreenRename | By its name, a **rename** (text-entry) screen | **UNKNOWN** | Nobody. The firmware has a device-side rename menu ("RENAME", "No callback registered for rename menu", FW 0xbef40, 0xbf350) | That it is the device's own program-rename editor, possibly interactive, is a **GUESS** | UNKNOWN |
| 33 (21) | eScreenCurveEditor | By its name, a **curve editor** | **UNKNOWN** | Nobody. The firmware has curve settings: "CUSTOM CURVE", "GLOBAL CURVES", "VELOCITY CURVE", "AFTERTOUCH CURVE" (FW 0xbe9f8-0xbfcc4) | That it is the velocity and aftertouch curve editor from the device's Settings menu is a **GUESS** | UNKNOWN |
| 34 (22) | eScreenPitchWheel | A **bar split at the centre**, with arrows | **UNKNOWN**. Following 28, a name, a value and a 0-127 position with 64 at the centre is a **GUESS** | Nobody. In the Arturia family the SB sweep saw "popup with a half-filled bar and arrows" for 0x22 (SB-doc:636) | Popup | Drawing seen (their unit); grammar UNKNOWN |
| 35 (23) | eScreenParamGauge | A **parameter gauge** | **UNKNOWN** | Nobody. In the Arturia family the SB sweep saw "empty bar with arrows" for 0x23 (SB-doc:637) | Popup | Drawing seen (their unit); grammar UNKNOWN |
| 36 (24) | eScreenIcon2Sides | By its name, **icons on both sides** | **UNKNOWN** | Nobody. Analog Lab has a "two-line screen with icon-left" component ("Delete Part 2?" with a delete icon, AL `KeyLab mk3-generated.xml:53`), which could be 36 or 27 | (none) | UNKNOWN |
| 37 (25) | eScreenWelcome | The **welcome screen** | **UNKNOWN** | Nobody. The SB sweep saw "welcome screen" for 0x25 in both families (SB-doc:639, 667). The device's own welcome page is in the firmware: "WELCOME, WHAT DO YOU WANT TO DO ?", "Control your Digital Audio Workstation", "Control an Arturia plugin", "SHOW THIS SCREEN AT LAUNCH" (FW 0xc09cc-0xc1d10) | **Caution**: the device's own welcome page lets its buttons pick a mode. If ours is that page, pressing a button while it shows may switch modes (**GUESSED**) | Drawing seen (their unit); grammar UNKNOWN |
| 38 (26) | eScreenBoot | Device boot | **Never send.** Our gate refuses it | (In the Arturia family the SB sweep sent 0x26 and saw "clears the screen", SB-doc:629. We keep our rule) | (none) | READ FROM CODE |
| 39 (27) | eScreenColorPicker | A **colour picker or palette** | **UNKNOWN** | Nobody. The SB sweep saw "colour palette at top left, unexplored" for 0x27 (Arturia family) and "colour picker" (DAW family) (SB-doc:640, 668) | That it shows the device's stored pad palette (MCC keeps 42 colours) is a **GUESS** | Drawing seen (their unit); grammar UNKNOWN |
| 40 (28) | eScreenBrowser | **List title with an icon panel on the right**: the browser | `00` title, `02` `<hi> <lo>` count; then items via 21 or 22, **each carrying `01 <large icon>`** | Analog Lab's preset and instrument browser (in `00 01 04`); SB-doc in `00 02 04` | 7 lines. The panel shows the large icon of the item under the cursor and changes as the cursor moves. **With this title, items without an icon make the keyboard stop sending MIDI for about 60 ms in every 100 while a fader readout is drawn**; title 20, or icons on every item, avoids it (SB-doc:322-355, measured on their unit) | READ FROM CODE (measured on their unit) |
| 41 (29) | eScreenLineKeyboardPopup | Keyboard drawing (popup variant) | **UNKNOWN** | Nobody. The SB sweep saw "grey keyboard icon at the top with a heading" (DAW family) and "clears the page, leaves a piano icon" (Arturia family) | That it shows key ranges or a split point (Analog Lab has a "Split Point :" popup and per-part low/high note parameters in orange and green) is a **GUESS** | Drawing seen (their unit); grammar UNKNOWN |
| 42 (2A) | eScreenLineKeyboard | Keyboard drawing | **UNKNOWN** | Nobody. The SB sweep saw "grey keyboard icon in the middle" and "large piano icon" | As 41 | Drawing seen (their unit); grammar UNKNOWN |
| 43 (2B) | eScreenPedalCalibration | Device procedure | **Never send** | (none) | (none) | READ FROM CODE |
| 44 (2C) | eScreenBootloader | Device procedure | **Never send** | (none) | (none) | READ FROM CODE |
| 45 (2D) | eScreen3L | By its name, **three lines, full screen** | **UNKNOWN**. Following 25, tags `00`-`08` is a **GUESS** | Nobody. The SB sweep reports nothing for 0x2D | Would stay up (**GUESSED**) | UNKNOWN |
| 46 (2E) | eScreen2LSmall | By its name, **two small lines** | **UNKNOWN**. Following 12, tags `00`-`05` is a **GUESS** | Nobody. In the Arturia family, 0x2E with empty fields "clears the screen" (SB-doc:629) | (none) | UNKNOWN |
| 47 (2F) | (not in FL's list; FL's `eLastEntry = 47`) | "Keyboard with colour marking, looks like a key range", in both families | **UNKNOWN** | Nobody. SB-doc:644, 672 | Newer firmware than FL's 2024 list (**GUESSED**) | Drawing seen (their unit) |
| 49-52 (31-34) | (not in FL's list) | **Two-column list with a divider**, 5 lines, used by Arturia's MainStage script | `31` init or refresh: `00` preset, `02` left size, `06` right size, `0A`/`0B` column labels. `32` append: `00` left text, `04` right text; with tags `03`/`07` it moves the cursor instead. `33` prepend. `34` heading | Arturia MainStage `config.lua` (per SB-doc:462-489, partly measured) | 5 lines. **A lit top button row costs 2 lines** (5 becomes 3), unlike lists 20 and 40. Ids 32-34 work only after 31. Lists 21 and 31 replace each other. Firmware: "Not 2 list setup before title change" | READ FROM CODE (their unit); firmware 1.5 or later (MainStage support arrived in 1.5) is **GUESSED** |
| 48 and above 0x3F | (none) | **UNKNOWN**. The sweeps stopped at 0x3F, and 0x30 showed nothing | | | | UNKNOWN |

What FL's script actually draws: **10, 11, 12, 13, 23, 24, 27, 28, 29, 31** and the labels 1-8, taken from every
SetCenterPage caller. It defines **0, 14, 15, 16, 25, 26 and 30** and never calls them. Its "page 9" call
(`KL3Navigation.py:304-309`) has no branch in `KL3Pages.SetCenterPage`, so it sends nothing. That code is dead and
never called. **READ FROM CODE.**

**Correction to our own records:** the surface map's row Y8 says every one of 17-22, 32-37, 39-42, 45 and 46 has an
unknown grammar. That is now out of date. **20, 21, 22 and 40 are fully worked out** (on another unit). **34, 35, 37,
39, 41 and 42 have been seen drawn.** Only **17, 18, 19, 32, 33, 36, 45 and 46** remain fully unknown. The firmware
also has ids FL's list lacks: 47 and 49-52.

---

## 3. The Arturia-mode canvas (`00 01 04`)

All facts in this section are **READ FROM CODE** (SB-doc:562-651, measured on their unit unless marked unverified),
except where Analog Lab's own files are cited.

- It works with no Analog Lab running, but only while the keyboard is in Arturia mode (Prog + the Arturia screen
  button). The keyboard then sends Arturia-mode CCs: screen buttons 60-63 below the screen and 56-59 above it, the
  dial 114/115, Back 65 (AL `controllers.prefmidi.xml:818-870`).
- **Labels**: `00 01 04 <id> 00 <type> 00 | 01 01 00 | 02 <sel> 00 | [04 <rgb> 00] | 05 <text> 00 | 06 00`.
  Ids 1-4 are the tabs along the bottom, and id 8 is the label at the top right. Type 00 clears, 02 is a top label,
  04 and 06 are tabs.
- **Lists**: 0x28 (with the icon panel) or 0x14 (one column; unverified, from a log), plus 0x15 items, exactly as in
  section 2. In Analog Lab's INSTRUMENTS list log, item icons were 0x10 ARP 2600, 0x11 Acid, 0x15 Augmented STRINGS,
  0x16 Augmented VOICES, 0x18 B-3, 0x19 Buchla Easel and 0x1E Clavinet (unverified, SB-doc:587-590). These **match
  FL's icon numbers exactly** (16, 17, 21, 22, 24, 25, 30).
- The SB sweep of 0x00-0x3F in this family saw (SB-doc:623-645, measured):

| Byte | Effect seen |
|---|---|
| 05, 06, 07 | lit a button LED |
| 0B, 0D | text in the middle |
| 0C, 0E, 26, 2E | cleared the screen |
| 17, 18 | small heading plus a grey popup |
| 19 | two-line popup |
| 1A | popup with right-aligned text |
| 1B, 1E | popups |
| 1F | small type |
| 22 | a centre-split bar with arrows |
| 23 | an empty bar with arrows |
| 25 | welcome |
| 27 | a palette |
| 28 | page title |
| 29, 2A | piano icons |
| 2F | keyboard key-range drawing |
| 31-34 | the MainStage two-column list |

- Analog Lab's own KeyLab mk3 screen design is described in AL `browser/KeyLab mk3-generated.xml`:
  - popups for parameter value, split point ("Split Point :") and octave/transpose (lines 17-19);
  - a preset browser whose buttons are search, like (empty and filled heart), previous and next (arrow-top,
    arrow-bottom) and edit (lines 22-29);
  - filter tabs TYPES, INSTRU, GENRES, BANKS and LIKED with styles "folded", "active", "on" and "active-tab", plus
    "monostable" (momentary) buttons (lines 31-38);
  - a two-line confirm screen with a left icon (line 53).
- Its VST3 has classes `KL3Browser`, `KL3ListView`, `KL3PlaylistView`, `KL3Popup`, `KL3Screen2L`,
  `KL3ParamControlScreen`, `KL3EditPresetScreen`, `KL3SysexButton` and
  `KL3Format::ListScreen::{TitleMsg, AppendMsg, PrependMsg, ScrollMsg, FullRefresh}`. That matches list title 20 or
  40, append 21, prepend 22 and the cursor-only "scroll" item. **READ FROM CODE** (class names only).

What this means for us (**GUESSED**, worth a probe): Arturia mode is a second, separate page we could draw on (for
example a full-time list) while DAW mode carries FL. But the keyboard shows only one mode at a time, and switching
modes is a physical press.

---

## 4. Icons

### 4.1 Large ("centre") icons: 86, numbers 0-85

Names are from FL `images_sub_enums.py:4-90`, a file marked "AUTOGENERATED DO NOT TOUCH". **READ FROM CODE.**

- **0** Arturia logo.
- **Types, 1-15**: 1 Bass, 2 Brass/Winds, 3 Drums, 4 Electric Piano, 5 Keys, 6 Lead, 7 Organ, 8 Pad, 9 Piano,
  10 Sequence, 11 Sound Effects, 12 Strings, 13 Template, 14 Vocal, 15 Default (type).
- **Instruments, 16-59**:

| No. | Name | No. | Name | No. | Name | No. | Name |
|---|---|---|---|---|---|---|---|
| 16 | ARP 2600 | 27 | CP-70 | 38 | Mellotron | 49 | SEM |
| 17 | Acid | 28 | CS-80 | 39 | Mini | 50 | SFZ Engine |
| 18 | Analog Lab | 29 | CZ | 40 | MiniFreak | 51 | SQ80 |
| 19 | Augmented Brass | 30 | Clavinet | 41 | MiniBrute | 52 | Solina |
| 20 | Augmented Grand Piano | 31 | DX7 | 42 | Modular | 53 | Stage-73 |
| 21 | Augmented Strings | 32 | Emulator II | 43 | OP-Xa | 54 | Synclavier |
| 22 | Augmented Voices | 33 | Farfisa | 44 | Piano | 55 | Synthi |
| 23 | Augmented Woodwinds | 34 | Jun-6 | 45 | Pigments | 56 | Vox Continental |
| 24 | B-3 | 35 | Jup-8 | 46 | Prophet-5 | 57 | Vocoder |
| 25 | Buchla Easel | 36 | Korg MS-20 | 47 | Prophet-VS | 58 | Wurli |
| 26 | CMI | 37 | Matrix-12 | 48 | Prophet | 59 | Default (instrument) |

- **UI icons, 60-85**:

| No. | Name | No. | Name | No. | Name |
|---|---|---|---|---|---|
| 60 | Ableton | 69 | DAW | 78 | Progression |
| 61 | Arp Chance | 70 | Delete | 79 | Reset |
| 62 | Arpeggiator | 71 | FL Studio | 80 | Scale |
| 63 | Arturia logo | 72 | Firmware update | 81 | Transpose minus |
| 64 | Bitwig Studio | 73 | Logic Pro | 82 | Transpose neutral |
| 65 | Chord | 74 | Metronome | 83 | Transpose plus |
| 66 | Cog | 75 | MIDI | 84 | Trash |
| 67 | Controls | 76 | Pads | 85 | User |
| 68 | Cubase | 77 | Pencil | | |

### 4.2 Small icons (for labels): 22, numbers 0-21

| No. | FL name (`images_sub_enums.py:92-114`) | Bitwig name | Live name |
|---|---|---|---|
| 0 | Blue Hand | BLUE_HAND | |
| 1 | Browsing Arrow (default) | BROWSING_ARROW_DEFAULT | UP |
| 2 | Browsing Arrow Down | BROWSING_ARROW_DOWN | DOWN |
| 3 | Browsing Arrow Left | BROWSING_ARROW_LEFT | |
| 4 | Browsing Arrow Right | BROWSING_ARROW_RIGHT | |
| 5 | Armed Audio | BUTTON_ARMED_AUDIO_DEFAULT | AUDIO_ARM |
| 6 | Armed MIDI | BUTTON_ARMED_MIDI_DEFAULT | MIDI_ARM |
| 7 | Cubase Monitor | BUTTON_CUBASE_MONITOR_DEFAULT | |
| 8 | GUI (FL) | SETTINGS | |
| 9 | GUI | TOOL | |
| 10 | Mute | MUTE | |
| 11 | Open | ARROW_DOWN | |
| 12 | Open variant 2 | ARROW_RIGHT | PLAY |
| 13 | Solo | SOLO | SOLO |
| 14 | Stop variant 2 | STOP | STOP |
| 15 | Check (big) | CHECK_BIG | |
| 16 | Delete | DELETE | |
| 17 | Heart | HEART_DEFAULT | |
| 18 | Heart (liked) | HEART_LIKED | |
| 19 | Mixer | MIXER | |
| 20 | Search | SEARCH_DEFAULT | |
| 21 | Search (on) | SEARCH_ON | |

Sources for the other two columns: Bitwig `SmallIcon.java:3-25`; Live `display.py:25-34`. **READ FROM CODE.** Where
the names differ, the numbers agree. The pictures behind 11, 12 and 14 are best described as a down arrow, a
play / right arrow and a stop square (**GUESSED** from Bitwig and Live).

### 4.3 Things to know about icons

- **Bitwig's large-icon list is wrong from 41 on.** It leaves out MiniBrute, so it puts Modular at 41 and shifts
  everything after it. It also gives two names the same number (60, 74) (Bitwig `CenterIcons.java:44-83`). Use FL's
  numbers. Analog Lab's log agrees with FL wherever they overlap (section 3). **READ FROM CODE.**
- **Which fields take which icons.** Large icons go in screens 15, 16, 26, 27 and 31, and in list items under
  title 40 (and probably 17, 18, 19 and 36: **GUESSED**). Small icons go in label tag `03`. **READ FROM CODE.**
- **A bad icon number.** The firmware logs "unknow icon" or "Couldn't load image with index" (FW 0xc0de4, 0xc1e64).
  What the screen shows then: **GUESSED** (no icon).
- **The pictures are fixed bitmaps.** They live in the firmware's `keylab3-assets` image, and the firmware checks
  "Widget's size and the icon's size are different". **No command uploads a picture.** **READ FROM CODE.**
- In list items under title 40, SB looked at icons 0-5 on screen: 0 the Arturia logo, 1 a string instrument (FL
  says Bass), 2 a trumpet, 3 a drum, 4 keys, 5 a keyboard (SB-doc:398-402, measured on their unit). Icon 1 is the
  one mild mismatch with FL's names.

---

## 5. Text, colour, brightness, pixels, speed

### 5.1 Text

- **Character set.** Plain ASCII 32-126 is all any source sends. Each source handles other characters its own way:
  - FL replaces the **whole line** with ".Undefined text." if any character is 128 or above (`KL3Display.py:26-47`;
    a rule in the script, not the device).
  - Bitwig folds some accented letters (`SysExUtil.java:7-37`) and sends `?` for the rest.
  - SB: anything else "costs you the character or the whole packet" (SB-doc:802-805; `keylab_screen.py:213-233`).
  - The firmware has "Couldn't parse string parameter, stopping parser" (FW 0xc227c).
  - **READ FROM CODE.** What the firmware draws for a byte above 0x7E: **UNKNOWN**.
- **Line length.** Each source caps text differently:
  - FL cuts any line over 32 characters to its first 28 plus "..." on its own side (`KL3Display.py:36-37`; 32 in
    every call).
  - Arturia's Live script uses 17 characters for line 1 and 30 for line 2 on screen 13, and 21 for popup line 2
    (`display.py:12-14`).
  - SB measured **34 visible characters per list line, cut, not wrapped** (SB-doc:613-614 and 807-810, measured on
    their unit). SB-live caps labels at 12 characters, its own choice.
  - **READ FROM CODE.** The real per-layout limits (how many characters screen 12 line 1 shows in big type versus
    line 2): **UNKNOWN on our unit**. SB's "34 whatever the characters are" hints at a fixed-width font in lists
    (**GUESSED**).
- **Upper case. CONFLICT with our own docs.**
  - FL upper-cases lines 2 and 3 **itself** (`_get_line_src(..., line_is_upper_case=True)` for every line 2 and
    line 3 in `KL3Display.py`).
  - Arturia's Live script and Bitwig send lower-case text on those lines ("Connected", "No Device", "Main encoder to
    offset"). Whether the **firmware** upper-cases anything is **UNKNOWN**.
  - Our README (line 51) and `chordsense-round2-and-vj-wiring-2026-10-23.md:254` say line 1 is "the only line the
    firmware leaves in its own case". That puts FL's rule on the firmware.
  - `screen.py` copies FL's rule on purpose, to stay byte-identical, which is fine. But if the firmware keeps case,
    our live readout could use line 2 for mixed-case text ("Am vi in Db"). One frame settles it (probe L1 below).

### 5.2 Colour

- **Per-line colour.** Every colour layout takes RGB at 0-127 per channel, one colour per line (screens 10-13, 14,
  24, 25, 27, 31) and one per readout bar (28, 29, 30). A colour must be exactly 3 bytes (FW "Color param is too
  short"). **READ FROM CODE.**
- Screen 12 with changing colours renders cleanly. **CONFIRMED** (2026-10-22).
- **The colour-type byte.** FL sends 1, and 0 with black for "No Selection". Bitwig sends 1, and 0 in one helper,
  with the comment "effects not clear" (`MidiProcessor.java:166, 177`). Arturia's Live script never sends it.
  - Our README says "Colour type 1 = use the RGB that follows". That is an **inference**.
  - **GUESSED**: 0 means the theme or default colour, 1 means custom RGB. Live's colours appear to work without the
    byte, which hints that RGB applies even when the type is absent (**GUESSED**).
- **Lists have no RGB.** An item's text is white (first byte of tag `02` = 0) or blue (anything else). Values 1-127
  all gave the same blue. Sweeping tag `02` did not change the cursor box colour (SB-doc:395 and 404-409, measured on
  their unit).
- **Label colour** sets the label's colour **and** the button's LED (section 6).
- **No colour fields** on screens 15, 16, 23 and 26 in FL's grammar.

### 5.3 Brightness and screen-wide properties

- **Device settings.**
  - **Display Brightness** runs 0-100 (MCC `KeyLab3 88.json` field 899, `paramId 64`, `globalParamId 1`).
  - **Sleep Mode** is 5, 15 or 30 min, each also as a "Vegas" variant (field 900). **Welcome Page** is on or off
    (field 901). **Low Power Mode** is on or off (field 902).
  - The firmware has the matching menu items ("DISPLAY BRIGHTNESS", "WELCOME PAGE", "SLEEP MODE", "LOW POWER MODE",
    FW 0xbfc60-0xbfc8c). **READ FROM CODE.**
  - The manual says the screen "will always be darkened after 5 minutes of inactivity, whatever time you've
    selected", to protect against burn-in (search summary of the KeyLab mk3 manual, p.60; not read in full).
  - Whether host frames count as activity, so that a VJ readout keeps the screen lit: **UNKNOWN**. This matters for
    long sets.
- **Brightness from the host.** No screen frame sets brightness. MCC writes settings through Arturia's
  configuration family. SB mapped a one-byte write as `21 03 40 <lo> <hi> <value>` and warns that **a write there
  throws the unit into User mode** (SB-doc:743-770, measured on their unit). The brightness address is unknown.
  - **GUESSED**: reachable, but risky, and not a live dimmer. **Do not use it.**
- **Screen 0 (properties)** takes one colour (FL `KL3Display.py:91-99`). Nobody calls it. Its meaning is **UNKNOWN**
  (section 2).

### 5.4 Raw pixels and custom images

- **None exist.** No integration sends a bitmap: FL, Bitwig, Live, Analog Lab's definitions, MainStage (per
  SB-doc), and both SB sweeps of 0x00-0x3F.
- The firmware shows a fixed set of page kinds and loads pictures by number from a baked-in assets image.
- **The only way to change the pictures is a firmware asset image. That is out of bounds.**
- The graphics we do have: coloured text lines, 0-127 bars (28, 29, 30), a centre-split bar (34) and a gauge (35),
  keyboard drawings (41, 42, 47), a list cursor and scrollbar, 108 icons, coloured button labels (with their LEDs),
  and popups over pages.
- **READ FROM CODE** (absence across every source). Strictly, "no pixel command" is proven only up to 0x3F and for
  the strings in firmware 1.5.0.

### 5.5 Refresh rate and pacing

- **On our unit.** A 60 ms colour cycle on screen 12 shows no flicker. Popups (23) go away after about 1 s. About 36
  LED packets in one burst froze the device until a power cycle. **CONFIRMED** (README, 2026-10-22). Every SysEx we
  send passes `governor.BurstGovernor` (at most 12 per 100 ms). `screen.py`'s writer adds "change-only, newest wins,
  at most one frame per 0.1 s".
- **From others.**
  - Two `00 02 04` frames sent back to back "can race on the device and one is dropped". A 60 ms queue fixed it.
    LED frames did not need the queue (SB-doc:793-797).
  - Send each SysEx as **one complete message**. Streaming the bytes one by one lost 2-4% of frames (SB-doc:786-791,
    measured on their unit).
  - Bitwig's driver runs a 50 ms tick (`MidiProcessor.java:64-80`). Live sends only changed frames
    (`elements.py:52, 58`, `optimized=True`).
  - Arturia's Live script sends about 44 readouts a second (SB-doc:333-334).
  - **READ FROM CODE.**
- **Faster than 60 ms on our unit**: **UNKNOWN**. Probe `lcdspeed` is already written for 80 / 60 / 40 / 20 ms.
- **The list hazard** (SB-doc:322-355, measured on their unit): with a title-40 list whose items lack icons, each
  changing fader readout pauses the keyboard's **own MIDI output** for about 60 ms in every 100. Notes and fader CCs
  arrive late and in bunches. **Use title 20, or give every item an icon.**
- **Popup timeout**: no field in any source. **GUESSED**: a fixed firmware timer. FL keeps a popup up by
  re-sending it on every idle tick (`KL3Return.py:285-293`). That is the only known way to hold one.

---

## 6. Screen-button labels and their lights

- **Which id is which physical button.**
  - Label ids **1-4 sit below the screen** and ids **5-8 above it**.
  - In DAW mode, label id n sends CC 48+n for n = 1-4 (CC 49-52) and CC 40+n for n = 5-8 (CC 45-48).
  - In Arturia mode the buttons below send CC 60-63 and those above send CC 56-59.
  - **READ FROM CODE**: AL `controllers.prefmidi.xml:851-861` (comments "Below screen", "Above screen"); Live
    mappings (`mappings.py:14-19` with `elements.py:25-41`: CC 45 device tab, 46 mixer tab, 47/48 previous/next
    scene, 49-52 mute/solo/arm/launch); SB-doc:84-100 (measured on their unit).
  - **Two numbering schemes exist.** Arturia calls the row above the screen "1-4" (F_Button1-4 = ids 5-8; FL's
    `eButton5 = 1`). SB calls the row below "1-4" (SB-doc:113-115). Our `screen.py` uses Arturia's
    (`SLOT_FOR_BUTTON`). Always name the row (above or below), not the number.
- **Label fields** (`00 02 04 <id> ...`):

| Tag | Meaning |
|---|---|
| `00` | type (style), 0-15 |
| `01` | line number |
| `02` | colour type |
| `03` | small icon |
| `04` | RGB |
| `05` | text line 1 |
| `06` | text line 2 |
| `07` | text line 3 |

  **READ FROM CODE**: FL `KL3Buttons.py:62-90` (tags 00-06); SB-doc:233-244, from MainStage `config.lua`, which
  adds `07`.
- **Types.** Bitwig names all twelve: 0 off, 1 simple, 2 toggle off, 3 toggle on, 4 tab folded, 5 tab folded
  disabled, 6 tab unfolded, 7 tab unfolded disabled, 8 icon tab folded, 9 icon tab unfolded, 10 simple icon, 11 toggle
  icon (`ButtonDisplayType.java:3-15`).
  - Arturia's Live script uses them as off / on pairs: toggle (2, 3), tab (4, 6), icon (10, 11) (`display.py:15`).
  - FL uses 0, 4, 6, 10 and 11 (`KL3Return.py:314-435`).
  - Analog Lab's style words "folded", "active", "on" and "active-tab" map onto these (**GUESSED**).
  - **READ FROM CODE.**
- **What Arturia's own Live script sends** for a label: tags `00 <type>`, `03 <icon>`, `04 <rgb>`, `05 <text>` only
  (`midi.py:23-25`). SB recorded the same on the wire, for example `00 02 00 | 03 00 00 | 04 7F 7F 7F 00 | 05 "2" 00`
  off and `00 03 00 | ...` on, and switching to that exact structure removed a 1-in-30 failure (SB-doc:246-261,
  measured on their unit). The values that work can **differ per button id** (SB-doc:263-266).
- **Measured rules** (SB-doc:268-291, their unit):
  - A colour without a type is ignored. An id with no fields does nothing.
  - `00 02 00 | 04 <rgb> 00 | 05 00` (an empty text field) **lights the button's LED and writes no text**. Without
    the empty `05`, a box is drawn.
  - `00 00 00 | 04 00 00 00 00 | 05 00` **clears the slot**. Sending it for ids 1-8 clears all labels.
  - Type 0 holds the slot without colour. Line number 0-7 does not change the row height.
  - Space: in the two-column list (49-52) a lit top row costs 2 lines. In lists 20 and 40 labels cost nothing.
- **LEDs. CONFLICT.**
  - SB measured that the screen buttons have **no address** in the LED family `00 02 03`: a sweep of ids 0-127
    lit only the transport row and pads. Their light comes **only from the label's colour field** (SB-doc:102-111).
  - Arturia's FL script and the Bitwig extension **do** address LEDs 21-28 as the eight screen buttons:
    - FL sets them dim grey at start (`KL3Return.py:104-111`), flashes them white on press (`KL3Process.py:820-830`)
      and names them `eContextual1-8` (`LedId.py:46-53`);
    - Bitwig uses `CONTEXT_BUTTON_LIGHT = 0x15` (`KeylabHardwareElements.java:26`).
  - One difference may explain it: Bitwig and Arturia's Live script start the LED frame with **`04 02 03`**, not
    `00 02 03` (Bitwig `RgbButton.java:26-36`; Live `midi.py:9`), and Bitwig adds a blink-state byte in the last
    data position: 0-2 blink, 3 pulse, 32 none (`color/BlinkState.java`). Whether that byte or the label's colour
    wins: **UNKNOWN**. Our unit has never lit a screen-button LED (surface map L7).
- **Firmware checks**: "unknow button", "unknow button param", "unknow button to clear" (FW 0xc1758-0xc177c).

---

## 7. Other messages that touch the screen

- **The "link" property on touch.**
  - FL sends `00 02 00 <control 0-8> 02 01 00` when a knob or fader is touched and `... 02 00 00` on release
    (`KL3Plugin.py:1083, 1129`).
  - Bitwig sends `00 02 00 <id> 00 01 00 01 00 00 02 <0|1> 00`, where the last value says whether a parameter is
    bound to that control (`MidiProcessor.java:254-259`).
  - SB notes the keyboard "draws its own readout from the hardware at the same moment" as a touch, and a host
    readout replaces it (SB-live `keylab_screen.py:295-298`).
  - **GUESSED**: tag `02` tells the device whether the host owns that control's readout, which turns the device's
    own popup off. Firmware: "unknown encoder property", "further properties will not be processed" (FW
    0xc25fc-0xc2618). That is relevant if we ever want the device's own value popups gone or kept.
- **Connect.** `00 02 05 01` / `00 02 05 00` (DAW) and `00 01 05 01` / `00 01 05 00` (Arturia). This is a handshake,
  not a mode switch (SB-doc:51-63). DAW connect is **CONFIRMED** on our unit (surface map V3). Bitwig sends a
  standard identity request first, `F0 7E 7F 06 01 F7`, connects on the reply and draws its "Connected" card 1 s
  later (`MidiProcessor.java:27, 55-58, 129-143`).
- **Soft connect** (`eSoftConnection = 8`): Analog Lab's hand-off into Arturia mode (AL
  `controllers.prefmidi.xml:215`; CC 117 in Arturia mode is "HardwareReceiveSoftConnect"). **Avoid** (surface map
  V9).

---

## 8. What this gives "our own context-aware engine" (screen part only)

This is not a design, just the palette FL's script leaves unused, so the D8 conversation starts from the full set.
It is **GUESSED** usefulness on top of the facts above.

- **A home page that never flickers** (12 or 13, or 14 for a big chord name), with mixed case on line 2 if probe L1
  says the firmware keeps case.
- **A scene, preset or chord-history browser as a native 7-line list** (20 or 40 plus 21 and 22), driven by the
  dial with each item's icon shown. This replaces any idea of drawing our own list.
- **Raised messages** on 30 (draws without touch) and **context cards** on 27 or 31 (icon + two lines).
  **Touch readouts** on 28 and 29, drawn only under a finger, which fits D2's "touch to peek".
- **Eight labelled, coloured tabs** whose colours also light the buttons. Toggle and tab styles show state without
  extra frames.
- **Bars for continuous values** (28-30). A centre-split bar (34) for bipolar values such as pan, hue shift or a
  pitch bend. A gauge (35).
- **Keyboard drawings** (41, 42, 47) for split points or key ranges, once their fields are known.

---

## 9. Probes this report suggests (nothing sent today)

These are listed for a later session, after Daniel says go, through `ScreenWriter` (it already refuses 38, 43 and
44), one frame at a time, at least 60 ms apart, with FL closed or in guest mode, and a photo or Daniel's words as the
receipt.

| # | Question | One frame (DAW family) |
|---|---|---|
| L1 | Does the firmware upper-case line 2? | Screen 12, line 1 "Am vi Db", line 2 "Am vi Db" |
| L2 | Does the native list render on our unit? | Title 20 "TEST" with count 10, then ten items through 21, then a cursor at 5 |
| L3 | Icon panel list | Title 40 with icon items (types 1-9), then move the cursor |
| L4 | Software popup | Screen 30 with no touch |
| L5 | Touch-gated readout | Screen 29, once with no touch and once while Daniel touches fader 1. This also fixes probe `screens`, which today draws 28 and 29 with nothing touched and would wrongly read "not seen" |
| L6 | Screen-button LED, label path | Label id 8: `00 02 00 \| 04 <red> 00 \| 05 00` |
| L7 | Screen-button LED, LED path | LED id 28 with `00 02 03` and then with `04 02 03` (settles the conflict in section 6) |
| L8 | The seen-but-unmapped screens | 34 and 35 with knob-style fields; 39, 41 and 42 empty. Leave 37 for last (possibly interactive) |
| L9 | The fully unknown screens | 14, 16, 17, 18, 19, 36, 45 and 46, each with the grammar of its nearest neighbour |
| L10 | Rate | The existing `lcdspeed` probe (80 / 60 / 40 / 20 ms) |
| L11 | Activity | Does a host frame every 30 s stop the 5-minute darkening? |

Before any of L8 or L9, reading Arturia's **Cubase script** (one download, 3.77 MB, Daniel's yes) may supply the
real field layouts and turn guesses into code facts without sending anything.

---

## 10. Corrections and conflicts, in one place

1. **Upper case** is FL's rule, not a proven firmware rule. Our README line 51 and the chordsense round-2 note
   (line 254) put it on the firmware. **UNKNOWN** until probe L1.
2. **Surface map row Y8 is out of date.** Lists 20, 21, 22 and 40 are worked out (on another unit), and 34, 35, 37,
   39, 41 and 42 have been seen drawn. FL's `ScreenId.py` (2024) is **not** the firmware's full list: 47 and 49-52
   exist on recent firmware.
3. **Probe `screens` (fader and knob readouts) may give a false "not seen"**: 29 draws only under a finger
   (measured on another unit).
4. **Screen-button LEDs**: FL and Bitwig use LED ids 21-28. SB found no response there. Unresolved (probe L7).
5. **Bitwig's large-icon numbers are wrong from 41 on**, and its "POP_UP_FADER = 0x1E" name is wrong (its code uses
   0x1D for faders). Use FL's numbers.
6. **The LED request byte**: Arturia's own Live script, not only Bitwig, sends `04 02 03` (Live `midi.py:9`). Surface
   map row L2 calls 0x04 "Bitwig's" and untested.
7. **Today's observations** (our frames show while we hold the DAW connection; FL repaints with the pattern name)
   came in the brief. **No repo receipt holds them yet.** `screen-20261023-012612.json` records a frame sent but no
   answer from Daniel's eyes.
8. **Firmware version on the unit: UNKNOWN.** 1.2.1 and 1.5.0 images are in Downloads, and 1.5.1 came out
   2026-10-16. Ids 47 and 49-52 probably need 1.5 or later.
