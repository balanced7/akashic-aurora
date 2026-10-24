# A context-aware FL engine: the context lane's report (verbatim)

Workflow run wf_05ceb8e4-91d (task w34xc5hn9), 2026-10-24. Research only: nothing was sent to the KeyLab.
Daniel (verbatim, 2026-10-24): "can't we make our own context aware engine that borrows from the default script? perhaps we can make it better. what can we write to the LCD? what are the full functionalities afforded us there?"
Local scratch paths shortened; third-party code was read for facts only.

---

# A context-aware engine for the KeyLab 88 mk3 in FL Studio: what Arturia's script does, and what we can build

Report file: `<session scratchpad>/lcdctx/context-report.md`

Lane: A CONTEXT-AWARE ENGINE · researched 2026-10-24 · read-only everywhere.
- Nothing was sent to the KeyLab.
- Nothing in FL was touched.
- No file outside the scratch folder was written.

Daniel's words (today, verbatim): "can't we make our own context aware engine that borrows from the default script?
perhaps we can make it better. what can we write to the LCD? what are the full functionalities afforded us there?"

## How to read the tags

Every fact carries one tag:

- **[CONFIRMED]**: confirmed on our hardware, and a record in the repo says so (the record is cited).
- **[CODE: whose file:line]**: read from code.
  - "Arturia": the vendor script in `C:/Users/L5/Documents/Image-Line/FL Studio/Settings/Hardware/Arturia KeyLab mk3/`.
  - "NI": Native Instruments' FL script on this machine (`.../Settings/Hardware/NI Komplete Kontrol/`, MIT licence,
    (c) 2021 Pablo Peral and 2026 Native Instruments).
  - "IL-MCU": Image-Line's own Mackie Control script (`.../Settings/Hardware/MackieCU/`).
  - "midi.py": FL's helper module `C:/Program Files/Image-Line/FL Studio 2026/Shared/Python/Lib/midi.py`.
- **[DOCS: source]**: from Image-Line's manual, the API stubs, a changelog, or a project's own documentation. It is
  written down somewhere, but not tested on our machine. "WhatsNew" means FL's local changelog
  `C:/Program Files/Image-Line/FL Studio 2026/WhatsNew.rtf`, cited by version and bug number.
- **[REPORTED: who]**: a community report (a GitHub issue, a blog, a forum post). I did not check it.
- **[SEEN TODAY]**: my own read-only check on this machine today. There is no repo receipt for it yet.
- **[GUESSED]**: my inference.

Nothing from Arturia, NI, Image-Line or any GitHub project was copied into the repo or into this report. Code was read
only for facts: numbers, ids, call names, message shapes and behaviours.

---

## 0. The short answer

**1. Yes. We can build our own context engine, and it can be clearly better than Arturia's.**

Arturia's script decides "where you are" with one question: which of four windows has focus (mixer, channel rack,
browser or plugin), via `ui.getFocused`. It asks this whenever a control moves and on every FL refresh.
[CODE: Arturia KL3Process.py:446-545, 549-608; KL3Return.py:304-478]

It controls plugins only through a fixed table of 16 parameters for **33 FL-native plugin names**. It always targets the
**selected channel's** instrument. [CODE: Arturia KL3Plugin.py:181-1010] So every third-party VST (Kontakt, Serum and the
rest) and every **mixer effect** gets nothing from the knobs.

FL's API gives us everything needed to do better (Part 2):
- which window and which plugin has focus, including effects;
- every parameter's name, value and display text, for any plugin;
- preset names;
- the names of controls Daniel has linked himself in FL;
- FL's own hint text, which FL pushes to controllers;
- meters, transport, song position, tempo, patterns and colours.

**2. The LCD runs fixed layouts. It cannot show a picture.**

We pick one of the firmware's layouts and fill it with:
- ASCII text, up to 31 characters a line;
- RGB colours (0-127 per channel);
- a 0-127 bar;
- an icon number (86 large, 22 small);
- eight screen-button labels.

Two-line screen 12 is [CONFIRMED] to stay up with no flicker, and so is a 60 ms colour cycle (surface map Y1 and Y3).
About half the layout ids have never been drawn by anyone, so what goes in them is UNKNOWN. That includes lists, a browser,
a colour picker and a curve editor (section 3.4). The real limits are what we choose to show and how fast we can refresh.
Pixels are not the limit.

**3. Arturia's script is what fights us on the LCD, and only replacing it ends that.**

The DAW port is shared, so our frames land while FL runs. [CONFIRMED: surface map V2, probe P1, 2026-10-22]

But Arturia's script re-sends its own screen and all eight labels on almost every FL refresh. That is about 40 SysEx
messages each time. It decides when to repaint by testing the refresh flags for an exact match instead of checking the
individual flags, so it fires on nearly every refresh. [CODE: Arturia device_KL3.py:137-152; KL3Return.py:304-478]

**4. A correction to how the repo describes the freeze risk (W266, P23).**

Bug 22368, "Freezes when MIDI scripts call functions in FL Studio", is in the **fixes** list of 26.1.3 (2026/07/24).
That is the build Daniel runs (FL64.exe 26.1.3.5570). [DOCS: WhatsNew 26.1.3 #22368] [SEEN TODAY: file version]

The live risk on his build is three later fixes, all in **2026.1.7 (1 Oct 2026)** [DOCS: IL forum t=342646]:
- #22604 "freeze when a script sends a sysex message";
- #22725 "freeze when calling the GlobalTransport function";
- #22689 "crash when calling the GlobalTransport function".

A KeyLab script sends SysEx all the time, and Arturia's own script calls GlobalTransport on ordinary button presses.
Whether to update FL to 26.1.7 or later before we ship our script is Daniel's call, and I recommend it.

**5. As far as anyone can show, talking to a program outside FL works only over MIDI.**

Sockets and threads are reported blocked inside FL's script interpreter (2025-2026). File access is disputed. ctypes is
reported blocked. [REPORTED: section 2.5]

Today this machine has **no loopback MIDI port**. The only Windows MIDI ports are the KeyLab's two and the GS Wavetable
Synth. [SEEN TODAY] So there are two choices:
- Put the engine **entirely inside FL** (our own device script). This needs no link at all.
- Add a loopback port so the script can report FL's context to the hub. Creating that port needs Daniel's OK.

---

## Part 1. What Arturia's FL script does, by context

### 1.1 How the package is laid out

- **Two scripts.** `device_KL3.py` (`#name=KeyLab mk3`) runs on the DAW port. `device_KeyLab mk3 MIDI.py`
  (`#name=KeyLab mk3 Arturia dev`) runs on the MIDI port. [CODE: Arturia device_KL3.py:1; device_KeyLab mk3 MIDI.py:1]
- **Ports.** FL 26 binds them as "KeyLab 88 mk3 DAW" on port 236 and "KeyLab 88 mk3 MIDI" on port 0.
  [DOCS: repo research/in-flight/fl-jam-bridge-2026-09-14/fl-scripting.md:29, a registry read on 2026-09-14]
- **Hardware ids.** The DAW script declares the three mk3 hardware ids `00 20 6B 02 00 0A 02/04/08 7F 7F 7F 7F`.
  [CODE: Arturia device_KL3.py:2]
- **One write path.** Every write to the device goes through one function: `F0 00 20 6B 7F 42` + data + `F7`, sent with
  `device.midiOutSysex`. [CODE: Arturia KL3Dispatch.py:64-66]
- **Credits and licences.** Version "1.1", developer Farès Mezdour. The dispatcher, display and pages files carry an MIT
  header "(c) 2020 Ray Juang". The generated enums say "(c) 2024 Arturia. All rights reserved".
  [CODE: Arturia device_KL3.py:7-9; KL3Dispatch.py:3-4; KL3Display.py:12-13; KL3Pages.py:6-7; ScreenId.py:16]
- **The user guide** is 6 pages, dated 2024-08-27. It documents only the controls listed in 1.3.
  [CODE: Arturia DAW User Guide PDF pp.2-6]

### 1.2 How it decides the context: which FL calls, and when

There is **no context model and no cache.** The script asks FL afresh each time:

| When | What it asks FL | Tag |
|---|---|---|
| Every control event (knob, fader, dial, screen button) | `ui.getFocused(w)` for w in {0 mixer, 1 channel rack, 4 browser, 5 plugin}, sometimes three or four calls in a row | [CODE: Arturia KL3Process.py:34-41, 446-545, 571-592, 706-739] |
| Every knob or fader event outside the mixer | `channels.selectedChannel(1)`, `plugins.isValid`, `plugins.getPluginName(selectedChannel)`, then get, set, name and value-string calls on the parameter: about 10 FL calls and 1 SysEx per knob step | [CODE: Arturia KL3Plugin.py:186-188, 1066-1090; KL3Process.py:767-814] |
| `OnRefresh(flags)`, whenever `flags not in [4, 4096]` | 1. LED states: recording, song tick position, loop-record, metronome, undo history, plugin focus. 2. The 12-pad step view of the selected channel (`getGridBit` and `getCurrentStepParam` × 8). 3. FPC pad colours (`plugins.getPadInfo` × 12). 4. Either the channel-rack screen or the mixer screen, with 8 labels | [CODE: Arturia device_KL3.py:137-152; KL3Return.py:154-231, 304-478] |
| `OnIdle()` (FL documents "roughly once every 20ms") | `mixer.getSongStepPos()`, `playlist.getVisTimeBar()` and `playlist.getVisTimeStep()` on every tick, even when stopped. When the step changes, it repaints the 12 step pads (13 SysEx). While Rewind or Fast-forward is held, it repaints screen 24 on **every tick** | [CODE: Arturia device_KL3.py:65-68, 157-159; KL3Return.py:258-293] [DOCS: stubs, callbacks page] |
| `OnUpdateBeatIndicator(v)` | Blinks the Play LED, and the Record LED while recording | [CODE: Arturia device_KL3.py:129-132; KL3Return.py:235-251] |

**The flag test is wrong.**

`OnRefresh` hands the script a set of on/off flags packed into one number [CODE: midi.py:77-94]:

| Value | Meaning |
|---|---|
| 1 | mixer selection |
| 2 | mixer display |
| 4 | mixer controls |
| 16 | remote links |
| 32 | focused window |
| 64 | performance |
| 256 | LEDs |
| 512 | remote link values |
| 1024 | patterns |
| 2048 | tracks |
| 4096 | control values |
| 8192 | colours |
| 16384 | names |
| 32768 | channel rack group |
| 65536 | channel event |
| 131072 | undo |
| 262144 | channel rack |
| 524288 | graph editor |

Arturia compares the whole number with exactly 4 or exactly 4096 [CODE: Arturia device_KL3.py:141]. So any combination
of flags triggers a full repaint, even 4 and 4096 together. NI's script says FL combines flags (its example is
65536|4096|256|32 = 69920), "so a bitwise check is required — strict == would never match".
[CODE: NI controller_definition.py:650-653]

**Cost of one refresh, counted from the code:**
- Fixed LED messages: Record 1, Play 1, Loop 1, Metronome 1, step pads 12, Undo/Redo 2, Back 1, FPC/bank-A pads 12.
- Plus 9 for the centre screen and its 8 labels, when the channel rack, a plugin or the mixer has focus.
- Total: **40 SysEx when the channel rack, a plugin or the mixer has focus; 31 otherwise.**
- No message is skipped when it is unchanged. The code that would skip duplicates ("screen filtering priority") is
  commented out. [CODE: Arturia KL3Return.py:154-231, 304-365 (the skip code at 353-356), 368-478 (at 451-457)]

Our own record: a burst of about 36 messages froze the device, and 12 per 100 ms is safe [CONFIRMED: surface map L3,
2026-10-22]. FL's script sends 40 per refresh, and no freeze has been reported. Most likely FL spaces its messages out, or
message size matters, but that is [GUESSED]. One probe would settle it (section 5).

### 1.3 What every control does, by FL context

"Native map" here means the plugin table in 1.4, applied to `channels.selectedChannel()` with no mixer slot.

**Knobs and faders**

| Control (DAW-port CC) | Channel rack focused | Plugin window focused (generator or effect) | Mixer focused | Browser focused | Playlist, piano roll, anything else |
|---|---|---|---|---|---|
| Knobs 1-8 (91, 92, 94, 95, 96, 97, 102, 103; relative, 1 % per tick) | native map, popup 28 | native map on the **selected channel**, even when an effect window has focus | pan of strips 1-8 (+8 × bank), 5 % per tick, popup 28 "Pan - n" | native map | native map |
| Knob touch (8-15) | peek the native parameter (28) and re-read its value as the starting point | same | peek the strip's pan (28) | same as channel rack | same |
| Faders 1-8 (105-112; absolute) | native map. The value jumps, and takeover follows FL's global "pickup" setting (`pickupMode=2`) | same | volume of strips 1-8 (+bank), **jumps** (`pickupMode=0`), popup 29 "Volume - n" | native map | native map |
| Fader touch (28-31, 33-36) | peek the native parameter (29) | same | peek volume (29) | same | same |
| Knob 9 (104) / fader 9 (113) | pan / volume of the **selected mixer track** (not the master) | same | same | same | same |

**Dial and Back**

| Control (DAW-port CC) | Channel rack focused | Plugin window focused | Mixer focused | Browser focused | Playlist, piano roll, anything else |
|---|---|---|---|---|---|
| Dial turn (116; speed ignored) | previous or next channel; the mixer selection follows the channel's mixer track | **closes every channel's plugin window** (loops over all channels) | previous or next track. While screen button 2 is held, the 8-strip bank moves (offset 0-14, so strips up to 120) | browser up or down (or popup menu up or down), with a hint screen | moves focus to the channel rack |
| Dial click (117) | opens the selected channel's plugin (`showCSForm`) | Arturia plugin: forwards to FL port 10 ("Arturia mode"); any other plugin: nothing | arms the selected track | nothing | nothing |
| Back (40) | LED flash only | closes the plugin window | LED only | closes a popup, or browser "left" | LED only |

**Screen buttons**

| Control (DAW-port CC) | Channel rack focused | Plugin window focused | Mixer focused | Browser focused | Playlist, piano roll, anything else |
|---|---|---|---|---|---|
| Button 1 (45) | focus channel rack, on release | same | same | same | same |
| Button 2 (46) | focus mixer, on release (unless the bank was moved while it was held) | same | same | same | same |
| Button 3 (47) | previous pattern | previous preset (only names in the native list) | nothing | browser tab left | nothing |
| Button 4 (48) | next pattern | next preset | nothing | nothing | nothing |
| Buttons 5, 6, 8 (49, 50, 52) | mute, solo, arm the selected mixer track | same | same | same | same |
| Button 7 (51) | nothing | nothing | nothing | nothing | nothing |

Sources for these tables:
- [CODE: Arturia KL3Process.py:119-161 (maps), 280-338 (dispatch and press/release filters), 494-545 (dial), 446-455
  (dial click), 549-608 (screen buttons), 612-624 (Back), 696-756 (knobs and faders), 930-948 (bank)]
- [CODE: Arturia ArturiaCrossKeyboardKL3.py:9-54 (volume and pan; pan steps 1/20; `pickupMode` 0)]
- [CODE: Arturia KL3Plugin.py:1069-1076 (knob 1 % per tick; fader `pickupMode` 2 = `PIM_FollowGlobal` per midi.py)]
- [DOCS: stubs: `setTrackVolume` and `setTrackPan` default to `PIM_None`]

This corrects the earlier evidence file, which said "no pickup for faders" (evidence-control-map-2026-10-22.md §5). That
is true for mixer faders. Plugin faders follow FL's global pickup option.

**Transport and command buttons** behave the same in every context [CODE: Arturia KL3Process.py:291-303, 629-692,
854-880]:
- Play (21): `transport.start()`, on release.
- Stop (20).
- Record (22): on release.
- Tap (23): `FPT_TapTempo`.
- Metronome (27): on release.
- **Loop (24) toggles loop-recording (`FPT_LoopRecord`), not pattern/song loop mode.** Its LED follows
  `ui.isLoopRecEnabled`. [CODE: Arturia KL3Process.py:645-646; KL3Return.py:163-167]
- Rewind and Fast-forward (25/26): `continuousMove(±2)` while held.
- Save (41): shows "Saving project...".
- Quantize (42): runs `channels.quickQuantize(selected)` and shows "Track Quantized". On release it also **hides the
  piano roll** (KL3Process.py:863-870).
- Undo and Redo (43/44): `general.undoUp` and `general.undoDown`.

**Pads (DAW bank, channel 10)** [CODE: Arturia KL3Process.py:350-422, 975-1058; KL3SeqParam.py:7-34]:
- Notes 0-7 toggle step-sequencer steps of the selected channel, on release.
- Hold pads and turn knobs 1-7 to edit those steps' pitch, velocity, release, fine pitch, pan, mod X and mod Y. FL's graph
  editor opens while you do. Knob 8 (shift) is skipped.
- Notes 8-11 pick the step page (1-8, 9-16, 17-24, 25-32) and show screen 27.
- Notes 12 and up are remapped to the FPC or Drumaxx layout when that plugin is on the selected channel.
- That pad hits arrive on the DAW port, channel 10, as notes 0-11 is [CONFIRMED] (surface map P1). The danger that pads
  write steps into the pattern is already recorded (P8).

**Wheels** [CODE: Arturia KL3Process.py:367-378]:
- With an Arturia V Collection plugin on the selected channel, pitch bend and CC1 are forwarded to port 10.
- With any other valid plugin, pitch bend also moves the channel's pitch knob (`setChannelPitch`).
- Which port the wheels actually arrive on in DAW mode is UNKNOWN. If they arrive on the MIDI port, this code never runs.
  [GUESSED]

### 1.4 The plugin maps (the "Device" context)

**33 FL-native plugins are mapped by exact name** [CODE: Arturia KL3Plugin.py:192-988]:

| Group | Plugins |
|---|---|
| Synths | FLEX, FL Keys, Sytrus, GMS, Harmless, Harmor, Morphine, 3x Osc, Fruity DX10, MiniSynth, PoiZone, Sakura, Ogun, SimSynth Live, Autogun, PLUCKED!, BeepMap, Toxic Biohazard, Sawer, Transistor Bass, BooBass, Kepler |
| Drums and samplers | FPC, BassDrum, Fruit kick, Drumaxx, Drumpad, Slicex, SoundFont Player, Fruity granulizer, Fruity Dance |
| Controllers | Fruity Envelope Controller, Fruity Keyboard Controller |

How the maps work:
- Each name gets **one fixed table of 16 parameter numbers**: 8 for knobs and 8 for faders. -1 means unmapped.
- Several tables are mostly empty: Autogun maps 1 control, Fruity Keyboard Controller 2, BooBass 3.
- There are **no pages**. A plugin with 800 parameters still gets the same 16.

**Every other plugin gets an all -1 table.** [CODE: Arturia KL3Plugin.py:990-1010, 1122-1137]
- For those, a knob or fader sends the device a "release" property message (`00 02 00 <slot> 02 00 00`) and draws
  nothing.
- The event is then handed back to FL (`event.handled = False`), so FL's own **Link to controller** mappings still work.
  [CODE: Arturia device_KL3.py:75-77] That is the only way to control VSTs today.

**The target is always the selected channel's instrument** (`channels.selectedChannel()`, `slotIndex` -1).
[CODE: Arturia KL3Plugin.py:186-188, 1070, 1076]
- With an effect window focused (say Fruity Reverb on a mixer insert), the knobs still move the selected channel's
  synth. The effect is never touched.
- The script checks only window id 5 (plugin). It never checks 6 (effect) or 7 (generator), which FL defines.
  [CODE: midi.py window constants `widPlugin` to `widPluginPicker`; Arturia KL3Process.py:39-41]

**A list bug.** `NATIVE_PLUGIN_LIST` is missing three commas, so 'BassDrum', 'Fruit kick', 'MiniSynth' and 'PoiZone'
fuse into one string. The list holds 30 entries, not 33. [CODE: Arturia KL3Plugin.py:124-158, the fused lines 135-138]
- Screen buttons 3 and 4 (previous and next preset) therefore do nothing for those four plugins.
- Fruit kick is still in the list of plugins whose presets can be changed (KL3Plugin.py:160-179). So its arrows are
  **drawn**, but pressing them does nothing.

**Touch.** On touch, the script reads the live value as its new starting point and sends a "connect" property message
(`... 02 01 00`) for that control. [CODE: Arturia KL3Plugin.py:1078-1083] What connect and release change on the device
is UNKNOWN (surface map V5).

### 1.5 Arturia's own plugins (the MIDI-port script)

- **Forwarding.** The MIDI-port script forwards **every CC** to FL MIDI port 10 with `device.forwardMIDICC(msg, 2)`, then
  leaves it unhandled. It packs the port into the message as `10 << 24`.
  [CODE: Arturia device_KeyLab mk3 MIDI.py:33-35]
- **What FL documents.** FL documents mode 2 as "send the message to all selected channels" [DOCS: stubs, device FL page].
  Packing the port number into the message bits is not documented by FL.
- **The DAW script's share.** The DAW script forwards to port 10 only for the 40 exact names in `V_COL`, and only for the
  dial click with a plugin focused and for the wheels.
  [CODE: Arturia ArturiaVCOL.py:5-46; KL3Process.py:367-378, 446-450, 845-851]
  A newer Arturia instrument that is not on that list falls through to the FL path. [GUESSED: the list is from 2024]
- **What the guide says.** Arturia plugins are controlled "as you would do in standalone". You enter that mode by clicking
  the dial on a track with an Arturia plugin, or with Prog + Arturia. [CODE: Arturia User Guide p.6]
- **Where that integration lives.** The script defines an `eArturia` connect message but never sends it (no callers).
  [CODE: Arturia KL3Connexion.py:17-23] So the plugin side of the integration lives in Arturia's plugins, not here.
  [GUESSED]

### 1.6 What it shows on the screen, and when it repaints

**The resting screen** (redrawn on refresh):

| Trigger | Screen id | Content | Tag |
|---|---|---|---|
| Script load (`OnInit`) | 31, full popup with the FL icon | Line 1: FL's window title. Line 2: "Connected" | [CODE: Arturia device_KL3.py:91-100] |
| `OnRefresh`, channel rack or plugin focused | 13, two lines inverted, + all 8 labels | See below | [CODE: Arturia KL3Return.py:368-478]; the pattern-name repaint was seen today per the brief, no repo receipt |
| Same, no channel selected | 10 | "No Selection" | [CODE: Arturia KL3Return.py:469-475] |
| `OnRefresh`, mixer focused | 11, one line inverted, + 8 labels | "n - track name" in the track colour at half brightness | [CODE: Arturia KL3Return.py:304-365] |
| `OnRefresh`, browser, playlist or piano roll focused | centre untouched | Nothing new; the last screen stays | [CODE: Arturia KL3Return.py:306, 370] |

Screen 13, in detail:
- Line 1: "*" if a plugin is focused, then the channel name, in the channel colour at half brightness.
- Line 2: "Pattern " plus the pattern name (or its number, if the name is the default).
- Labels: PLUGIN and MIXER; pattern arrows, or preset arrows for natives whose presets can be changed; mute, solo and arm
  pictograms showing the selected mixer track.

**Popups** (drawn when something happens):

| Trigger | Screen id | Content | Tag |
|---|---|---|---|
| Knob or fader on a mapped native parameter | 28 knob / 29 fader | Parameter name, FL's value text, 0-127 bar, "Analog Lab blue" | [CODE: Arturia KL3Process.py:767-814; KL3Navigation.py:120-142] |
| Mixer knob or fader, or touch | 28 / 29 | "Pan - n" / "Volume - n", %, bar | [CODE: Arturia KL3Navigation.py:39-80] |
| Dial in the browser | 12 (or 10 inside a popup menu) | Item caption + browser tab, or FL's hint text; all 8 labels re-sent | [CODE: Arturia KL3Navigation.py:271-301] |
| Mixer bank move | 27 | "Tracks a - b" + controls icon | [CODE: Arturia KL3Navigation.py:254-266] |
| Step page pad | 27 | "Step Position" / "Step a - b" + pads icon | [CODE: Arturia KL3Navigation.py:320-333] |
| Save / Quantize | 23 | "Saving project..." / "Track Quantized" | [CODE: Arturia KL3Navigation.py:155-170] |
| Rewind or Fast-forward held | 24, every idle tick | "Track Position" / "Bar b Step s" | [CODE: Arturia KL3Return.py:275-293] |

**Popups that were switched off.** Popups for Undo, Redo, Metronome and Tap tempo were written and then switched off,
with the comment "Screen priority...". [CODE: Arturia KL3Process.py:682, 689; KL3Navigation.py:173-225] The next refresh
repaint would erase them at once. [GUESSED]

**Text rules** [CODE: Arturia KL3Display.py:26-56]:
- ASCII only. Any other character turns the whole line into ".Undefined text.".
- A line over 32 characters becomes its first 28 plus "..." (31 in all).
- Lines 2 and 3 are upper-cased **by the script**. Whether the firmware would show lower case on line 2 is UNKNOWN, and
  cheap to test (section 5).

### 1.7 What it lights

| What | When | Tag |
|---|---|---|
| Lights at script load | Transport and command buttons dim; Play dim green, Record dim red, Loop dim amber; screen-button LEDs dim; bank A and B pads dim blue. Then it sets property 0x14 = 1 ("Pad MIDI Port") | [CODE: Arturia KL3Return.py:92-147] |
| Play LED | Bright whenever `mixer.getSongTickPos() != 0`, which is not the same as `transport.isPlaying()`. So a stopped song parked mid-way may show "playing" until the next beat blink. Beat blinks come from `OnUpdateBeatIndicator` | [CODE: Arturia KL3Return.py:178-182, 235-241]; the stale-LED effect is [GUESSED] |
| Undo / Redo LEDs | From `general.getUndoHistoryLast` and `getUndoHistoryCount` | [CODE: Arturia KL3Return.py:184-193] |
| Step pads 1-8 / page pads 9-12 | Step velocity shown as grey, empty steps nearly off, playhead dim orange, current page bright orange | [CODE: Arturia KL3Return.py:218-231, 258-265] |
| Bank A pads | FPC's pad colours when FPC is selected (`plugins.getPadInfo(chan, -1, 2, pad)`), otherwise grey | [CODE: Arturia KL3Return.py:202-213, 512-523] |

### 1.8 What is clumsy or limited (the list to beat)

1. **The faders jump.**
   - With the mixer focused, they move mixer strips 1-8. There are no motors and no takeover on that path.
   - Outside the mixer, they jump native plugin parameters.
   - Daniel's ruling (D8) is that faders are unbound by default.
   - [CODE: Arturia ArturiaCrossKeyboardKL3.py:9-30; KL3Process.py:714-720]
2. **Plugin control is narrow.**
   - 16 fixed parameters for 33 named native plugins, on the selected channel only.
   - Third-party VSTs and every mixer effect get nothing.
   - There are no pages and no learn mode, and the name list has the missing-comma bug (1.4).
3. **Repaint storms, and no idea of which screen should win.**
   - About 40 SysEx go out on nearly every refresh, because of the exact-match flag test, and none are skipped as
     duplicates.
   - Anything else on the screen gets painted over, so useful popups were switched off.
   - Together with our burst limit (L3), this may be a stability risk as well as a usability one. [GUESSED for the risk]
4. **The screen says nothing useful outside the channel rack and mixer.**
   - There is no song position or tempo, except while Rewind or Fast-forward is held.
   - Missing as well: bar and beat, loop mode, the project title after loading, the preset name, meters, and what the
     mouse is doing in FL.
5. **The dial ignores turn speed.**
   - Turning it with a plugin focused closes all plugin windows.
   - That costs one FL call per channel, per step of the dial.
   - [CODE: Arturia KL3Process.py:494-503, 436-438]
6. **Most buttons do little.**
   - The labels barely change.
   - Button 7 is unused. There is no Shift layer and no long press.
   - Hold, Chord, Scale, Arp, Bank±, Settings, MIDI, Transpose and Octave are unbound (evidence-control-map §2).
7. **The pads always write steps.** DAW pads 1-8 toggle steps in the selected channel's pattern in every context
   (surface map P8).
8. **"Master" is mislabelled.** Knob 9 and fader 9 drive the selected track, not the master. The guide does say
   "selected track".
9. **Odd side effects.** [CODE: Arturia KL3Process.py:863-870, 645-646, 681, 687, 856, 580, 618-620, 696-702, 1064-1065]
   [DOCS: IL forum t=342646]
   - Quantize hides the piano roll.
   - Loop means loop-record.
   - In step-edit mode, each step of a knob calls `transport.globalTransport(FPT_Punch, 1, GT_All)` (a function named
     "FakeMIDImsg").
   - Loop, Metronome, Tap, Save and two browser actions call `transport.globalTransport` too.
   - GlobalTransport is exactly the call that FL 26.1.7 fixed a freeze and a crash in.
10. **Dead or broken code.** These functions have zero callers, and any of them would crash if it were ever used:
    - `NoPlugin` passes a `transient` keyword that `SetCenterPage` does not accept.
    - `StereoSepChRefresh`, `SetRouteChRefresh` and `SnapModeRefresh` call methods that do not exist.
    - `BackRefresh` and `PressRefresh`.
    - `PluginParamReturn` unpacks 3 of 5 return values.
    - The three `Toggle*ChannelRack` functions, plus `PartOn`, `PadOn/Off` and `AnalogLabPreset`.

    [CODE: Arturia KL3Navigation.py:83-117, 228-250, 304-317; KL3Return.py:297-301; KL3Process.py:465-490, 760-764,
    898-968; caller counts by grep today]
11. **Non-ASCII names** (accents, "♭", emoji in track names) show as ".Undefined text." (1.6).
12. **The mixer bank stops at strips 113-120** (offset 14), but FL 2025 and later has up to 500 tracks.
    [CODE: Arturia KL3Process.py:945] [DOCS: fl-scripting.md:155, dynamic mixer]

---

## Part 2. What FL Studio's scripting API makes possible for our engine

### 2.1 Our FL and its API level

- **What is installed.** [SEEN TODAY: FL64.exe file version; folder listing of `Shared\Python`]
  - FL Studio 2026 **26.1.3.5570**, with an embedded Python 3.12 (`python312.dll`; `python312._pth` lists the zip and ".").
  - `Lib\` holds only `midi.py` and `utils.py`.
  - The socket, ctypes and select modules (`_socket.pyd`, `_ctypes.pyd`, `select.pyd`) are on disk.
- **The manual's latest version.** The official MIDI scripting manual now documents up to **API version 45**
  (`duplicatePatternData`). [DOCS: IL manual midi_scripting.htm]
- **26.1.3 is API 44.** [GUESSED, strong] Four anchors:
  - The manual dates `clearPattern` and `HW_Dirty_GraphEditor` to API 44.
  - WhatsNew dates both to 26.1.3 RC1 (#22323, #22321).
  - Our midi.py has `HW_Dirty_GraphEditor = 524288` at line 94.
  - A user reports "MIDI scripting version 45" on 26.1.7.5653. [REPORTED: Zierax/fl-studio-mcp issue #1, 2026-10-07]
- **The stubs are dated.** [DOCS: pypi.org/pypi/fl-studio-api-stubs/json; IL-Group/FL-Studio-API-Stubs README;
  MaddyGuthridge/FL-Studio-API-Stubs LICENSE.md]
  - The PyPI type stubs (`fl-studio-api-stubs`) stop at **37.0.1 (2024-08-07)**. LGPL-3.0-only, by Maddy (formerly
    Miguel) Guthridge.
  - The IL-Group copy now calls itself unmaintained and points to the FL manual and the author's repo.

So: **design against the manual (API 45), and test against API 44**, which is Daniel's build. The stubs site is a handy
mirror, but out of date.

### 2.2 The context calls (what the engine can know)

API version in brackets.

**Focus**
- `ui.getFocused(w)` [1]. Window ids: 0 mixer, 1 channel rack, 2 playlist, 3 piano roll, 4 browser, 5 plugin, 6 effect,
  7 generator, 8 plugin picker. [CODE: midi.py window constants] [DOCS: stubs, ui windows]
- `ui.getFocusedFormID()` [13] returns [DOCS: IL manual; stubs ui windows]:
  - the window number, for a main window;
  - the channel index, for an instrument plugin;
  - `(track << 6 + slot) << 16`, that is track × 4194304 + slot × 65536, for an effect.
- `ui.getFocusedFormCaption()` [1] gives the window title. `ui.getFocusedPluginName()` [5] gives the original plugin
  name, or "". [DOCS: same]
- `mixer.getActiveEffectIndex()` [25] returns `(track, slot)` of the focused effect, or None. [DOCS: IL manual]
- Maddy Guthridge's Universal Controller Script (UCS) calls `ui.getFocused` "horrible" and loops over window ids 0-4
  instead. It calls the form-ID function "horrible" too, and decodes the track and slot itself. [CODE: Maddy Guthridge,
  Universal-Controller-Script src/common/util/api_fixes.py, GPL-3.0, via a summary of the file]

**Plugins** (any plugin; addressed by channel index, or by mixer track + slot for effects)
- These all date from API 8 [DOCS: stubs plugins]:
  - `plugins.isValid`;
  - `getPluginName(index, slot, userName)`;
  - `getParamCount`, `getParamName`, `getParamValue`, `getParamValueString`;
  - `setParamValue(value, param, index, slot, pickupMode)`.
- Later additions: `getColor` [12], `getName(..., flag)` [13], `getPadInfo` [19], `getPresetCount` [15] and
  `nextPreset`/`prevPreset` [10]. The `useGlobalIndex` option came later still.
- `plugins.getName(index, slot, midi.FPN_Preset)` gives the **preset name** (`FPN_Preset = 6`). [CODE: midi.py:669-678]
  [GUESSED: that it works for every plugin type]
- **A VST reports 4240 parameters**: 4096 plus 128 MIDI CCs plus 16 aftertouch. The stubs say not all of them are used.
  [DOCS: stubs plugins] Finding the named ones costs one FL call per number, so do it once per plugin and keep the result.
  [GUESSED]

**FL's own controller links**

These let the LCD name any plugin parameter Daniel has linked in FL.
- `midi.EncodeRemoteControlID(port, chan, cc)` = `cc + (chan << 16) + ((port + 1) << 22)`. [CODE: midi.py:761-762]
- `device.findEventID(controlId)` [1] gives the linked parameter's event id, or `REC_InvalidID`.
- `device.getLinkedParamName` [10], `getLinkedValueString` [10], `getLinkedValue` [1] (0-1, or -1 if nothing is linked)
  and `getLinkedChannel` [27].
- `device.linkToLastTweaked(controlIndex, channel, globalLink, eventID)` [21] creates "a regular (or global) controller
  link for the last tweaked parameter". It returns 0 on success, 1 if nothing was tweaked, and 2 if the control is in use.
  [DOCS: IL manual; stubs device FL]
- Image-Line's MCU script reads linked values with `mixer.remoteFindEventValue(EncodeRemoteControlID(...))`. On its
  "free" page it hands knobs to FL with `device.processMIDICC`. [CODE: IL-MCU device_MackieCU.py:714-718, 746-768, 260-270]

**Channels** [DOCS: stubs] [CODE: Arturia uses most of these, KL3Process and KL3Return]
- `selectedChannel`, `channelNumber`, `channelCount`, `getChannelName`, `getChannelColor`, `getChannelType`.
- `getTargetFxTrack` (the mixer track a channel feeds).
- The step grid and step parameters, `isGraphEditorVisible`, `midiNoteOn`, and volume, pan and pitch.

**Mixer** [DOCS: stubs mixer tracks; IL manual]
- `trackNumber`, `trackCount`, `getTrackName` and `getTrackColor` (format 0x--BBGGRR).
- `getTrackVolume(i, mode)` (the mode gives dB), `getTrackPan`, and `isTrackMuted`, `isTrackSolo`, `isTrackArmed`.
- `getTrackPeaks(i, mode)`: 0 is silence, 1.0 is 0 dB, above 1 is clipping. Modes: left, right, max, inverted.
- `getSlotColor` [32], `getPluginMixLevel` [37], the EQ band functions [35], `getCurrentTempo(asInt)`, and
  `setCurrentTempo` [38].
- NI's script warns: "FL Studio's tempo API documentation is backwards!" In practice `getCurrentTempo(0)` returns
  BPM × 1000, and `getCurrentTempo(1)` returns BPM as a decimal number. [CODE: NI controller_definition.py:686-689]
  Arturia's tap-tempo code agrees with the ×1000 reading. [CODE: Arturia KL3Navigation.py:211-215]

**Transport and position** [DOCS: stubs] [CODE: IL-MCU device_MackieCU.py:985-1003 builds its LCD time readout from
exactly these]
- `transport.isPlaying`, `isRecording`, `getLoopMode`, `getSongPos`.
- `playlist.getVisTimeBar`, `getVisTimeStep`, `getVisTimeTick`.
- `mixer.getSongTickPos`, `getSongStepPos`.
- `ui.getTimeDispMin`, `ui.isMetronomeEnabled`, `ui.getSnapMode`.

**Patterns and arrangement** [DOCS: fl-scripting.md:57-72 with its citations]
- `patternNumber`, `patternCount`, `getPatternName`, `getPatternColor`, `getPatternLength`.
- Markers, and launching clips in Performance mode (`playlist.triggerLiveClip`).

**Browser and hints** [DOCS: stubs ui browser and state; IL manual]
- `ui.getFocusedNodeCaption()` (API 20 per the stubs, API 1 per the manual) and `navigateBrowserTabs` [22].
- `ui.getHintMsg()` and `ui.setHintMsg()` [1].

**Project and general** [DOCS: stubs general and ui state; IL manual]
- `general.getVersion()` returns the API version (per the stubs).
- `ui.getVersion(mode)` gives the FL version.
- `getProjectTitle` [38] and `general.getChangedFlag`.
- `general.safeToEdit()` [29] returns 1 "when safe to use setter functions".
- `getRecPPQ`.

**Device** [DOCS: stubs device/device and device/util; WhatsNew #20989]
- `getName`, `getPortNumber` and `isAssigned`.
- `getDeviceID()` [25]: the device's identity bytes, as FL saw them when it connected.
- `midiOutSysex` (the whole F0..F7 message; no size limit stated), `midiOutMsg`, and `midiOutNewMsg` (sends only if
  changed).
- `setHasMeters()`. Call it in `OnInit`, and `OnUpdateMeters` then fires.
- `isDoubleClick(index)`, `createRefreshThread`, `fullRefresh` and `hardwareRefreshMixerTrack`.
- `releaseCC` (added in 25.1.99 Beta 3, #20989).

**Talking to other scripts** [DOCS: stubs device dispatch; IL manual "receiveFrom"]
- `device.dispatch(ctrlIndex, message, sysex)` sends a short message or SysEx to scripts that declare
  `#receiveFrom=<this device>`. Such messages "are received identically to normal inputs".
- `dispatchReceiverCount` and `dispatchGetReceiverPortNumber`.
- Image-Line's MCU script uses this to drive its extender units. [CODE: IL-MCU device_MackieCU.py:700-711]

### 2.3 The callbacks, their timing and their cost

**Load and connection**

| Callback [API] | When | Use for the engine | Tag |
|---|---|---|---|
| `OnInit` / `OnDeInit` [1] | Script load and unload | Our handshake policy; warm the cache | [DOCS: stubs callbacks] |
| `OnInitAll` | Added in 24.2.99 Beta 5 (#19777) | (Runs after all scripts load) | [DOCS: WhatsNew #19777] [GUESSED meaning] |
| `OnFirstConnect` [17] | The device connects for the first time | First-run screen | [DOCS: stubs] |
| `OnProjectLoad(status)` [16] | A project loaded (status 0, 100 or 101) | Project title card | [DOCS: stubs] |

**Input**

| Callback [API] | When | Use for the engine | Tag |
|---|---|---|---|
| `OnMidiIn`, then `OnMidiMsg`, then `OnSysEx` / `OnNoteOn` / `OnControlChange` and the rest [1] | Every input event | The controls, and the inbox for a hub link | [DOCS: stubs] |

**State changes**

| Callback [API] | When | Use for the engine | Tag |
|---|---|---|---|
| `OnRefresh(flags)` [1] | "Called when something changed that the script might want to respond to." Flags as in 1.2 | **The main context trigger.** Test the flags one bit at a time | [DOCS: IL manual] [CODE: midi.py:77-94] |
| `OnDoFullRefresh` [1] | Like `OnRefresh`, but everything | Full redraw | [DOCS: stubs] |
| `OnDirtyMixerTrack(i)` [1] / `OnDirtyChannel(i, flag)` [16] | A track or channel changed. Channel flags: `CE_New`, `CE_Delete`, `CE_Replace`, `CE_Rename`, `CE_Select` | Mark one track or channel as changed | [DOCS: stubs; IL manual] |
| `OnUpdateMeters` [1] | When peak meters need updating, after `setHasMeters()` | Meters, on the pads or as a bar layout | [DOCS: stubs] [CODE: NI controller_definition.py:452, 695-718] |
| `OnUpdateBeatIndicator(v)` [1] | 0 off, 1 bar, 2 beat | Beat LEDs; a bar flash on the LCD | [DOCS: stubs] |
| `OnSendTempMsg(message, ms)` [1] | "Called when a hint message is sent to the controller display" | **Free context: FL tells us what it would show a controller** | [DOCS: IL manual] [CODE: IL-MCU device_MackieCU.py:609-614 stores it as a timed message] |
| `OnDisplayZone`, `OnUpdateLiveMode(lastTrack)`, `OnWaitingForInput`, `OnMidiOutMsg` [1] | Playlist zone changed; Performance mode changed; FL is waiting for input; a MIDI Out plugin sent something | A Performance-mode view | [DOCS: stubs] |

**Timer**

| Callback [API] | When | Use for the engine | Tag |
|---|---|---|---|
| `OnIdle` [1] | "Called frequently (roughly once every 20ms)". If it runs too slowly, "your script won't receive incoming MIDI messages fast enough" | Only a slowed-down check for missed changes | [DOCS: stubs callbacks] |

**How often `OnIdle` really fires is disputed. Measure it; don't assume it.**

| Source | Rate claimed | Tag |
|---|---|---|
| FL API stubs | about every 20 ms | [DOCS] |
| UCS docs | "roughly once every 0.05 seconds"; UCS skips a tick "if it has been too long since the last tick" | [DOCS: Universal-Controller-Script docs/contributing/overview.md] |
| An FL 2026 bridge | "approximately 20 times per second", median round trip 43 ms | [REPORTED: geezoria/FLStudioMCP PR #2, tested on 26.1.6.5639] |
| NI's code comments | about 10 ms per tick ("every 3 OnIdle calls (~30ms)") | [CODE: NI controller_definition.py:438, 674, 680] |
| A 2025 bridge | never fired on 25.2.5 | [DOCS: fl-scripting.md:102] |

**API quirks the engine must design around** (from scripts that ran into them):
- **Reading a parameter name can trigger a false "focused window" refresh.**
  - Calling `plugins.getParamName` can make FL fire a spurious `HW_Dirty_FocusedWindow` flag.
  - NI turned a feature off because it caused "a feedback loop".
  - So an engine that reads names on every focus refresh can loop forever. It needs a guard that stops it from reacting
    to the refresh it caused itself.
  - [CODE: NI controller_definition.py:643-647; mixer_definition.py:309-310]
- **Preset changes are delayed.** NI's comment: "nextPreset/prevPreset is async: getName(FPN_Preset) may return the old
  value immediately after the call". Read the name again on a later tick. [CODE: NI controller_definition.py:666-670]
- **FL does not always report effect changes.** When an effect is added or removed, `OnDirtyMixerTrack` may not fire.
  NI checks every 5 idle ticks instead. [CODE: NI controller_definition.py:672-676]
- **Calling FL at the wrong moment raises an error:** `TypeError: Operation unsafe at current time`.
  - UCS catches it. [CODE: UCS api_fixes.py `catchUnsafeOperation`, via a summary]
  - FL 26.1.3 also fixed "potential crashes when functions are called at the wrong time" (#22297).
    [DOCS: WhatsNew 26.1.3 RC1]
  - `general.safeToEdit()` [29] exists to check before changing anything.
- **Highlight calls are capped at 2 seconds** from 26.1.5 on (the DisplayRect functions that highlight part of a window).
  [DOCS: IL forum t=342068] Arturia uses 1000 ms, which is fine. [CODE: Arturia KL3Process.py:915, 936, 1056]

### 2.4 The 2026 freeze and crash record (W266 / P23)

| FL build | Scripting fixes that matter to a KeyLab script | Tag |
|---|---|---|
| 26.1.1 (2026/07/10) | #22055 ClonePattern destination; #22057 the plugin picker can be focused from a script | [DOCS: WhatsNew] |
| 26.1.2 (2026/07/16) | #22298 Global Transport commands delayed unnecessarily | [DOCS: WhatsNew] |
| 26.1.3 RC1 (2026/07/23) | #22359 crash using GlobalTransport; #22297 potential crashes when functions are called at the wrong time; #22323 clearPattern; #22321 graph-editor refresh flag | [DOCS: WhatsNew] |
| **26.1.3 (2026/07/24): Daniel's build** | **#22368 Freezes when MIDI scripts call functions in FL Studio (FIXED here)**; #22367 crash reading the script list at startup | [DOCS: WhatsNew] [SEEN TODAY: build 5570] |
| 26.1.5 (2026/08/24, build 5618) | Highlight (DisplayRect) calls capped at 2 s; undo/redo refresh flags; Mackie Control support moved into a script; `setPatternLength`; get/set swing | [DOCS: IL forum t=342068] |
| 26.1.6 (2026/09/07, build 5639) | Pattern duplication changed (#22607); FL shows a notice when a new controller connects | [DOCS: IL forum t=342331] |
| **26.1.7 (2026/10/01, build 5653)** | **#22604 freeze when a script sends a sysex message; #22725 freeze when calling the GlobalTransport function; #22689 crash when calling the GlobalTransport function** | [DOCS: IL forum t=342646] |

**What this means:**
1. The repo's line "FL 26.1.3 lists freezes when scripts call FL functions" (W266, D8) mistakes a fix for a bug. Bug 22368
   is fixed in 26.1.3.
2. But on 26.1.3, **sending SysEx and calling GlobalTransport can still freeze FL**. Those fixes landed only in 26.1.7.
3. Arturia's script already does both, so the risk is already there today:
   - it sends SysEx on every refresh;
   - it calls GlobalTransport on Loop, Metronome, Tap, Save, two browser actions, and every knob step in step-edit mode.

   [CODE: Arturia KL3Process.py:580, 618-620, 646, 681, 687, 856, 1065] [GUESSED: whether Daniel has hit it]
4. P23 should therefore do one of two things:
   - run on 26.1.7 or later, after Daniel agrees to update; or
   - stay on 26.1.3 and specifically test bursts of SysEx and calls to `globalTransport`.

### 2.5 Talking to a program outside FL

**What FL's script interpreter allows.** The reports disagree. MIDI is the only channel everyone agrees on.

- **Threads: reported blocked.** [REPORTED: geezoria/FLStudioMCP issue #1 and PR #2 (26.1.6.5639); Boyan253 bridge on
  25.2.5, per fl-scripting.md:102]
  - The error reads "daemon threads are disabled in this (sub)interpreter" (2025-26).
  - `threading` is called "non-functional" in FL 2026.
- **Sockets: reported blocked.** [REPORTED: geezoria PR #2; beatsage.ai blog 2026-02-24]
  - `_socket` calls "return NULL without raising".
  - "traditional TCP communication impossible" (geezoria). BeatSage: "No sockets".
- **Files: contested.**
  - Works: "only basic file operations work: open().read() and open('w').write()" on 26.1.6, with `os.remove` and
    `os.replace` blocked. [REPORTED: geezoria PR #2]
  - Fails: `SystemError: <class '_io.FileIO'> returned NULL...` on 26.1.7.5653 (API 45). The reporter later closed the
    issue as fixed "through MIDI configuration adjustments". [REPORTED: Zierax issue #1, 2026-10-07]
  - BeatSage: "No file I/O".
- **ctypes: reported blocked.** [REPORTED: Zierax #1; BeatSage]
  - Listed as failing on 26.1.7; BeatSage says "No ctypes".
  - The ctypes module (`_ctypes.pyd`) is on disk [SEEN TODAY], but that proves nothing.
- **Custom modules.** The manual says to put them in the shared `Python/Lib` folder. [DOCS: IL manual]
- **MIDI in and out, including SysEx: works in every bridge.** "The only way to communicate with a running FL Studio
  instance from the outside world is MIDI." [REPORTED: BeatSage; also Flapi, MadBlast0, giang17 (fl-scripting.md §7)]
- **On this machine, nothing has been tested yet.** P30 (which imports work) and the JamProbe drill are still open. There
  is no receipt in the repo. [SEEN TODAY]

**Loopback ports (the pipe between FL and the hub).**
- **Today there is no loopback.** Windows lists only "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW" (in and out) plus
  "Microsoft GS Wavetable Synth". `C:\ProgramData\Microsoft\MIDI` does not exist. [SEEN TODAY: read-only listing of the
  Windows MIDI devices; no port was opened]
- **There are two ways to get one.** Both need Daniel's OK. [DOCS: repo
  research/in-flight/fl-jam-bridge-2026-09-14/virtual-midi-and-sync.md:9-23 and 90-130, with Microsoft's links]
  - **Windows MIDI Services loopback.** Built into Windows. It survives reboots when made in the MIDI Settings app, and
    several apps can share each end. The tools that create it are a separate download.
  - **loopMIDI.** A third-party driver.
- **FL can probably see the Windows loopback.** BeatSage used Windows MIDI Services loopbacks, made at the command line,
  with FL (Feb 2026). That is community evidence that FL sees them. [REPORTED: BeatSage blog]

**How the pieces would connect.** A script can only talk to its own linked output: `midiOutSysex` sends "to the (linked)
output device". `forwardMIDICC` goes to plugins inside FL, not to ports. [DOCS: stubs device/device and device/FL] So a
hub link needs one of two layouts:
- **Two scripts:**
  - ours, on the KeyLab DAW port;
  - a thin "Aurora Link" script on the loopback port;
  - joined by `device.dispatch` and `#receiveFrom`. [DOCS: IL manual; stubs dispatch]
- **The shared-port shortcut:** the hub writes the LCD directly, because the port is shared [CONFIRMED: V2]. The FL script
  then only needs to *report* context to the hub over the loopback.

**Message size.** Flapi caps SysEx data at **1000 bytes**. Its author blames "a limitation on the length of sysex
messages" in the Windows MIDI API, where larger ones "silently fail". [CODE: Flapi `flapi/_consts.py`, MIT]
[DOCS: Flapi Unmaintained.md] A context report is a few hundred bytes at most. Keep frames small, and split anything
bigger. [GUESSED]

### 2.6 Prior art

**Flapi** (Maddy Guthridge)
- What it is: remote control of FL from outside.
  - A server script inside FL runs API calls that arrive over two loopback ports, "Flapi Request" and "Flapi Response".
  - Its SysEx header is `7D 46 6C 61 70 69` (0x7D is the non-commercial maker id, then "Flapi").
  - Message types: hello, goodbye, version, register, exec, stdout. Timeout 0.1 s.
- Licence and status: MIT; PyPI 1.0.1 (2024-04-13); **unmaintained**, "half-way through a refactor".
- Lesson: the pattern works. Its author hit the Windows SysEx size limit, and found FL's API "difficult ... many
  frustrating bugs and crashes".
- [DOCS: github MaddyGuthridge/Flapi README and Unmaintained.md; PyPI] [CODE: `_consts.py`]

**FL Studio API stubs** (Maddy Guthridge; IL-Group copy)
- What it is: type stubs and docs for the whole API.
- Licence and status: LGPL-3.0-only; PyPI 37.0.1 (2024-08-07). The IL-Group copy is marked unmaintained.
- Lesson: use it as a development aid. The FL manual (API 45) is the authority.
- [DOCS: PyPI JSON; IL-Group README]

**Universal Controller Script, UCS** (Maddy Guthridge)
- What it is: a context-aware controller framework.
  - It knows the windows (channel rack, mixer, playlist, piano roll).
  - It has plugin-specific maps: FLEX, FPC and Harmless among the natives; Vital, Serum and Spitfire among the VSTs.
  - It forwards MIDI-learn CCs to other plugins.
- Licence and status: GPL-3.0; active. Its own docs say they are "outdated due to several refactors" for v2.
- Lessons:
  - It runs on `OnIdle` ticks and skips ticks that arrive late.
  - It wraps the focus and form-ID calls.
  - It catches "Operation unsafe at current time".
- [DOCS: README; docs/contributing/overview.md] [CODE: api_fixes.py, via a summary]

**NI Komplete Kontrol FL script** (on this machine)
- What it is: focus-follow, plugin chain, track names and peak meters on NI keyboards.
- Licence: MIT, (c) 2021 Pablo Peral and 2026 Native Instruments.
- Lessons:
  - the quirks in 2.3;
  - flags tested one bit at a time;
  - meters via `setHasMeters` and `OnUpdateMeters`;
  - names kept in a cache and sent only when they change (`mixer_definition.py:98-100`).
- [CODE: NI files cited above]

**Image-Line MackieCU** (on this machine)
- What it is: Image-Line's own reference script for a controller with an LCD. Mackie Control support moved into this
  script during the FL 2026 (26.1) cycle (#20506). It shows:
  - track names and a time display;
  - FL's hint text (`OnSendTempMsg`);
  - a "free" page bound to FL's own links;
  - extender units driven by dispatch.
- Licence: Image-Line's.
- Lesson: the template for "show FL's hint", "show the linked parameter" and "time readout".
- [CODE: IL-MCU device_MackieCU.py] [DOCS: WhatsNew #20506]

**AI and MCP bridges, 2025-26** (MadBlast0, giang17, karl-andres, rosasynthesiz, Boyan253, geezoria, BeatSage)
- What they are: a loopback port, a small device script, and the real logic outside FL. They pass messages through files
  where files work, and through SysEx where they don't.
- Licences: various.
- Lesson: nobody claims tight timing, and everyone avoids sockets and threads.
- [DOCS: fl-scripting.md §7] [REPORTED: as cited]

**Licence rule for us.**
- Arturia's enums are "All rights reserved". UCS is GPL-3.0. The stubs are LGPL-3.0.
- Read them for facts only, and write our own code (D8 R8.1).
- The MIT projects (Flapi, NI, Ray Juang's parts) would allow borrowing code with credit. The house rule is still facts
  only. [CODE: headers as cited]

---

## Part 3. The engine we could build ("borrow from the default script, make it better")

This is a proposal to riff on with Daniel. Every item is [GUESSED] design unless it cites a fact above.

### 3.1 Three possible designs

**A. Everything inside FL**
- How: `device_AuroraKeyLab.py` replaces Arturia's script on the DAW port, and does context, LCD, labels and LEDs itself.
- Needs: nothing new. No loopback, and no install beyond copying the script folder.
- Pros: works today; nothing fights it; FL's data is local and instant.
- Cons: it cannot see the VJ engine or the hub.

**B. FL reports, the hub paints**
- How: the script from A, in "report" mode, sends a small context message whenever something changes, over a loopback.
  The hub already writes the LCD through the shared port [CONFIRMED V2]. It would draw chord, beat and scene **plus** FL's
  context.
- Needs: a loopback (Daniel's OK), and the P30 test of which imports work.
- Pros: one thing paints, one rate limiter, and the keyboard looks the same in and out of FL.
- Cons: two moving parts, and a loopback to keep alive.

**C. Handoff (D8's three modes)**
- How: B plus a heartbeat. If the hub goes quiet for 2 s, the script paints FL's context itself, as in A. When the hub
  returns, it hands back.
- Needs: the same as B.
- Pros: the screen is never dark, and the two never fight over it.
- Cons: the most to build.

**Recommendation:**
1. Start with **A, in a small slice**: transport, the context record, and the resting screen for each context.
2. Grow it into **C** once a loopback exists.

A answers Daniel's question on its own, and C is already D8's design.
[CODE refs for D8: docs/library/design/20261022_a16-d8-fl-script-handoff_3384d8.md:58-107]

### 3.2 The context model

**One record of FL's current state.** Only the parts that changed are rebuilt.
- **window**: decoded from `ui.getFocusedFormID()` (2.2), with `ui.getFocused` as the fallback. One of: mixer, channel
  rack, playlist, piano roll, browser, instrument (channel), effect (track, slot), plugin picker.
- **target plugin**: the focused instrument or effect; if neither, the selected channel's instrument.
  - name (`getPluginName`: both the user's name and the original);
  - preset (`getName(..., FPN_Preset)`);
  - colour;
  - the list of parameter pages (3.3).
- **channel**: index, name, colour, type, and the mixer track it feeds.
- **mixer**: selected track, name, colour, volume in dB, pan, mute/solo/arm, and peaks while meters are on.
- **pattern**: number, name, colour, length.
- **transport**: playing, recording, loop mode, bar : step : tick, tempo (mind the ×1000 quirk), metronome, snap.
- **browser**: item caption and tab.
- **project**: title [38] and whether it has unsaved changes.
- **hint**: the last `OnSendTempMsg` text and how long FL wants it shown.
- **links**: for each knob and fader, whether Daniel linked it in FL, and if so the linked parameter's name and value
  text.

**How it notices changes.** Mostly event-driven, with a slow check as a safety net.
1. `OnRefresh(flags)` tests the flags **one bit at a time** and marks parts of the record as changed:

   | Flag value | Marks as changed |
   |---|---|
   | 32 | window and target plugin |
   | 1 | mixer selection |
   | 65536 or 262144 | channel |
   | 1024 | pattern |
   | 8192 or 16384 | colours and names |
   | 256 | LEDs |
   | 131072 | undo |
   | 16 or 512 | links |

2. `OnDirtyMixerTrack` and `OnDirtyChannel` mark one track or channel.
3. A slowed-down `OnIdle` (its true rate measured in P23, not assumed) does three things:
   - checks the song position, only while playing;
   - reads the preset name again a tick after a preset change (the delay quirk);
   - checks the focused window id, one cheap call, to catch anything FL failed to flag.
4. **A guard against feedback loops**: never read parameter names in response to a refresh that the reading itself may
   have caused (the NI loop in 2.3).
5. **Compare, then draw only what changed.**
   - The resting screen, the labels and the LEDs each remember the last bytes sent.
   - Everything goes through the burst limiter: 12 per 100 ms [CONFIRMED L3], or the window P24 measures.
6. **Screens take turns:**
   - each context has a resting screen;
   - short popups (screens 23-27 and 28-30) sit on top of it;
   - when a popup's time is up, the resting screen comes back.

   This replaces Arturia's approach of repainting everything and switching popups off (1.2, 1.6).

### 3.3 Better behaviour, context by context

The headline improvements over 1.8:

- **The knobs follow the focused plugin, including effects and every VST.**
  - First choice: a hand-made map, if one exists. Arturia's 33 tables show which parameters matter on each native, and
    we can write our own maps as data.
  - Otherwise, **automatic pages**: walk `getParamCount`, keep the parameters that have names (VSTs report 4240), and
    split them into pages of 8.
  - The dial pages through them, and the screen-button labels name the page.
  - Touching a knob shows that parameter's name and value.
  - Knob steps get bigger when you turn faster, which is the turn-speed handling Arturia threw away.
- **The faders are unbound by default** (Daniel's ruling).
  - When bound, they use **takeover** (`setParamValue` or `setTrackVolume` with `PIM_AlwaysPickup`, 2.2).
  - Touching a fader shows something like "Cutoff 41% → pick up at 41%".
- **Daniel's own FL links are honoured and named.**
  - If a knob is linked in FL, the LCD shows the linked parameter's name and value.
  - A "learn" gesture could call `linkToLastTweaked`: touch a knob, wiggle anything in FL, press a screen button (2.2).
- **FL's hint text appears on the LCD** (`OnSendTempMsg`), as in Image-Line's own MCU script (2.3).
- **A resting screen for each context:**

  | Context | Resting screen |
  |---|---|
  | Plugin | plugin name + preset (big two lines, screen 14; or icon + 2 lines, screen 16) |
  | Mixer | "n Track name" in the track colour, plus volume in dB and pan (and peaks on the pads, if wanted) |
  | Channel rack | channel + pattern (keeps Arturia's useful screen) |
  | Playlist | bar : beat : tick, tempo, loop mode |
  | Piano roll | channel, pattern, snap |
  | Browser | item and tab |

- **The pads stop writing steps** unless a step-sequencer mode is chosen. That mode is a tab of its own, with its label
  lit.
- **The labels mean something in every context**, and button 7 gets a job. Long press stays UNKNOWN (C2) until a probe.
- **Arturia's bugs are left behind:**
  - the fused plugin names;
  - Loop meaning loop-record (decide with Daniel);
  - Quantize hiding the piano roll;
  - the dial closing every plugin window;
  - the Play LED keyed off the song position;
  - the bank stopping at 120 strips;
  - non-ASCII names becoming ".Undefined text." (convert them to ASCII first; `arsenal/keylab/screen.py` already has
    `ascii_clean`).

### 3.4 What we can write to the LCD (the full menu as known today)

The message is `F0 00 20 6B 7F 42 00 02 04 <screen id> <fields> F7`. Each field is `[tag] value 00`.
[CONFIRMED: the frame shape was used live, surface map Y1; screen.py:1-60 holds our encoder, which matches Arturia's byte
for byte]

**Text screens**
- Layouts:
  - 12: two lines;
  - 10 / 11: one line, normal or inverted;
  - 13: two lines inverted;
  - 14: two big lines.
- Holds: lines of text, each with a colour type and an RGB colour (0-127).
- Status: 12 is [CONFIRMED] to stay up with no flicker (Y1); the rest are INFERRED (Y5).
- FL data that fits: resting screens such as plugin + preset, channel + pattern, track.

**Text with an icon**
- Layouts:
  - 15 / 16: icon + 1 or 2 lines;
  - 26 / 27: icon popups;
  - 31: full popup with an icon.
- Holds: text plus one of 86 large icons (instrument types, the FL logo, transport and edit symbols).
- Status: INFERRED (Y5, Y7).
- FL data that fits: an icon per context (FL logo, pads, controls, metronome); a project title card.

**Popups**
- Layouts: 23, 24 and 25 (one, two or three lines).
- Holds: short-lived text, gone after about 1 second.
- Status: 23 is [CONFIRMED] (Y2); 24 and 25 are INFERRED.
- FL data that fits: FL's hints (`OnSendTempMsg`), "Saved", "Bank 9-16", bar flashes.

**Value screens**
- Layouts: 28 knob, 29 fader, 30 pad.
- Holds: value text, name, a 0-127 bar, colour.
- Status: INFERRED (Y4); Arturia draws them.
- FL data that fits: parameter peeks, takeover targets, volume in dB, velocity.

**Button labels**
- Layouts: 1-8 (one per screen button), 9 (clear all).
- Holds, for each screen button: type, line count, colour type, a small icon, an RGB colour and two text lines. There are
  22 small icons: arrows, mute, solo, arm, heart, search, mixer and more.
- Status: INFERRED (Y6).
- FL data that fits: page names, mute/solo/arm states, tabs, the step-sequencer mode.

**Screen properties**
- Layout: 0.
- Holds: one RGB value whose meaning is UNKNOWN.
- Status: INFERRED.
- FL data that fits: none yet (needs a probe).

**Never drawn by anyone**
- Layouts: 17; 18-19 carousels; 20-22 lists; 32 rename; 33 curve editor; 34 pitch wheel; 35 parameter gauge; 36 icon
  two sides; 37 welcome; 39 colour picker; 40 browser; 41-42 line keyboard; 45 three lines; 46 two small lines.
- Holds: these are named in Arturia's list but never drawn by their script, so their fields are UNKNOWN.
- Status: UNKNOWN (Y8).
- FL data that fits, and big wins if they render:
  - a real scrolling list for plugin pages and presets (20-22);
  - a browser (40);
  - a parameter gauge (35);
  - a curve editor for envelopes (33).

**Device procedures**
- Layouts: 38 boot, 43 pedal calibration, 44 bootloader.
- Status: **never send** (Y9).

**Limits:**
- Text is ASCII only, 31 visible characters a line.
- Lines 2 and 3 are upper-cased because Arturia's script chooses to. Whether the device needs that is UNKNOWN.
- About 60 ms per frame is [CONFIRMED] (Y3). 20-40 ms is UNKNOWN.
- Arturia's list has no command for raw pixels. [INFERRED: surface map, section "Output: the screen"]
- The "connect" and "release" property messages for each control may turn the device's own value popups on or off. That
  is UNKNOWN (V5).

### 3.5 What must be settled before anything ships

1. **FL version.** Updating to 26.1.7 or later removes the SysEx and GlobalTransport freezes (2.4). This is Daniel's
   call, because it is an install.
2. **P23, rewritten:**
   - measure how often `OnIdle` really fires;
   - time the bursts of `OnRefresh` calls;
   - on whichever FL build is in use, test bursts of SysEx and calls to `globalTransport` specifically;
   - then test every other FL call, one at a time (D8 R8.6).
3. **P30.** Which imports work inside FL: `open()`, `threading`, `socket`, `ctypes`. This decides between passing files
   and MIDI only.
4. **A loopback** (designs B and C only). Creating one needs Daniel's OK.
5. **Who sends connect and disconnect.**
   - While Arturia's script is loaded, it owns connect and disconnect (V3). The hub must not send them then.
   - Our script takes over that job when it replaces Arturia's.
   - Arturia's files stay untouched, and switching back is one dropdown in FL (D8 R8.7).

---

## 4. Facts that change what the repo says

- **The W266 / D8 freeze wording.** Bug 22368 is fixed in 26.1.3. The live risks on 26.1.3 are #22604 (the SysEx freeze)
  and #22725 / #22689 (the GlobalTransport freeze and crash), all fixed in 26.1.7 (2.4).
- **evidence-control-map §5, "no pickup for faders".** True for mixer faders (`pickupMode` 0). Plugin faders pass
  `pickupMode` 2, which follows FL's global pickup setting (1.3).
- **evidence-control-map §1, "Loop".** The Loop button is loop-*record* (`FPT_LoopRecord`) (1.3).
- **New:** Arturia's preset buttons are broken for BassDrum, Fruit kick, MiniSynth and PoiZone, because three commas are
  missing (1.4).
- **New:** Arturia's refresh test looks for an exact flag value instead of checking each flag, so it repaints about 40
  SysEx on almost every refresh (1.2).

## 5. Probes worth running with Daniel present (nothing was sent today)

| Probe | Question | Why |
|---|---|---|
| LCD-lower | Does line 2 of screen 12 show lower case if we don't upper-case it? | Chord names like "Am" and "vi" (screen.py notes the problem) |
| LCD-Y8 | Do screens 20-22 (lists), 35 (gauge), 40 (browser) and 39 (colour picker) render with guessed fields? | A real menu for plugin pages and presets |
| Burst pacing | Why does FL's 40-message refresh not freeze the device, when our 36-message burst did? Compare the gaps between messages with a MIDI monitor on the hub's side of the shared port, if Windows MIDI Services allows it | Tells the rate limiter its true ceiling |
| P23 / P30 | As in 3.5 | Decides between designs A, B and C |
| Wheel port | In DAW mode, do pitch bend and the mod wheel arrive on the DAW port or the MIDI port? | Arturia's wheel code may never run |
| Property 0x14 | Does "Pad MIDI Port = 1" move pad banks A-D onto the DAW port? Arturia remapping notes 36-59 for FPC on the DAW port suggests it does | Where pads arrive when FL is closed (P2) |

## 6. Sources

**Local, read-only**
- `C:/Users/L5/Documents/Image-Line/FL Studio/Settings/Hardware/Arturia KeyLab mk3/`:
  - device_KL3.py and device_KeyLab mk3 MIDI.py;
  - KL3Process.py, KL3Plugin.py, KL3Navigation.py, KL3Return.py, KL3Display.py, KL3Pages.py, KL3Buttons.py,
    KL3Dispatch.py, KL3SeqParam.py, KL3Connexion.py;
  - ArturiaVCOL.py, ArturiaCrossKeyboardKL3.py;
  - IntegrationPatchId.py, ParamId.py, ScreenId.py, LedId.py, images_sub_enums.py;
  - KeyLab_mk3__1_0__2024_08_27__FL_Studio__DAW_User_Guide.pdf (text extracted to scratch).
- `.../Settings/Hardware/NI Komplete Kontrol/`: controller_definition.py, mixer_definition.py, LICENSE.
- `.../Settings/Hardware/MackieCU/device_MackieCU.py`.
- `.../Settings/Hardware/KORG Keystage/device_KorgKeystage_Daw.py`. Transport only, but it tests the refresh flags one bit
  at a time (line 144).
- `C:/Program Files/Image-Line/FL Studio 2026/`:
  - the FL64.exe version;
  - the `Shared/Python/` listing and `Shared/Python/Lib/midi.py`;
  - `WhatsNew.rtf` (converted to `whatsnew.txt` in scratch).
- The Windows MIDI device list (read-only).
- Repo:
  - research/reviewed/keylab-liberation-2026-10-22/keylab-full-surface-map-2026-10-23.md
  - research/reviewed/keylab-liberation-2026-10-22/evidence-control-map-2026-10-22.md
  - research/in-flight/fl-jam-bridge-2026-09-14/fl-scripting.md
  - research/in-flight/fl-jam-bridge-2026-09-14/virtual-midi-and-sync.md
  - docs/library/design/20261022_a16-d8-fl-script-handoff_3384d8.md
  - docs/WISHLIST.md:1781 (W266)
  - arsenal/keylab/screen.py:1-60
  - state/arsenal/keylab/receipts/screen-20261023-012612.json

**Web** (fetched 2026-10-24)
- Image-Line manual, MIDI scripting:
  https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/midi_scripting.htm
- API stubs pages, all under https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/:
  - callbacks/
  - ui/windows/, ui/state/, ui/browser/
  - plugins/
  - device/device/, device/fl/, device/dispatch/, device/util/
  - general/fl%20state/
  - mixer/tracks/
- The stubs themselves:
  - IL-Group copy: https://github.com/IL-Group/FL-Studio-API-Stubs
  - Maddy Guthridge's copy: https://github.com/MaddyGuthridge/FL-Studio-API-Stubs (LICENSE.md)
  - PyPI: https://pypi.org/pypi/fl-studio-api-stubs/json
- Flapi:
  - https://github.com/MaddyGuthridge/Flapi
  - https://github.com/MaddyGuthridge/Flapi/blob/main/Unmaintained.md
  - https://raw.githubusercontent.com/MaddyGuthridge/Flapi/main/flapi/_consts.py
  - https://pypi.org/pypi/flapi/json
- Universal Controller Script:
  - https://github.com/MaddyGuthridge/Universal-Controller-Script
  - https://raw.githubusercontent.com/MaddyGuthridge/Universal-Controller-Script/main/docs/contributing/overview.md
  - https://raw.githubusercontent.com/MaddyGuthridge/Universal-Controller-Script/main/src/common/util/api_fixes.py
- FL release threads:
  - 2026.1.7: https://forum.image-line.com/viewtopic.php?t=342646
  - 2026.1.6: https://forum.image-line.com/viewtopic.php?t=342331
  - 2026.1.5: https://forum.image-line.com/viewtopic.php?t=342068
- Reports on what FL's script interpreter allows:
  - https://github.com/geezoria/FLStudioMCP/pull/2
  - https://github.com/geezoria/FLStudioMCP/issues/1
  - https://github.com/Zierax/fl-studio-mcp/issues/1
  - https://beatsage.ai/blog/fl-studio-midi-breakthrough
