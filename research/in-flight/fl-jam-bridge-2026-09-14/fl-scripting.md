# FL Studio scripting for the jam bridge

Lane: FL STUDIO SCRIPTING · researched 2026-09-14 (late night) · read-only on DESKTOP-5886HDP
Goal it serves: Claude plays bass lines, drum patterns and chord backings **inside FL Studio** (his Kontakt instruments, Splice samples) in time, while Daniel improvises on the KeyLab 88 mk3, and the piano page keeps showing everything.

Confidence tags: **[official]** = Image-Line manual or IL-maintained API docs · **[local]** = read off this machine tonight · **[community]** = third-party repo/forum, not verified by me · **[inference]** = my reasoning, not a sourced fact.

---

## 0. Short answer

1. **You can't inject notes or commands into FL from outside without a MIDI port that FL can open.** Every working bridge I found (Flapi, the six-plus FL MCP servers from 2025-2026) uses a virtual loopback port on Windows, and all of them name loopMIDI. Windows MIDI Services has its own loopback transport, and it is registered on this machine. But its diagnostic "Service Test Loopback" ports don't show up in WinMM apps, and no one has confirmed that user-created loopbacks do. So **step one is Daniel's OK for a loopback port** (loopMIDI, or a Windows MIDI Services loopback made with Microsoft's tools). Both mean a download or creating a port, which I can't do in this lane.
2. **A device script (`device_*.py`) is the conductor. The notes themselves should be plain MIDI.** The MIDI Controller Scripting API can start and stop the transport, set tempo (a new dedicated function since 25.2.4, or `general.processRECEvent(REC_Tempo)`), switch or clone or clear patterns, flip step-sequencer steps and per-step pitch, trigger Performance-mode clips with quantised launch, reroll Loop Starter channels, and send MIDI/SysEx out. It **cannot write piano-roll notes** into a pattern. Its `channels.midiNoteOn` plays a note live but does not store it.
3. **For in-time backing, let FL's own sequencer keep time.** The steadiest setup is to have Claude *edit* what FL is looping (step grid, pattern choice, clip launches quantised to the bar) instead of streaming every note in real time over a loopback. Streaming live notes still works well for expressive lines, but Windows scheduling adds jitter. **[inference]**
4. **Piano roll scripts (`.pyscript`) can write real notes** (`flpianoroll.score.addNote`), but nothing documented lets you trigger them remotely. The community workaround is to focus FL's window and send the run-last-script shortcut as a keystroke. That steals focus mid-jam, so it only suits the gaps between takes.
5. **FL has no Ableton Link.** Forum requests run from 2023 to 2026, and staff replied "No news" in Aug 2025. It **does** have MIDI clock out ("Send master sync") and, since 21.1 (2023), external MIDI clock in.
6. **The sandbox is the open risk.** One 2025 bridge says FL 25.2.5 device scripts run in a sub-interpreter that blocks threads, sockets and most `os` file calls, and never calls `OnIdle`. Other 2026 bridges read and write JSON files from their device script, and IL's docs still describe `OnIdle` as firing about every 20 ms. **Build as if MIDI in and MIDI out are the only channels you have.** Treat file I/O as "maybe" and sockets as "no" until a drill on Daniel's 26.1.3 settles it (section 4).

---

## 1. What is on this machine (read-only census, 2026-09-14) [local]

| Item | Finding |
|---|---|
| FL Studio | **FL Studio 2026 26.1.3.5570** (active; registry `Shared\Paths` → `C:\Program Files\Image-Line\FL Studio 2026\FL64.exe`) and FL Studio 2025 25.2.5.5319 are both installed. The latest public build is 2026.1.6 (7 Sep 2026) ([forum](https://forum.image-line.com/viewtopic.php?t=342331)), so he is three point releases behind. |
| Local changelog | `C:\Program Files\Image-Line\FL Studio 2026\WhatsNew.rtf`, with dated entries up to 26.1.3 RC1 (2026-07-23). Cited below as "WhatsNew #id". |
| User data folder | `C:\Users\L5\Documents\Image-Line\FL Studio\Settings\` contains `Hardware\`, `Piano roll scripts\` (empty), `FL Studio Remote Scripts\` (empty) and `Audio scripts\` (empty). |
| User MIDI scripts | `Settings\Hardware\` holds vendor folders: Arturia KeyLab mk3, KeyLab Essential (mk3), MKII, MiniLab 3/37/MKII, Akai Fire, KORG Keystage, MackieCU, NI Komplete Kontrol, Novation, SMK-37 Elite, Solid State Logic. There is **no custom or bridge script yet**. |
| KeyLab 88 mk3 routing in FL 26 | Registry `HKCU\Software\Image-Line\FL Studio 26\Devices\MIDI input`: **"KeyLab 88 mk3 MIDI"** is enabled, **port 0**, script folder "KeyLab mk3 Arturia dev". **"KeyLab 88 mk3 DAW"** is enabled, **port 236**, script folder "KeyLab mk3". The output side matches (0 and 236), with Sync off. |
| Other ports FL has seen | FLkey MIDI (236/237, Sync on for MIDIOUT2), Focusrite USB MIDI (disabled), CHMidi-2.3, KeyLab mkII 88, "USB Midi", Microsoft GS Wavetable Synth. **No loopback port of any kind** appears in the FL 25 or FL 26 device lists. |
| Embedded Python | `C:\Program Files\Image-Line\FL Studio 2026\Shared\Python\` holds a **CPython 3.12 embeddable** build (`python312.dll`, `python312.zip` with 599 entries, `_pth`). `Lib\` contains only `midi.py` and `utils.py`, which are the MIDI-scripting helper modules, so this is the scripting runtime. The stdlib zip **contains** `socket`, `threading`, `selectors`, `asyncio`, `subprocess`, `http.server`, `urllib.request` and `json`, with `_socket.pyd`, `select.pyd` and `_asyncio.pyd` next to it. Those files being present does **not** mean the device-script sandbox allows them (section 4). The engine DLL references `Py_InitializeFromConfig` and `PyImport_AppendInittab`. I did not find sub-interpreter symbols by plain string search, which proves nothing either way. |
| Factory piano roll scripts | `System\Config\Piano roll scripts\`: Arpeggiator, Euclidean, Humanize, Note repeater sprinkler, Select by velocity. `System\Tools\Chord progression\cpt.pyscript` and `stack.pyscript` show the Chord Progression tool is itself a pyscript. |
| Factory Remote scripts | `System\Config\FL Studio Remote Scripts\`: `rerollLSloop`, `rerollLSsample`, `rerollLSsteps` (call `channels.rerollLoopStarterLoop` / `rerollLoopStarterSteps`), `filleach`, `flrInit`. |
| Windows MIDI stack | Service `midisrv` (Windows MIDI Service) is **running**. `HKLM\SOFTWARE\Microsoft\Windows MIDI Services\Transport Plugins` includes `Midi2LoopbackMidiTransport` and `Midi2VirtualMidiTransport`. Drivers32 shows `midi1 = wdmaud2.drv` and `MidisrvTransferComplete = 1`, so WinMM is routed through the new service. **No** "Windows MIDI Services" tools folder is in Program Files, so the MIDI Settings app and console for creating loopbacks are not installed. |
| Other music software | Kontakt 8 (8.12.1), Splice Bridge 5.1.1, Splice INSTRUMENT 1.1.15, Arturia MIDI Control Center 1.23 and USB MIDI driver 1.7. **loopMIDI is not installed.** |

---

## 2. MIDI Controller Scripting API: what it can do

### 2.1 Basics [official]
- It is Python device scripts that FL runs itself, with nothing to install. A script lives at `Documents\Image-Line\FL Studio\Settings\Hardware\<folder>\device_<name>.py`. The `device_` prefix is required, and a `#name=` line at the top makes it appear under **MIDI Settings → Controller type** with a "(user)" suffix. The feature is **Fruity Edition and up**. ([IL manual: MIDI Scripting](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/midi_scripting.htm), current manual, undated)
- A script is bound to **one input device** in MIDI Settings, and FL matches input and output by port number. So a bridge script needs **its own input port**, which means a loopback, because the KeyLab ports are already bound to Arturia's scripts. [official + local]
- Modules: `transport`, `mixer`, `channels`, `patterns`, `playlist`, `arrangement`, `ui`, `device`, `general`, `plugins`, `launchMapPages`, `screen`, plus the helper modules `midi` and `utils`. ([IL-maintained API stubs index](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/)). The scripting API was introduced in FL 20.7 ([flmidi-101](https://flmidi-101.readthedocs.io/en/latest/scripting/fl_midi_api.html)).
- Debugging: **View → Script output**, one tab per script ([stubs: getting started](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/tutorials/getting_started/)).

### 2.2 Callbacks (event model) [official]
Source: [stubs: callbacks](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/callbacks/)
- Inbound MIDI: `OnMidiIn` runs first and is meant for filtering. `OnMidiMsg` is the main handler. Then come the per-type handlers: `OnNoteOn`/`OnNoteOff`/`OnControlChange`/`OnProgramChange`/`OnPitchBend`/`OnKeyPressure`/`OnChannelPressure`, plus **`OnSysEx`**. Setting `event.handled = True` stops FL's default processing, so notes on the command port don't also play the selected channel.
- **`OnIdle`**: the stubs say it runs roughly every 20 ms and must stay fast. This is the only timer-like hook. **No timers or threads are documented.** `device.repeatMidiEvent(event, delay, rate)` can repeat an event on a millisecond schedule ([stubs: device](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/device/device/)).
- Timing and state hooks: **`OnUpdateBeatIndicator(value)`** (0 = off, 1 = bar, 2 = beat), which gives a script a beat and bar tick from FL's clock. Also `OnRefresh(flags)` / `OnDirtyChannel` / `OnDirtyMixerTrack`, `OnUpdateLiveMode` (Performance mode), `OnProjectLoad`, `OnMidiOutMsg` (MIDI coming out of a MIDI Out plugin), `OnInit`/`OnDeInit`.

### 2.3 Capability map for jamming

| Need | API | Notes |
|---|---|---|
| Play / stop / record | `transport.start()`, `stop()`, `record()`, `isPlaying()` | [stubs: transport](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/transport/) [official] |
| Pattern vs song loop | `transport.getLoopMode()` / `setLoopMode()` (toggle) | same |
| Jump or scrub position | `transport.setSongPos()` / `getSongPos()`, markers via `markerJumpJog` | same |
| **Set tempo** | `general.processRECEvent(midi.REC_Tempo, bpm*1000, midi.REC_Control \| midi.REC_UpdateControl)` | Tempo is stored as 1000 × BPM ([stubs: global REC events](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/midi/__rec_events/global%20properties/)) [official]. **New:** WhatsNew #21346 "added a function to set tempo", #21347 time base and numerator, #21390 float tempo via `mixer.SetCurrentTempo`. All shipped in **25.2.4 RC1 (2026-01-26)** [local]. The stubs site doesn't list the setter yet, so check the exact name in `midi.py` or on the stubs site before relying on it. |
| Read tempo / position | `mixer.getCurrentTempo()`, `mixer.getSongTickPos()`, `getSongStepPos()`, `getRecPPS()` | [stubs: mixer properties](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/mixer/properties/) |
| Swing | `REC_MainShuffle` via processRECEvent. New get/set swing functions arrived in WhatsNew #21791, **26.1 Beta 6 (2026-05-05)** [local] | |
| **Drum patterns** (step sequencer) | `channels.getGridBit` / `setGridBit(chan, step, on)`, `getStepParam`, `setStepParameterByIndex(chan, patNum, step, param, value)` | The step parameters include **note pitch**, velocity, release, fine pitch, pan, Mod X/Y and shift ([stubs: channels sequencer](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/sequencer/)). So **monophonic bass lines in step mode are possible** too (per-step pitch). [official; per-step pitch for bass is my inference] |
| Live note on a channel (not stored) | `channels.midiNoteOn(chanIndex, note, velocity, midiChan=-1)`; velocity 0 sends note-off | Plays live. Does **not** write to the piano roll ([stubs: channels notes](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/notes/)) [official]. Whether FL records these while recording is untested. |
| Patterns | `patterns.jumpToPattern`, `patternNumber/Count`, `get/setPatternName`, `getPatternLength`, `clonePattern` (API v25), `findFirstNextEmptyPat`, `selectPattern` | [stubs: patterns properties](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/patterns/properties/). **New in the local changelog:** `setPatternLength`/`incrementPatternLength` (#21585, 26.1 Beta 1, 2026-03-24, fixed in #21751 Beta 4); `movePattern` (#21263, 25.2.3, 2025-12-17); ClonePattern destination index (#22055, 26.1.1, 2026-07-10); **"added function to clear a pattern"** (#22323, 26.1.3 RC1, 2026-07-23). [local] |
| **Clip launching in time** | `playlist.triggerLiveClip(track, block, flags, velocity)`, with trigger and position snap: off, 1/4, 1/2, 1, 2 or 4 beats, or auto | Performance mode. Launches are quantised, so a pattern change lands on the bar ([stubs: playlist performance](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/playlist/performance/)) [official] |
| Loop Starter reroll | `channels.rerollLoopStarterLoop(chan, 1)`, `channels.rerollLoopStarterSteps(chan, 1)` | Seen in factory FL Studio Remote scripts [local]. I have not checked whether they are exposed to device scripts or only to the Remote runtime. |
| MIDI out | `device.midiOutMsg(...)`, `midiOutNewMsg`, **`midiOutSysex(bytes)`** (needs F0…F7), `directFeedback` | The output goes to the port **linked** to the script's input port ([stubs: device](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/device/device/)). This is how a script can report state (bar ticks, pattern changes, tempo) back to Claude and the piano page. |
| Script-to-script | `device.dispatch(...)` to other device scripts | [IL manual](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/midi_scripting.htm) |
| Master sync from script | `device.setMasterSync()` (v18) / `getMasterSync()` (v19); the docs discourage it | [stubs: device](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/device/device/) |
| Plugins | `plugins.getParamValue/setParamValue` and similar | It cannot **load** a plugin or an audio file, and cannot render ([rosasynthesiz/flstudio-mcp README](https://github.com/rosasynthesiz/flstudio-mcp)) [community] |

Recent **scripting stability** fixes worth knowing about [local, WhatsNew]:
- 26.1.3 RC1 (2026-07-23): #22367 crash while reading the MIDI script list at startup, #22368 **freezes when scripts call FL functions**, #22297 "potential crashes when functions are called at the wrong time", #22359 crash with GlobalTransport, #22357 **Performance mode broken with external MIDI sync**.
- 26.1.2 (2026-07-16): #22291 MIDI Out didn't send notes when FL wasn't playing; #22298 GlobalTransport commands delayed.
- 26.1 RC1 (2026-06-24): #22078 "TPythonSession.ThreadEnded" error; #21933 realtime tempo map while recording MIDI; #21965 external MIDI sync didn't work properly.

Takeaway **[inference]**: the API was patched heavily during 2026. Upgrading to 2026.1.6 before building the bridge is sensible, and it needs Daniel's OK.

---

## 3. Piano Roll scripting (`.pyscript`)

- **Where scripts live:** `Documents\Image-Line\FL Studio\Settings\Piano roll scripts\*.pyscript`. They appear in the piano roll's Scripts / Tools menu ([IL manual: Piano roll Scripting API](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_scripting_api.htm), manual text references FL 2024+) [official].
- **They can write real notes:** `flpianoroll.score` gives `addNote(Note)`, `getNote`, `deleteNote`, `clearNotes`, `noteCount`, `PPQ`, `tsnum`/`tsden`, and markers. A `Note` has number, time, length, velocity, pan, release, color (MIDI channel), fcut/fres, slide, porta, muted and selected. `ScriptDialog` builds knob, combo and text UIs, and parts of the stdlib are importable (e.g. `random`) ([IL manual](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_scripting_api.htm); [stubs: flpianoroll](https://il-group.github.io/FL-Studio-API-Stubs/piano_roll_scripting/flpianoroll/)) [official].
- **They are isolated:** `flpianoroll` isn't available in MIDI controller scripts, and nothing documented lets a controller script run a piano roll script ([stubs](https://il-group.github.io/FL-Studio-API-Stubs/piano_roll_scripting/flpianoroll/)) [official].
- **Remote triggering is a hack in every community bridge:**
  - **karl-andres/fl-studio-mcp** and **giang17/fl-studio-mcp** write a JSON note request, bring FL to the foreground, then send **Ctrl+Alt+Y** (Cmd+Opt+Y on macOS) to re-run the armed script. The script has to be started once per session from Tools → Scripting ([giang17 README](https://github.com/giang17/fl-studio-mcp); [karl-andres ComposeWithLLM.pyscript on Glama](https://glama.ai/mcp/servers/@karl-andres/fl-studio-mcp/blob/b2798b311ae4b02785bc8f4c2ab040f674a06584/scripts/ComposeWithLLM.pyscript)) [community].
  - **rosasynthesiz/flstudio-mcp** does the same with a generated `MCP_Apply` pyscript: it forces focus briefly, then sends the run-last-script shortcut ([README](https://github.com/rosasynthesiz/flstudio-mcp)) [community].
  - **MadBlast0/Fl-Studio-MCP** skips keystrokes. The user runs Tools → Scripting → FL Bridge Notes by hand, or binds a hotkey ([README](https://github.com/MadBlast0/Fl-Studio-MCP), commits 2026-09-07..09) [community].
- **FL 2026 additions:** Gopher can **generate piano roll scripts on demand** ([IL: What's new in 2026](https://www.image-line.com/fl-studio/release/2026)), and WhatsNew #22284 (26.1 RC1) confirms "Storing a piano roll script from Gopher" [local]. There was a freeze when VFX Script and piano roll scripts ran together, fixed in #21906 (26.1 Beta 8, 2026-05-27) [local].
- **Fit for the jam [inference]:** good for writing a chord or bass progression into a pattern **between** takes, so FL then plays it sample-accurately. Wrong for changes in the middle of a take, because the keystroke trick steals focus from FL and whatever Daniel is doing, which clashes with the no-focus-steal rule and with a musician playing.

---

## 4. The sandbox question (threads, sockets, files, OnIdle)

Evidence, roughly in order of weight:

1. **IL docs:** they say nothing about sockets, threads or file I/O. Custom modules can go in the shared Python Lib folder ([IL manual](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/midi_scripting.htm)). `OnIdle` fires about every 20 ms ([stubs callbacks](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/callbacks/)). [official, undated]
2. **Older community guide:** calls the interpreter a stripped-down custom build of Python 3.9, with most system modules removed (threading and similar) and threads "broken" ([flmidi-101](https://flmidi-101.readthedocs.io/en/latest/scripting/fl_midi_api.html)). This is **stale for 2026**: the local runtime is CPython **3.12** and its stdlib zip includes socket and threading. [community, pre-2025; local contradicts the version]
3. **Boyan253/fl-studio-2025-ai-bridge:** says that on **FL 2025 build 25.2.5** control-surface scripts run in a **CPython sub-interpreter that blocks threads, sockets and most `os` filesystem calls, and never calls `OnIdle`**. Its bridge uses **two fixed JSON files** for RPC plus a **MIDI note sent to a loopMIDI port** to wake `OnMidiIn`. It doesn't mention FL 2026 ([GitHub](https://github.com/Boyan253/fl-studio-2025-ai-bridge); [Glama listing](https://glama.ai/mcp/servers/Boyan253/fl-studio-2025-ai-bridge)). [community, 2025-2026]
4. **MadBlast0 (tested on FL 2026, Sept 2026) and giang17:** both have the device script **read and write JSON files**, woken by a MIDI note (note 127 for MadBlast0). MadBlast0's script runs arbitrary `exec` payloads ([MadBlast0](https://github.com/MadBlast0/Fl-Studio-MCP); [giang17](https://github.com/giang17/fl-studio-mcp)). [community]
5. **Local:** the Arturia KeyLab mk3 script he uses defines `OnIdle()` (`device_KL3.py:157`). A vendor wouldn't ship a dead callback, but that doesn't prove it fires on 26.1.3. [local]
6. **Flapi** was abandoned partly because the **Windows MIDI API silently drops SysEx over a fixed size**, and the author found FL's Python API buggy and crash-prone ([Flapi Unmaintained.md](https://github.com/MaddyGuthridge/Flapi/blob/main/Unmaintained.md)). [community]

**Working stance [inference]:**
- **Sockets and threads: assume no.** Nothing shows them working, one source says they're blocked, and every 2025-2026 bridge avoids them.
- **File I/O: likely allowed** for plain `open()` in the user data folder, based on two 2026 bridges. `os` calls may still be blocked.
- **OnIdle: uncertain.** Design so the **MIDI input wakes the script** and keep all logic event-driven. Use `OnUpdateBeatIndicator` for bar and beat ticks.
- **SysEx: keep messages small** (tens of bytes). Encode commands as CC/NRPN or short SysEx. Don't ship JSON over MIDI.

**Drill to settle it (needs Daniel present plus a loopback port):** a 30-line `device_JamProbe.py` that, in `OnInit`, tries `import socket, threading, os`, writes a file to the user data folder, and prints the results to Script output. It also counts `OnIdle` calls per second and logs `OnUpdateBeatIndicator` while FL plays. The results would be an executed drill with a dated receipt, which the drill doctrine requires.

---

## 5. How FL routes external MIDI (input, output, clock)

Source unless noted: [IL manual: MIDI Settings](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_midi.htm) [official, current manual]

- **Input:** each device in the Input list is Enabled, gets a Controller type (a script or generic), and a **port number from 0 to 255**. With a generic controller, notes go to the **selected Channel Rack channel**. Other input options:
  - **Omni preview MIDI channel:** on that MIDI channel, each key triggers a different Channel Rack entry, starting at C4. That's a drum-kit mode: one MIDI channel plays every channel in the rack.
  - **Performance mode MIDI channel:** notes trigger Playlist clips.
  - **Song marker jump MIDI channel:** notes jump between time markers.
  - Also: Pickup (takeover), foot pedal note-off, and "Update MIDI scripts".
- **Routing a port straight to one instrument (bypassing "selected channel"):** in the plugin wrapper (gear icon → settings), a **VST's MIDI input port** can be set to match a controller's port. That plugin then gets that port's MIDI **no matter which channel is selected** ([IL manual: Plugin Wrapper](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/wrapper.htm)). FL native plugins mostly lack this setting ([forum t=296151](https://forum.image-line.com/viewtopic.php?t=296151)). **For the jam:** Kontakt (a VST) can listen to the "Claude bass" port while the KeyLab keeps playing the selected piano channel. Inside that port, Kontakt's own MIDI channels can split bass, keys and pads. [official + inference]
- **MIDI Out plugin:** sends piano-roll or pattern notes out on 16 channels to any of 256 ports. It can drive external hardware or **another plugin whose wrapper input port matches**, and note colour can map to MIDI channel ([IL manual: MIDI Out](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/MIDI%20Out.htm)). **For the jam:** if a loopback port is added, a MIDI Out channel copying the backing pattern could mirror FL's backing notes out to the piano page. That page is Chrome Web MIDI, so it would need a port Chrome can see (loopMIDI works for WinMM apps; Chrome visibility is another lane's question). [official + inference]
- **MIDI clock out:** turn on **Send master sync** on an output port, with synchronization type MIDI clock. It requires Options → Enable MIDI master sync. IL warns against enabling it for devices that don't do transport. [official] This machine has Sync = 1 only on "MIDIOUT2 (FLkey MIDI)" [local].
- **MIDI clock in:** "External clock sync" plus an offset in ms lets FL follow external MIDI clock. IL warns that tempo-dependent effects may misbehave [official]. Added in **FL 21.1** (RC July 2023, released Aug 2023) ([IL: 21.1 what's new](https://www.image-line.com/fl-studio-news/fl-studio-211-whats-new); [forum t=310469](https://forum.image-line.com/viewtopic.php?t=310469)). Performance mode with external sync was broken until 26.1.3 RC1 (#22357) [local].
- **Ableton Link: not supported.** The request thread runs July 2023 to May 2026, and the site admin's reply in Aug 2025 was "No news" ([forum t=308744](https://forum.image-line.com/viewtopic.php?t=308744); also [t=157443](https://forum.image-line.com/viewtopic.php?t=157443)). The 2025.2 and 2026 feature lists don't mention it ([AlternativeTo 2025.2](https://alternativeto.net/news/2025/11/fl-studio-2025-2-adds-fruity-slicer-2-emphasizer-new-genres-and-smarter-tools/); [IL 2026](https://www.image-line.com/fl-studio/release/2026)).
- **Recording accuracy:** the 2026.1.6 notes mention much less jitter when recording incoming MIDI, including across tempo changes ([forum t=342331](https://forum.image-line.com/viewtopic.php?t=342331), 2026-09-07). That thread's feature summary looked cumulative (it repeated 26.1-beta items), so only this jitter item is treated as new in .6, at **medium confidence**. Separately, #21933 (26.1 RC1) added a realtime tempo map while recording MIDI [local].

### Loopback ports on Windows (the gating dependency)
- Every FL bridge above names **loopMIDI** on Windows ([Flapi](https://github.com/MaddyGuthridge/Flapi), [fruityloops-mcp](https://github.com/quinnjr/fruityloops-mcp), [rosasynthesiz](https://github.com/rosasynthesiz/flstudio-mcp), [Boyan253](https://github.com/Boyan253/fl-studio-2025-ai-bridge)). [community]
- **Windows MIDI Services:**
  - It ships user loopbacks (MIDI 1.0 "BLOOP", MIDI 2.0 "LOOP") separate from the diagnostic loopback ([Microsoft: MIDI Services overview](https://microsoft.github.io/MIDI/overview/)).
  - Microsoft's Feb 2026 post says loopbacks work for all MIDI 1.0 and 2.0 apps without extra drivers. They're managed in the **MIDI Settings app** from a separate tools download, and the rollout is phased ([Windows Experience Blog, 2026-02-17](https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/)). [official]
  - Real-world testing in **Aug 2026** on build 26200 found the diagnostic "Service Test Loopback A/B" **invisible to WinMM apps and to Ableton Live**. Visibility of user-created loopbacks was **unconfirmed**, and the tester says loopMIDI is still the practical choice ([gopie on note.com](https://note.com/gopie/n/n0403fc1003a9?hl=en)). [community, Aug 2026]
  - This matches tonight's known fact that Chrome can't see the Service Test Loopback. FL uses WinMM, and FL's device list has never shown it [local].
- **Both routes need Daniel's OK:** loopMIDI is a download plus a port, and a MIDI Services loopback needs the tools download plus a port.

---

## 6. FL Studio 2025 / 2026 features relevant to jamming

| Feature | What it is | Jam relevance [inference unless noted] | Source |
|---|---|---|---|
| **Loop Starter** (2025) | Instant genre-based loop and one-shot stacks in the Channel Rack. You roll the dice to reroll, send the result to the playlist, and it detects key (#20983). | A fast, in-key drum and bass bed. Scripts can reroll channels (`rerollLoopStarterLoop/Steps`). The expanded library needs **FL Cloud**. | [IL 2025 release (2025-07-10)](https://www.image-line.com/fl-studio-news/fl-studio-2025-whats-new-2); [IL 2026](https://www.image-line.com/fl-studio/release/2026); local WhatsNew |
| **Gopher** | 2025: a multilingual help assistant. 2026: organises tracks, sets levels, routes audio, **generates Piano roll and VFX scripts**, and (in 2026.1.x, experimental) controls some FL and plugin features. IL says it doesn't train on user data. | A second pair of hands **inside** FL. It has no documented external API, so it can't be part of an automated bridge. | [IL 2026](https://www.image-line.com/fl-studio/release/2026); [MusicTech](https://musictech.com/news/gear/fl-studio-2026-everything-you-need-to-know/); [forum 2026.1.6](https://forum.image-line.com/viewtopic.php?t=342331) |
| **Chord Progression tool + Bassline Generator** (2025) | The progression tool is a pyscript on disk (`System\Tools\Chord progression\cpt.pyscript`). The bassline generator extends it. | A ready model for "write progression + bass into a pattern". Its code is readable on disk as a reference. | [IL 2025](https://www.image-line.com/fl-studio-news/fl-studio-2025-whats-new-2); local |
| **Chord panel / chord detection** (2026) | Detects chords in the piano roll and live from MIDI input (#18941), suggests in-key chords, and adds a Chord Stamp tool with voice-leading modes. | FL's own view of Daniel's live harmony, a counterpart to the riff analysis on the piano page. | [IL 2026](https://www.image-line.com/fl-studio/release/2026); local WhatsNew #18941 |
| **Audio Logger** (2026) | Keeps the last 60 s of master output. | Catches the improvisation after it happens, with no arming. | [IL 2026](https://www.image-line.com/fl-studio/release/2026); [Gearnews](https://www.gearnews.com/fl-studio-daw-software/) |
| **Performance mode** | Launches Playlist clips from MIDI or script with quantised trigger and position snap. 2026.1.x added a marker count and spacing popup. | The cleanest way to switch sections in time (verse bass to chorus bass). | [stubs: playlist performance](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/playlist/performance/); [forum 2026.1.6](https://forum.image-line.com/viewtopic.php?t=342331) |
| **FL Studio Remote** (2025.1+) | A phone or tablet controller over Wi-Fi (UDP **9050/9100**). It has **script pads** that run `.pyscript` from `Settings\FL Studio Remote Scripts`, where "all main FL API modules are preloaded" (Remote 2.1 / FL 2025.2+). Remote scripting can **send virtual MIDI messages** (#20945). | A no-loopback path in theory, but the protocol is **undocumented** and I found no public client. Useful for Daniel today: a pad could run "reroll drums" or "next section". | [IL: FL Studio Remote](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/fl_studio_remote.htm); [IL: Remote Scripting](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/fl_studio_remote_scripting_api.htm); local WhatsNew |
| Dynamic mixer (500 tracks), per-clip stretch and pitch (2025); FLEX rebuild, Transmitter, Remix-a-Song stems, FL Cloud backup (2026) | General production features. | Stem separation could pull a bass or drum reference from a song he wants to jam over. | [IL 2025](https://www.image-line.com/fl-studio-news/fl-studio-2025-whats-new-2); [IL 2026](https://www.image-line.com/fl-studio/release/2026) |

---

## 7. Community bridges, compared

| Project | Transport into FL | Notes into piano roll | Status / date | Source |
|---|---|---|---|---|
| **Flapi** (MaddyGuthridge) | 2 loopMIDI ports ("Flapi Request/Response"). Patched API stubs forward calls as SysEx to a server script inside FL. | No | **Unmaintained**, stuck halfway through a refactor. Hit the Windows SysEx length limit and FL API crashes. | [GitHub](https://github.com/MaddyGuthridge/Flapi); [Unmaintained.md](https://github.com/MaddyGuthridge/Flapi/blob/main/Unmaintained.md); [IL forum intro](https://forum.image-line.com/viewtopic.php?t=322286) |
| **fruityloops-mcp** (quinnjr) | Flapi plus a third loopMIDI port for notes and CC | Live notes only | Has CI; FL 20.7+ | [GitHub](https://github.com/quinnjr/fruityloops-mcp) |
| **MadBlast0/Fl-Studio-MCP** ("fl-bridge-mcp") | JSON file plus MIDI note 127 wake; device script handles `ping`/`exec` | Queued; applied by a **manually run** "FL Bridge Notes" pyscript | Tested on FL 2026; commits 2026-09-07..09 | [GitHub](https://github.com/MadBlast0/Fl-Studio-MCP) |
| **giang17/fl-studio-mcp** | MIDI trigger plus JSON files in Settings; `device_FLStudioMCP.py` | JSON plus **Ctrl+Alt+Y** keystroke after focusing FL | FL 20.7+ | [GitHub](https://github.com/giang17/fl-studio-mcp) |
| **karl-andres/fl-studio-mcp** | Similar (ComposeWithLLM.pyscript) | Keystroke | n/a | [GitHub](https://github.com/karl-andres/fl-studio-mcp); [Glama](https://glama.ai/mcp/servers/karl-andres/fl-studio-mcp) |
| **rosasynthesiz/flstudio-mcp** | A daemon owns ports "FLStudioMCP RX/TX"; thin script in FL | `MCP_Apply` pyscript, re-run with a shortcut after forcing focus | FL 2025+; Windows and macOS | [GitHub](https://github.com/rosasynthesiz/flstudio-mcp) |
| **Boyan253/fl-studio-2025-ai-bridge** | Two JSON files plus MIDI-note wake of `OnMidiIn` (because `OnIdle` never fires on 25.2.5, per the author) | n/a | Verified on 25.2.5 only | [GitHub](https://github.com/Boyan253/fl-studio-2025-ai-bridge) |

Pattern across all of them: **a loopback port, a small device script, the real logic outside FL, and piano roll writes by keystroke or by hand.** None of them claims tight real-time timing. MadBlast0 even notes that FL applies changes "a moment later".

---

## 8. Design options for the jam bridge [inference, grounded in sections 2-7]

**A. Live MIDI performer (fastest to try, least FL-specific)**
- Claude's sequencer (in `arsenal`) sends bass, drum and chord notes to loopback port(s).
- In FL, set the Kontakt instance's wrapper **MIDI input port** to that port. Use an FPC or drum channel through Omni-preview mapping, or through a second port.
- For timing, make **FL the clock master**: Send master sync on a loopback output, and Claude's sequencer follows MIDI clock and song position. Or make Claude the master and set FL to External clock sync, which comes with IL's warning about tempo-dependent effects.
- Risk: Windows timer jitter on every note. That is audible for tight drums, and less so for pads and chords.
- No device script needed. The piano page can see the same port if Chrome enumerates it.

**B. FL-native conductor (best timing)**
- A `device_JamBridge.py` on its own loopback port. Claude sends compact commands as CC/NRPN or short SysEx: tempo, start and stop, `jumpToPattern`, `triggerLiveClip` with bar snap, `setGridBit` and `setStepParameterByIndex` to rewrite the drum grid or a step-mode bass line **for the next loop**, swing, Loop Starter reroll.
- FL plays everything from its own sequencer, sample-accurately, through his Kontakt and Splice samples.
- The script reports back over MIDI out: bar and beat from `OnUpdateBeatIndicator`, the current pattern, tempo. That feeds Claude's decisions and the piano page's cue channel.
- Limits: the step sequencer is one pitch per step per channel, so chords need either one channel per voice or **pre-built patterns** chosen by clip launch.

**C. Pre-take composition with piano roll scripts**
- Between takes, Claude writes JSON (progression, bass, drums), and Daniel presses one hotkey in the piano roll to apply a `JamApply.pyscript`, which writes the notes into the selected pattern.
- No focus stealing, because Daniel presses the key himself. Full polyphony, velocities, slides.
- Pair it with B's clip launching to switch sections live.

**Recommended path:** **B + C for structure, A only for optional expressive lines.**
- Step 0: Daniel approves a loopback (loopMIDI, or a MIDI Services loopback once someone confirms WinMM visibility).
- Step 1: run the section-4 sandbox drill on FL 26.1.3, ideally after upgrading to 2026.1.6 with his OK.
- Step 2: a minimal conductor that handles tempo, play, `jumpToPattern` and `setGridBit`, with bar-tick feedback.

---

## 9. Open questions
1. Does FL 26.1.3 / 2026.1.6 block `socket`, `threading` and `os` in device scripts, and does `OnIdle` fire? The only 2025 evidence is Boyan253's claim for 25.2.5. The drill in section 4 answers this.
2. Are Windows MIDI Services **user** loopbacks (BLOOP) visible to WinMM (FL) and to Chrome Web MIDI on build 26200? If yes, loopMIDI isn't needed, though it still needs Daniel's OK for the tools download and creating the port.
3. What is the exact name and signature of the new set-tempo function (WhatsNew #21346) and the clear-pattern function (#22323)? The stubs site may lag. Check `Shared\Python\Lib\midi.py` or the updated stubs.
4. Are `channels.rerollLoopStarterLoop/Steps` callable from **device** scripts, or only from the FL Studio Remote runtime?
5. Does FL record `channels.midiNoteOn` notes into the pattern while recording? If so, B could capture Claude's live lines as editable notes.
6. How much jitter does a loopback add from an external Python sequencer to FL at the Focusrite ASIO buffer shown in the registry? That buffer value (4096) looks like the DirectSound field, so check the real ASIO buffer in FL. Needs a measured drill.
7. Is the FL Studio Remote UDP protocol (9050/9100) stable or documented anywhere? It would be a no-loopback route, but I found no public client.

---

## Sources (all fetched or read 2026-09-14)
Official (Image-Line, IL-maintained stubs, Microsoft):
- IL manual, MIDI Scripting: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/midi_scripting.htm
- IL manual, MIDI Settings: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_midi.htm
- IL manual, Piano roll Scripting API: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_scripting_api.htm
- IL manual, Plugin Wrapper: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/wrapper.htm
- IL manual, MIDI Out: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/MIDI%20Out.htm
- IL manual, FL Studio Remote: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/fl_studio_remote.htm
- IL manual, FL Studio Remote Scripting: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/fl_studio_remote_scripting_api.htm
- FL Studio API stubs (IL-group): index https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/ · callbacks https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/callbacks/ · transport https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/transport/ · channels/notes https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/notes/ · channels/sequencer https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/sequencer/ · device https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/device/device/ · patterns/properties https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/patterns/properties/ · mixer/properties https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/mixer/properties/ · playlist/performance https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/playlist/performance/ · REC global properties https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/midi/__rec_events/global%20properties/ · getting started https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/tutorials/getting_started/ · flpianoroll https://il-group.github.io/FL-Studio-API-Stubs/piano_roll_scripting/flpianoroll/
- IL, What's new in FL Studio 2026: https://www.image-line.com/fl-studio/release/2026
- IL, FL Studio 2025 released (2025-07-10): https://www.image-line.com/fl-studio-news/fl-studio-2025-whats-new-2
- IL, FL Studio 21.1 what's new: https://www.image-line.com/fl-studio-news/fl-studio-211-whats-new
- IL forum, 2026.1.6 release (2026-09-07): https://forum.image-line.com/viewtopic.php?t=342331
- IL forum, Ableton Link threads: https://forum.image-line.com/viewtopic.php?t=308744 · https://forum.image-line.com/viewtopic.php?t=157443
- IL forum, MIDI clock sync in 21.1: https://forum.image-line.com/viewtopic.php?t=310469
- IL forum, MIDI input port for FL plugins: https://forum.image-line.com/viewtopic.php?t=296151
- Microsoft, Windows MIDI Services overview: https://microsoft.github.io/MIDI/overview/
- Microsoft, Windows Experience Blog 2026-02-17: https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/

Community:
- flmidi-101 guide: https://flmidi-101.readthedocs.io/en/latest/scripting/fl_midi_api.html
- Flapi: https://github.com/MaddyGuthridge/Flapi · https://github.com/MaddyGuthridge/Flapi/blob/main/Unmaintained.md · https://forum.image-line.com/viewtopic.php?t=322286
- fruityloops-mcp: https://github.com/quinnjr/fruityloops-mcp
- MadBlast0/Fl-Studio-MCP: https://github.com/MadBlast0/Fl-Studio-MCP
- giang17/fl-studio-mcp: https://github.com/giang17/fl-studio-mcp
- karl-andres/fl-studio-mcp: https://github.com/karl-andres/fl-studio-mcp · https://glama.ai/mcp/servers/@karl-andres/fl-studio-mcp/blob/b2798b311ae4b02785bc8f4c2ab040f674a06584/scripts/ComposeWithLLM.pyscript
- rosasynthesiz/flstudio-mcp: https://github.com/rosasynthesiz/flstudio-mcp
- Boyan253/fl-studio-2025-ai-bridge: https://github.com/Boyan253/fl-studio-2025-ai-bridge · https://glama.ai/mcp/servers/Boyan253/fl-studio-2025-ai-bridge
- gopie, Windows MIDI Services real-world testing (Aug 2026): https://note.com/gopie/n/n0403fc1003a9?hl=en
- MusicTech FL 2026: https://musictech.com/news/gear/fl-studio-2026-everything-you-need-to-know/ · Gearnews FL 2026: https://www.gearnews.com/fl-studio-daw-software/ · AlternativeTo FL 2025.2: https://alternativeto.net/news/2025/11/fl-studio-2025-2-adds-fruity-slicer-2-emphasizer-new-genres-and-smarter-tools/

Local (read-only): `C:\Program Files\Image-Line\FL Studio 2026\WhatsNew.rtf`; `...\FL Studio 2026\Shared\Python\` (python312._pth, python312.zip listing, Lib\midi.py); `...\System\Config\FL Studio Remote Scripts\*.pyscript`; `...\System\Config\Piano roll scripts\`; `C:\Users\L5\Documents\Image-Line\FL Studio\Settings\Hardware\`; registry `HKCU\Software\Image-Line\FL Studio 26\Devices`, `HKCU\Software\Image-Line\Shared\Paths`, `HKLM\SOFTWARE\Microsoft\Windows MIDI Services\Transport Plugins`, `HKLM\...\Drivers32`; service `midisrv`; installed-programs list.
