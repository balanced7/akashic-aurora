# FL jam bridge: adversarial fact-check

- **Status:** in-flight research, not ratified. This file checks the claims in [fl-jam-bridge-plan.md](fl-jam-bridge-plan.md) and the four lane docs plus [local-inventory.md](local-inventory.md). It patches nothing else.
- **Date:** 2026-09-14 (same night as the plan)
- **Method:**
  - For every load-bearing claim, I tried to refute it from a primary source: the Image-Line manual and IL-maintained API stubs, Microsoft's Windows MIDI Services KB, blog and GitHub, Chromium source, Splice's terms and help center, JUCE, Steinberg and Microsoft Learn.
  - Inventory claims were re-read on this machine, read-only. That meant the registry, file versions, folder listings, `Get-Service`, `py -c "importlib.util.find_spec(...)"`, and the text of FL's own `WhatsNew.rtf` and factory VFX Script presets.
  - Nothing was installed, downloaded, launched or changed, and no GUI app was opened.
- **Verdicts:** **CONFIRMED** = a primary source or local read agrees. **CORRECTED** = the claim is wrong, stale or materially incomplete, and the fix is given. **UNVERIFIED** = no primary source settles it, so it needs a drill or a question to Daniel.
- **Currency:** each source line says when the source was dated or fetched. All fetches were on 2026-09-14.

---

## 0. Corrections that change the recommendation (read these first)

### C1. FL already contains a zero-install, playhead-locked Python note generator: VFX Script. Nothing in the plan or lanes mentions it. [CORRECTED: omission]

- **What the plan says:** a "plugin inside FL" that places notes on FL's playhead needs plugdata (~257 MB) or a JUCE build (multi-GB toolchain). Plan §3 Option D and plugin-path §0 also say "FL has no MIDI-effect slot, so the plugin loads as an instrument".
- **What is true on this machine:**
  - FL 2026 26.1.3 ships **VFX Script**, a Patcher module that runs Python to transform or generate note and automation data. Local evidence: `Plugins\Fruity\Effects\VFX Script\VFX Script_x64.dll`; FL's plugin database files it only under `Effects\Patcher` and `Generators\Patcher`.
  - Image-Line's manual gives it `onTick()` (every clock tick), `onTriggerVoice` / `onReleaseVoice`, and `vfx.context.ticks`, `PPQ` and `isPlaying`. Scripts can create `vfx.Voice()` objects and call `trigger()` / `release()`. Its output feeds the plugins it is wired to inside Patcher ([IL manual: VFX Script](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/VFX%20Script.htm); [beta manual](https://www.image-line.com/fl-studio-learning/fl-studio-beta-online-manual/html/plugins/VFX%20Script.htm); undated live manual, fetched 2026-09-14).
  - The factory presets prove autonomous, transport-locked generation [local, read from `Data\Patches\Plugin presets\Effects\VFX Script\*.fst`]:
    - **"Random Sequencer"** builds new `vfx.Voice()` notes inside `onTick` while `vfx.context.isPlaying`, stepping on `PPQ/4` multiples, with no input notes needed.
    - "Arpeggiator" syncs to `vfx.context.ticks`.
    - "Phase Modulator LFO" reads **`vfx.context.tempo`**. The manual page doesn't list tempo, but the factory script uses it.
  - The local changelog adds more [local `WhatsNew.rtf`]:
    - **#21719, 26.1 Beta 2 (2026-04-09):** VFX Script can import Python files from `[User Data Folder] > VFX Script > Python`.
    - **#21567:** checkbox parameter automation, so the script's controls are automatable.
    - **#19518:** external code editor support.
    - **#21906, 26.1 Beta 8:** the freeze when VFX Script and piano roll scripts run together was fixed.
    - FL 2026's Gopher can also generate VFX scripts on demand ([IL: What's new in 2026](https://www.image-line.com/fl-studio/release/2026)).
- **Why it matters:**
  - A "Claude Band" VFX Script can hold several whole patterns (bass, drums, comp), all baked in or imported from the user folder. It plays them on FL's own tick clock into Kontakt, Addictive Drums 2 or Serum hosted in the same Patcher.
  - Its controls ("variation", "section", "fill", "mute drums") can switch patterns on the next bar. Those controls can be automated, linked to KeyLab knobs or pads through FL's normal controller linking, or set from a device script.
  - That delivers most of Option D (in-FL, locked to the playhead, mid-take changes on the next bar) and most of Option C, **with zero downloads, no compiler and no loopback**.
- **Recommendation impact:**
  - Insert **VFX Script as the first upgrade after the Option A MVP**, before plugdata or JUCE. Defer D6 and D7 further.
  - Add drills:
    - **VX1:** does a module in the VFX Script Python folder re-import without recompiling the script?
    - **VX2:** does `open()` of a JSON file work from `onTick`? Treat it as "no" until probed, like the device-script sandbox.
    - **VX3:** timing. Notes land on project ticks, so set project PPQ high (e.g. 960) if the laid-back snare or swing needs sub-tick resolution [inference].
    - **VX4:** can a KeyLab-port CC be linked to a VFX Script control while the Arturia script owns that port?
- **Unverified details:**
  - The exact on-disk folder for `[User Data Folder] > VFX Script > Python` is unknown. `Documents\Image-Line` has per-plugin folders such as `VFX Keyboard Splitter`, but no `VFX Script` folder yet [local]. Check Options > File settings before writing there, and ask Daniel first (the same D1 class of change).
  - What VFX Script can't do without a loopback: send bar or beat information to the piano page. Page sync for this path stays as weak as Option A's (see C3).

### C2. Decision D2, "install SDK Runtime and Tools 1.0.14-rc.1.209 now", is stale. The tooling changes hands in about 10 weeks. [CORRECTED]

- **What the plan says:** the headline morning decision is to install Microsoft's Windows MIDI Services SDK Runtime and Tools (1.0.14-rc.1.209, from the get-latest page) and create two permanent loopbacks. Recommended default: yes.
- **What the primary sources say on 2026-09-14:**
  - **The get-latest page still shows 1.0.14-rc.1.209** ([get-latest](https://microsoft.github.io/MIDI/get-latest/)).
    - Microsoft's GitHub releases list a newer out-of-band **"App SDK Runtime and Tools Release Candidate 4" (2026-04-12)**.
    - Its notes describe an **unsigned installer** that needs manual approval, with the MIDI Settings app at **preview quality**. They warn that antivirus can interfere; this machine runs no AV by posture.
    - Everything since then consists of **"In-box Dev (and Advanced Customers) Previews"**: Preview 6 (2026-08-31, new C++ MIDI Settings), Preview 7 (2026-09-07) and Preview 8 (**2026-09-14**). These are marked not for end users and need Developer Mode ([GitHub releases](https://github.com/microsoft/MIDI/releases); fetched 2026-09-14).
  - **Microsoft's Pete Brown, in the RtMidi PR thread (Sept 2026):** the out-of-band SDK "will no longer be available come November". The API moves in-box to Windows 11 25H2 ([rtmidi PR #382](https://github.com/thestk/rtmidi/pull/382)).
  - **Microsoft's MIDI Settings page:** the app "will be released to consumers in November 2026". Loopbacks are made by a separate **Loopback Setup** tool launched from MIDI Settings, not by MIDI Settings itself ([MIDI Settings](https://microsoft.github.io/MIDI/tools/settings/); undated live page). The releases page gives the in-box target as the last week of November 2026.
  - **This machine** already has the newer in-box service transports, **1.0.15.0** (dated 2026-08-12) [local]. No source says the RC tools are compatible with that newer in-box service. **UNVERIFIED.**
  - **User-created loopbacks visible to WinMM apps (FL) and Chrome** is still only documented, never field-confirmed:
    - Microsoft documents it ([KB: create loopbacks](https://microsoft.github.io/MIDI/kb/how-to-create-loopback-endpoints-using-tools/); [Windows Experience Blog, 2026-02-17](https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/)).
    - The only independent test found (2026-08-05, build 26200.8875) could not confirm it and concluded loopMIDI is still the practical tool ([gopie on note.com](https://note.com/gopie/n/n0403fc1003a9?hl=en)).
    - Every FL bridge updated in Sept 2026 still names loopMIDI (e.g. [MadBlast0](https://github.com/MadBlast0/Fl-Studio-MCP)).
- **Recommendation impact:**
  - D2 should not be "yes, tonight's headline". It is a three-way choice:
    - **(a)** the RC4 out-of-band tools now: unsigned, preview-quality, may be superseded or unavailable in November, compatibility with the 1.0.15 service unknown;
    - **(b)** wait for the in-box MIDI Settings and Loopback Setup, about the last week of November 2026;
    - **(c)** loopMIDI now: fixed for the new service since April 2026, but a third-party driver whose ports vanish when the app closes.
  - Because C1 covers mid-take changes without any port, the **v1 loopback path loses its urgency**. The default becomes: build A plus VFX Script now, and revisit D2 when the in-box tools ship.
  - If Daniel wants B or C before then, loopMIDI (c) is the better-trodden path. It is what every existing FL bridge uses.

### C3. The KeyLab Play button is a play/pause toggle, not "bar 1 starts now". [CORRECTED]

- **What the plan says** (Option A, §6 sync table, MVP step 2): the page anchors bar 1 of the strip on the release of CC 21 on the DAW port.
- **What is true:**
  - Arturia's script maps CC 21 (release only) to `self.Start`. `Start` calls `transport.start()` [local `KL3Process.py` lines 291, 633-634].
  - IL's stubs define `transport.start()` as start **or pause** ([stubs: transport](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/transport/); live stubs).
  - So a second press **pauses**, and a third **resumes mid-bar**.
  - Stop is CC 20 and acts on **press**, not release (lines 637-639). The command CCs only dispatch on MIDI channel 1 (status 176, line 282).
  - Starting after the playhead was moved also does not begin at bar 1.
- **Recommendation impact:**
  - The page must model a toggle: CC 21 while "playing" means pause.
  - Treat an anchor as trustworthy only after a Stop (CC 20 press) followed by Play.
  - Keep the tap-downbeat fallback as a first-class control, not an optional extra.
  - Drill A1 should include pause and resume and a moved playhead.

---

## 1. Local inventory claims (re-read on this machine)

| Claim (where) | Verdict | Evidence |
|---|---|---|
| FL Studio 2026 **26.1.3.5570** active; FL 2025 25.2.5 also installed (plan §1, inventory) | CONFIRMED | `FL64.exe` FileVersion 26.1.3.5570, dated 2026-07-24; uninstall entries FL Studio 2025 25.2.5.5319 / FL Studio 2026 26.1.3.5570 |
| Latest public build 2026.1.6 (2026-09-07) | CONFIRMED | [IL forum t=342331](https://forum.image-line.com/viewtopic.php?t=342331), release post 2026-09-07 |
| FL ships Python 3.12.1 | CONFIRMED | `Shared\Python\python312.dll` FileVersion 3.12.1; `Shared\Python\Lib` holds only `midi.py` and `utils.py` |
| User script folders empty; no custom script | CONFIRMED | `Settings\Piano roll scripts`, `FL Studio Remote Scripts`, `Audio scripts` present; no bridge folder under `Settings\Hardware` |
| KeyLab 88 mk3 MIDI = port 0 with "KeyLab mk3 Arturia dev"; DAW = port 236 with "KeyLab mk3" | CONFIRMED | `HKCU\SOFTWARE\Image-Line\FL Studio 26\Devices\MIDI input`. **Side note:** the absent "FLkey MIDI" is *also* on port 236 with its own script. If the FLkey is ever reconnected, the two collide [local] |
| Play = CC 21 (on release), Stop = CC 20, Record = CC 22, Tap = CC 23, Loop = CC 24; pads = status 153 | CONFIRMED with nuance | `KL3Process.py` 280-313, 350-355. Record and Loop act on release; Stop and Tap act on press. Pads also use note-off status 137. Pad notes 0-11 go to a sequencer handler instead of the drum handler. **Play toggles pause (C3)** |
| `midisrv` running; loopback and virtual transports enabled; SDK Runtime and Tools not installed; no user loopbacks; loopMIDI absent | CONFIRMED | `midisrv` Running/Manual; `C:\Program Files\Windows MIDI Services` absent; `C:\ProgramData\Microsoft\MIDI` has 0 items; `Midi2.*.dll` all 1.0.15.0 (2026-08-12); no Tobias Erichsen folders or uninstall entries; no MIDI Appx package |
| "FL's stored ASIO buffer is 256 samples = 5.3 ms at 48 kHz" (plan §1) | **CORRECTED** | `HKCU\SOFTWARE\Image-Line\ASIO\bufferSize=256` is the **FL Studio ASIO** driver's own setting. FL's audio output is "Focusrite USB ASIO", 48000 Hz, with a DirectSound field of 4096. For third-party ASIO drivers, the buffer is set in that driver's panel, opened from FL's "Show ASIO panel" ([IL manual: Audio settings](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_audio.htm)). No Focusrite buffer value is readable from the registry. **The real buffer is UNVERIFIED.** Plan open question 4 half-flags this; §1 and §3B state 5.3 ms as fact |
| No MSVC, CMake, Rust; Python 3.11.9 without mido or python-rtmidi | CONFIRMED | `Get-Command cl,cmake,cargo,rustc,ninja,msbuild,vswhere` returned nothing; 3.11 `find_spec`: mido, rtmidi and aalink all False |
| Chrome 152.0.7977.83; Windows 11 25H2 26200.9168 | CONFIRMED | `HKCU\Software\Google\Chrome\BLBeacon`; `CurrentVersion` DisplayVersion/Build/UBR |
| Splice app 5.4.12, Bridge 5.1.1, INSTRUMENT 1.1.15; Kontakt 8.12.1; AD2 2.3.5.4; Serum 2 2.1.4 | CONFIRMED | Appx `Splice 5.4.12.0`; uninstall entries |
| "81 licensed WAVs" in `Documents\Splice\Samples\packs` | CONFIRMED | 81 WAVs, 106 MB, 0 MIDI |
| Pack count "40+" (inventory) / "67 pack folders" (splice lane) | **CORRECTED** | **65** top-level pack folders. The `packs` folder last changed 2026-09-03 (newest WAV). The `Samples` folder itself last changed 2025-11-03, which is what the splice lane reported as "last write" |
| No CLAP folder or plugins | CONFIRMED (inventory read, not re-read) | Consistent with the lane census |
| VFX Script present | **NEW** | See C1 |

## 2. FL Studio scripting claims

| Claim | Verdict | Evidence and currency |
|---|---|---|
| Device scripts can start/stop the transport, switch/clone/clear patterns, edit the step grid including per-step pitch, launch Performance-mode clips quantised, and send MIDI/SysEx | CONFIRMED | Stubs for [transport](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/transport/), [sequencer](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/sequencer/) and [performance](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/playlist/performance/) (live, fetched 2026-09-14). Step parameters: pitch, velocity, release, fine pitch, pan, Mod X/Y, and **tick offset (0..PPQN/4)**. That last one allows per-step lay-back and swing, which the plan doesn't mention. `triggerLiveClip(index, subNum, flags, velocity)`; trigger and position snap: none, 1/4, 1/2, 1, 2, 4 beats, auto |
| "start" semantics | **CORRECTED** | `transport.start()` toggles play/pause (stubs, above). It matters for C3 and for any `start` verb in Option C: send `start` only when stopped |
| Tempo can be set from a script (new function in 25.2.4) | CONFIRMED (function name UNVERIFIED) | WhatsNew #21346 "added a function to set tempo" sits under **25.2.4 RC 1 (2026-01-26)**; #21390 float tempo via `mixer.SetCurrentTempo`. The stubs' transport page still lists no tempo setter, only `setPlaybackSpeed` |
| `setPatternLength` in 26.1 Beta 1; clear-pattern in 26.1.3 RC1; swing get/set in 26.1 Beta 6 | CONFIRMED | WhatsNew #21585 [26.1 Beta 1, 2026-03-24], #22323 [26.1.3 RC1, 2026-07-23], #21791 [26.1 Beta 6, 2026-05-05]. The 2026.1.6 forum post lists setPatternLength and swing too, which suggests its notes are cumulative |
| Device scripts **cannot write piano-roll notes**; `channels.midiNoteOn` plays but doesn't store | CONFIRMED | [Stubs: channels/notes](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/notes/): it creates extra notes live; no pattern-note writer exists in the controller API |
| Piano roll scripts write notes but can't be triggered remotely | CONFIRMED (negative) | [IL manual: Piano roll scripting](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_scripting_api.htm) lists user, downloaded and system folders and the Scripts menu. No remote run and no file I/O are documented. `Documents\Image-Line\FL Studio\Settings\Piano roll scripts` confirmed |
| "Ctrl+Alt+Y to repeat" the last piano roll script (plan Option A diagram) | **UNVERIFIED** | Not in [IL's piano roll page](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll.htm) or the scripting page. Only the community bridges use it ([karl-andres ComposeWithLLM.pyscript](https://glama.ai/mcp/servers/@karl-andres/fl-studio-mcp/blob/b2798b311ae4b02785bc8f4c2ab040f674a06584/scripts/ComposeWithLLM.pyscript); [giang17](https://github.com/giang17/fl-studio-mcp)). Fold it into drill A2 |
| `OnIdle` ~every 20 ms; `OnUpdateBeatIndicator` 0/1/2; `event.handled` stops FL's processing | CONFIRMED with nuance | [Stubs: callbacks](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/callbacks/). The value 0 means off **or half-beat**, so a beacon must not treat 0 as "stopped". The docs say nothing about threads, sockets or file I/O |
| Sandbox: Boyan253 says threads, sockets and most `os` calls are blocked and `OnIdle` never fires on 25.2.5; 2026 bridges still do JSON file I/O | CONFIRMED as reported claims; sandbox on 26.1.3 still UNVERIFIED | [Boyan253 README](https://github.com/Boyan253/fl-studio-2025-ai-bridge) ("verified end-to-end" on 25.2.5; JSON files plus a MIDI-note wake over loopMIDI). [MadBlast0 README](https://github.com/MadBlast0/Fl-Studio-MCP) (developed on FL 2026; JSON file plus MIDI note 127; WinMM to **loopMIDI**; piano roll notes applied by manually running a script). The community guide says FL's Python avoids anything that could alter the PC ([flmidi-101](https://flmidi-101.readthedocs.io/en/latest/scripting/fl_midi_api.html), older). Drill C1 stands |
| "FL scripting freezes were fixed only in 26.1.3 RC1, so update to 2026.1.6 first" (plan Option C risks, D5) | **CORRECTED** | #22368 "Freezes when MIDI scripts call functions" sits under **26.1.3 (2026-07-24)**, the final build Daniel **already runs** [local WhatsNew]. The fix is already installed. The case for D5 rests only on 2026.1.6's claim of "much less jitter" when recording incoming MIDI ([forum t=342331](https://forum.image-line.com/viewtopic.php?t=342331)). That helps recording, and says nothing about live loopback playback |
| Windows MIDI silently drops over-long SysEx (Flapi) | CONFIRMED as a reported claim | [Flapi Unmaintained.md](https://github.com/MaddyGuthridge/Flapi/blob/main/Unmaintained.md) (community; not re-tested) |

## 3. FL routing, sync and plugin-format claims

| Claim | Verdict | Evidence and currency |
|---|---|---|
| FL has MIDI clock out ("Send master sync", MIDI clock normally used) and clock in since 21.1 | CONFIRMED | [IL manual: MIDI settings](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_midi.htm) (live); [IL 21.1 news](https://www.image-line.com/fl-studio-news/fl-studio-211-whats-new) (2023-08-10: new "External sync" mode). Whether FL sends Song Position Pointer is still UNVERIFIED |
| **No Ableton Link** | CONFIRMED | [IL forum t=308744](https://forum.image-line.com/viewtopic.php?t=308744): site admin "No news" (2025-08-22); requests continue to 2026-05-31. Link isn't on the MIDI settings page or the FL 2026 page, and isn't in the 2026.1.6 notes |
| Performance mode was broken with external MIDI sync until 26.1.3 RC1 | CONFIRMED | WhatsNew #22357 [26.1.3 RC1] |
| A VST wrapper's MIDI **input port** matched to a controller's port feeds that plugin "regardless of which channel is selected" | UNVERIFIED as worded | The [IL wrapper page](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/wrapper.htm) only says matched port numbers share "exclusive MIDI data". It doesn't state the selected-channel behaviour either way. The practical routing matches community reports |
| Double-trigger risk (a generic input also sounds the selected channel or other plugins) | CONFIRMED as a real risk (old evidence) | [IL forum t=220559](https://forum.image-line.com/viewtopic.php?f=100&t=220559) (2020): matched-port plugins played from both keyboards; the fix was MIDI filters in Patcher or a filter plugin. Keep drill B3. Binding the loopback to a device script with `event.handled = True` remains the right mitigation [inference] |
| FL supports VST 1/2, VST3 and CLAP on Windows | CONFIRMED | [IL manual: plugin standards](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins_supported.htm) |
| VST3 plugin-to-plugin MIDI fixed in 24.2.99 Beta 1; CLAP note output fixed in Beta 8; CLAP tempo/position fixed in 24.2.1 | CONFIRMED | WhatsNew #19370 [24.2.99 Beta 1, 2025-03-11], #20064 [24.2.99 Beta 8, 2025-06-19], #17397 [24.2.1, 2024-12-10], #17071 CLAP preliminary [21.2.99 Beta 2, 2024-03-12] |
| "FL has no MIDI-effect slot, so the plugin loads as an instrument" | **CORRECTED (incomplete)** | True for VST3 MIDI-effect plugins as a stand-alone insert ([JUCE forum 2025](https://forum.juce.com/t/midi-generator-plugin-im-distributing-a-vst3i-could-i-distribute-a-vst3-midi-effect-too-for-ableton-cubase-fl-studio/65814)). But FL's own **VFX note-effect family runs inside Patcher**: VFX Script, VFX Sequencer, Key Mapper and others [local]. See C1 |
| Import MIDI: dropping on the Channel Rack creates new FLEX/MIDI Out channels; Shift skips the dialog | PARTLY CORRECTED | [IL manual: Import MIDI data](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/automation_midiimport.htm): Shift suppresses the dialog (Alt forces it), **CONFIRMED**. The page says the dialog's options depend on how the file is loaded, and "Create one channel per track" appears only for the File menu or a desktop/Playlist drop. It does **not** say a Channel Rack drop creates new channels. [Piano roll MIDI import](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_midi.htm) **overwrites** the pattern's notes unless "Blend with existing data" is on. The plan's practical advice (import onto each channel's piano roll) holds; add "leave Blend off to replace" |
| FL 2026 Audio Logger keeps the last 60 s; Gopher generates piano roll and VFX scripts | CONFIRMED | [IL: What's new in 2026](https://www.image-line.com/fl-studio/release/2026) |

## 4. Windows MIDI Services, loopMIDI and Chrome

| Claim | Verdict | Evidence and currency |
|---|---|---|
| Chrome can't see "Service Test Loopback" because it is a diagnostics endpoint for SDK apps only | CONFIRMED | [MS KB: diagnostic endpoints](https://microsoft.github.io/MIDI/kb/diagnostic-endpoints/) (undated): diagnostics endpoints are available only to apps using the new SDK |
| User-created loopbacks work with WinMM, WinRT and web pages; every port is multi-client | CONFIRMED as documentation; UNVERIFIED in the field | [KB: create loopbacks](https://microsoft.github.io/MIDI/kb/how-to-create-loopback-endpoints-using-tools/) names desktop apps, web sites, WinMM and WinRT MIDI 1.0. The [Feb 2026 blog](https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/) says WebMIDI pages can use them and every port is multi-client. The only field test found could not confirm it ([gopie, 2026-08-05](https://note.com/gopie/n/n0403fc1003a9?hl=en)). Drill B1 stands |
| Loopbacks made in MIDI Settings persist; console loopbacks last until service restart | CONFIRMED with nuance | Same KB. Per the [MIDI Settings page](https://microsoft.github.io/MIDI/tools/settings/), the creating tool is **Loopback Setup**, launched from MIDI Settings. Hand-editing the config is unsupported ([KB: virtual loopback](https://microsoft.github.io/MIDI/kb/virtual-loopback/)); unique ids are 32 characters or fewer |
| SDK Runtime and Tools needed to create loopbacks; version 1.0.14-rc.1.209; WinGet `Microsoft.WindowsMIDIServicesSDK` | **CORRECTED** | WinGet id CONFIRMED (Feb 2026 blog). Version and availability are stale; see C2 (RC4 of 2026-04-12, in-box tools about the last week of November 2026, out-of-band SDK going away in November) |
| April 2026 fixes for loopMIDI and other dynamic ports disappearing | CONFIRMED | [MS known issues](https://devblogs.microsoft.com/windows-music-dev/windows-midi-services-rollout-known-issues-and-workarounds/) (updated 2026-04-30; 30-day staged rollout from 2026-04-30); [GitHub #835](https://github.com/microsoft/MIDI/issues/835) (opened 2026-01-30, labelled fixed-windows-release-april2026). This machine's MIDI binaries are dated 2026-08-12 [local], so the fix is very likely present [inference] |
| loopMIDI page lists Windows 7-10 only, v1.0.16.27 | CONFIRMED | [tobias-erichsen.de](https://www.tobias-erichsen.de/software/loopmidi.html) (fetched 2026-09-14; no Windows 11 or MIDI Services mention) |
| Plan D3 "No to loopMIDI" | **CORRECTED (weakened)** | Its reason, "in-box loopbacks survive reboot", assumes the in-box creation tool is ready. Today that tool is either an unsigned RC or a November release (C2). loopMIDI is the path every Sept 2026 FL bridge uses |
| WinMM apps identify ports by name; reuse loopMIDI names | CONFIRMED | [Pete Brown, Steinberg forum](https://forums.steinberg.net/t/loopmidi-loopbe-etc-virtual-ports-replacement-for-windows/1025292/3) (2026-02-28) |
| Chromium on Windows uses WinMM (WinRT behind a flag) | CONFIRMED; default flag state UNVERIFIED | [midi_manager_win.cc](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/media/midi/midi_manager_win.cc) calls `midiInOpen` / `midiOutShortMsg`; `kMidiManagerWinrt` still selects a WinRT manager. Its default wasn't found. Either API goes through `midisrv`, so this doesn't change the plan |
| Microsoft claims low-microsecond service jitter | NOT RE-CHECKED | Vendor claim ([microsoft.github.io/MIDI](https://microsoft.github.io/MIDI/)); the Feb blog says timestamps are accurate to under a microsecond. No loopback measurement exists |

## 5. Timing claims

| Claim | Verdict | Evidence and currency |
|---|---|---|
| Python 3.11 "sleeps with 100 ns resolution" on Windows | **CORRECTED (nuance)** | The [Python 3.11 time docs](https://docs.python.org/3.11/library/time.html) say Windows 8.1+ uses a high-resolution waitable timer with 100 ns *resolution*. That is the timer's unit, not measured wake-up accuracy, and no measurement was found ([CPython #89592](https://github.com/python/cpython/issues/89592) showed no numbers when fetched). The plan's "hi-res sleep plus a short busy-wait" is the right design. Just don't budget jitter from the 100 ns figure |
| Hidden Chrome tabs are throttled to once per second, or once per minute | CONFIRMED | [Chrome for Developers, Chrome 88](https://developer.chrome.com/blog/timer-throttling-in-chrome-88) (2021-01-18). Intensive throttling needs more than 5 min hidden, chained timers and 30 s of silence; audible pages are exempt |
| Perceptible jitter about 1-5 ms | CONFIRMED with caveat | [Expressiveness 2012](https://expressiveness.org/2012/12/04/midi-jitter): listening studies found about 1-5 ms, most sensitive at 2-3 ms. Players may be more sensitive than listeners |
| FL input-to-sound delay is at least the buffer | CONFIRMED | [IL manual: Audio settings](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_audio.htm). The value is Focusrite's buffer, which is unknown (§1) |

## 6. Plugin path claims

| Claim | Verdict | Evidence and currency |
|---|---|---|
| JUCE 9 current; Starter free up to $20k revenue; AGPLv3 dual licence | CONFIRMED | [juce.com/get-juce](https://juce.com/get-juce/) (live): Starter free to $20,000; Indie $40/month to $300,000; Pro $175/month; dual JUCE licence / AGPLv3. [JUCE releases](https://github.com/juce-framework/JUCE/releases): 9.0.2 released Sept 7; 9.0.x notes don't mention native CLAP. Splash-screen terms not checked (irrelevant to a private plugin) |
| VST3 SDK moved to MIT with 3.8.0 (Oct 2025) | CONFIRMED | [Sonicstate 2025-10-30](https://sonicstate.com/news/2025/10/30/vst-3-now-available-under-mit-license/); [KVR](https://www.kvraudio.com/news/steinberg-moves-vst-3-sdk-to-mit-open-source-license-asio-now-gplv3-65179); [Steinberg licensing portal](https://steinbergmedia.github.io/vst3_dev_portal/pages/VST+3+Licensing/Index.html) |
| VST3 `ProcessContext` gives tempo, `projectTimeMusic`, `barPositionMusic`, kPlaying and validity flags | CONFIRMED | [Steinberg ProcessContext](https://steinbergmedia.github.io/vst3_doc/vstinterfaces/structSteinberg_1_1Vst_1_1ProcessContext.html) |
| VS Build Tools 2.3-60 GB, admin to install | CONFIRMED | [Microsoft Learn VS 2026 requirements](https://learn.microsoft.com/en-us/visualstudio/releases/2026/vs-system-requirements) (updated 2026-04-01) |
| plugdata v0.9.3-2 (2026-03-06), Win64 MSI about 257 MB; `[netreceive]` runs only while the DAW sends audio blocks | CONFIRMED | [GitHub API latest release](https://api.github.com/repos/plugdata-team/plugdata/releases/latest): published 2026-03-06, `plugdata-Win64.msi` 269,381,632 bytes. [Discussion #144](https://github.com/plugdata-team/plugdata/discussions/144) (developer, 2022-08-04; old). Now lower priority because of C1 |
| CLAP event times are sample offsets; transport event | NOT RE-CHECKED | [CLAP events.h](https://raw.githubusercontent.com/free-audio/clap/main/include/clap/events.h); no bearing on the recommendation |

## 7. Splice claims

| Claim | Verdict | Evidence and currency |
|---|---|---|
| Terms ban automated access (spiders, robots, scrapers, crawlers) | CONFIRMED | [splice.com/terms](https://splice.com/terms) (last updated **2026-07-24**), section II(8)(j) |
| AI training on Splice content not permitted | CONFIRMED, stronger than stated | [Licensing FAQ](https://support.splice.com/en/articles/8652642-splice-sounds-licensing-faq) (2024-09-06): content may not be used "for the purposes of training/modeling data for AI". The **Terms themselves** (2026-07-24) also forbid using Sounds as source or training material for generative or other AI models (section 3.1.1.3(h)). D9's default ("no" to analysing Splice audio) is well founded |
| No public API | UNVERIFIED (negative finding) | Nothing found; the terms' automation ban makes the point moot |
| Splice Bridge syncs previews to DAW tempo and key; officially tested on FL 20.8+; needs the desktop app | CONFIRMED | [How to use Bridge](https://support.splice.com/en/articles/8652857-how-do-i-use-splice-bridge) and [DAW compatibility](https://support.splice.com/en/articles/8652858-will-my-daw-work-with-splice-bridge) (both 2024-01-24; old but unchanged) |
| Sounds Plugin beta: VST3, no MIDI, not for the INSTRUMENT-only plan | CONFIRMED with small corrections | [Sounds Plugin FAQ](https://support.splice.com/en/articles/12997860-faq-splice-sounds-plugin-now-in-beta) (2026-07-20): "AU and VST3" (the lane also lists AAX from the product page); **Windows 10 or later** (the lane said 22H2+); FL not named specifically |
| No native FL Studio Splice integration | CONFIRMED (negative) | Not in [FL 2026 what's new](https://www.image-line.com/fl-studio/release/2026) or the 2026.1.6 notes; request thread [t=336226](https://forum.image-line.com/viewtopic.php?t=336226) |
| INSTRUMENT is LABS' new home; LABS support ends 2026-10-31; Transistor Bass is All Plugins Edition only; AD2 GM map | NOT RE-CHECKED | Not load-bearing for the bridge design; the lane's sources stand |

---

## 8. What the corrected recommendation looks like (for the plan's author, not applied)

1. **MVP (unchanged, zero installs):** Option A `.mid` / `.pyscript` delivery.
   - Page sync must treat KeyLab Play as a **toggle** (C3).
   - Anchor only after Stop then Play, and keep tap-downbeat as a primary control.
   - Verify Ctrl+Alt+Y as part of A2.
2. **New v1 candidate, still zero downloads: a "Claude Band" VFX Script in Patcher (C1).**
   - Bass, drums and comp patterns baked in or imported.
   - Next-bar pattern switching on FL's tick clock.
   - Variation and section controls automatable or linkable to KeyLab controls.
   - Drills VX1-VX4 first. Its gap is page sync (no beacon without a port).
3. **Loopback path (B + C) moves to "when the in-box tools ship" (about late Nov 2026), or loopMIDI if Daniel wants it sooner (C2).**
   - Keep drills B1-B4 and C1.
   - D2 becomes a three-way choice, not a default yes.
4. **Plugin path:** plugdata and JUCE drop behind VFX Script. Revisit only if VX3 shows tick resolution or `onTick` cost can't meet the timing budget.
5. **D5 (update to 2026.1.6):** optional. The scripting-freeze fix is already in 26.1.3; the update improves MIDI *recording* jitter.
6. **Timing budget:** measure Focusrite's real ASIO buffer before quoting 5.3 ms.

## 9. Sources

Primary, fetched 2026-09-14:

**Image-Line**
- Manual pages:
  - VFX Script: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/VFX%20Script.htm (beta manual: https://www.image-line.com/fl-studio-learning/fl-studio-beta-online-manual/html/plugins/VFX%20Script.htm)
  - MIDI settings: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_midi.htm
  - Audio settings: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_audio.htm
  - Plugin wrapper: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/wrapper.htm
  - Plugin standards: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins_supported.htm
  - Import MIDI data: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/automation_midiimport.htm
  - Piano roll MIDI import: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_midi.htm
  - Piano roll scripting: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_scripting_api.htm
  - Piano roll: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll.htm
- News and release pages:
  - FL 2026: https://www.image-line.com/fl-studio/release/2026
  - FL 21.1: https://www.image-line.com/fl-studio-news/fl-studio-211-whats-new
- Forum threads:
  - 2026.1.6 release: https://forum.image-line.com/viewtopic.php?t=342331
  - Ableton Link requests: https://forum.image-line.com/viewtopic.php?t=308744
  - Double-trigger on matched ports: https://forum.image-line.com/viewtopic.php?f=100&t=220559
  - Splice integration request: https://forum.image-line.com/viewtopic.php?t=336226
- API stubs:
  - Transport: https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/transport/
  - Callbacks: https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/callbacks/
  - Sequencer: https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/sequencer/
  - Performance: https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/playlist/performance/
  - Channels/notes: https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/notes/

**Microsoft**
- Diagnostic endpoints KB: https://microsoft.github.io/MIDI/kb/diagnostic-endpoints/
- Create loopbacks KB: https://microsoft.github.io/MIDI/kb/how-to-create-loopback-endpoints-using-tools/
- Virtual loopback KB: https://microsoft.github.io/MIDI/kb/virtual-loopback/
- Get latest SDK Runtime and Tools: https://microsoft.github.io/MIDI/get-latest/
- MIDI Settings tool: https://microsoft.github.io/MIDI/tools/settings/
- GitHub releases: https://github.com/microsoft/MIDI/releases
- Issue #835: https://github.com/microsoft/MIDI/issues/835
- Known issues post: https://devblogs.microsoft.com/windows-music-dev/windows-midi-services-rollout-known-issues-and-workarounds/
- Windows Experience Blog, 2026-02-17: https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/
- VS 2026 system requirements: https://learn.microsoft.com/en-us/visualstudio/releases/2026/vs-system-requirements
- Pete Brown on port names: https://forums.steinberg.net/t/loopmidi-loopbe-etc-virtual-ports-replacement-for-windows/1025292/3
- Pete Brown on the out-of-band SDK ending: https://github.com/thestk/rtmidi/pull/382

**Chromium**
- Windows MIDI manager source: https://chromium.googlesource.com/chromium/src/+/refs/heads/main/media/midi/midi_manager_win.cc
- Timer throttling in Chrome 88: https://developer.chrome.com/blog/timer-throttling-in-chrome-88

**Python**
- time module (3.11): https://docs.python.org/3.11/library/time.html
- CPython issue #89592: https://github.com/python/cpython/issues/89592

**Plugins**
- JUCE:
  - Get JUCE (licences): https://juce.com/get-juce/
  - Releases: https://github.com/juce-framework/JUCE/releases
- Steinberg VST3:
  - ProcessContext: https://steinbergmedia.github.io/vst3_doc/vstinterfaces/structSteinberg_1_1Vst_1_1ProcessContext.html
  - Licensing: https://steinbergmedia.github.io/vst3_dev_portal/pages/VST+3+Licensing/Index.html
  - MIT change coverage: https://sonicstate.com/news/2025/10/30/vst-3-now-available-under-mit-license/ and https://www.kvraudio.com/news/steinberg-moves-vst-3-sdk-to-mit-open-source-license-asio-now-gplv3-65179
- plugdata:
  - Latest release (GitHub API): https://api.github.com/repos/plugdata-team/plugdata/releases/latest
  - Discussion #144: https://github.com/plugdata-team/plugdata/discussions/144
- JUCE forum, MIDI generator plugins in FL: https://forum.juce.com/t/midi-generator-plugin-im-distributing-a-vst3i-could-i-distribute-a-vst3-midi-effect-too-for-ableton-cubase-fl-studio/65814

**Splice**
- Terms of Use: https://splice.com/terms
- Licensing FAQ: https://support.splice.com/en/articles/8652642-splice-sounds-licensing-faq
- Sounds Plugin FAQ: https://support.splice.com/en/articles/12997860-faq-splice-sounds-plugin-now-in-beta
- How to use Bridge: https://support.splice.com/en/articles/8652857-how-do-i-use-splice-bridge
- Bridge DAW compatibility: https://support.splice.com/en/articles/8652858-will-my-daw-work-with-splice-bridge

**loopMIDI**
- https://www.tobias-erichsen.de/software/loopmidi.html

**Community**
- gopie field test, 2026-08-05: https://note.com/gopie/n/n0403fc1003a9?hl=en
- Boyan253 bridge: https://github.com/Boyan253/fl-studio-2025-ai-bridge
- MadBlast0 bridge: https://github.com/MadBlast0/Fl-Studio-MCP
- giang17 bridge: https://github.com/giang17/fl-studio-mcp
- karl-andres script: https://glama.ai/mcp/servers/@karl-andres/fl-studio-mcp/blob/b2798b311ae4b02785bc8f4c2ab040f674a06584/scripts/ComposeWithLLM.pyscript
- Flapi: https://github.com/MaddyGuthridge/Flapi/blob/main/Unmaintained.md
- flmidi-101 guide: https://flmidi-101.readthedocs.io/en/latest/scripting/fl_midi_api.html
- Expressiveness, MIDI jitter: https://expressiveness.org/2012/12/04/midi-jitter

**Local (read-only, 2026-09-14)**
- FL install: `C:\Program Files\Image-Line\FL Studio 2026\FL64.exe` (version), `WhatsNew.rtf` (IDs mapped to version headers), `Shared\Python\python312.dll`, `Plugins\Fruity\Effects\VFX Script\`, `Data\Patches\Plugin presets\Effects\VFX Script\*.fst` (Random Sequencer, Arpeggiator, Phase Modulator LFO script text), `Data\Patches\Plugin database\{Effects,Generators}\Patcher\VFX Script.fst`
- KeyLab script: `C:\Users\L5\Documents\Image-Line\FL Studio\Settings\Hardware\Arturia KeyLab mk3\KL3Process.py` (lines 267-313, 350-355, 633-646)
- Registry: `HKCU\SOFTWARE\Image-Line\FL Studio 26\Devices`, `HKCU\SOFTWARE\Image-Line\ASIO`, `HKCU\Software\Google\Chrome\BLBeacon`, `HKLM\...\Windows NT\CurrentVersion`, uninstall keys
- Windows MIDI stack: `C:\Windows\System32\Midi2.*.dll`, service `midisrv`, `C:\ProgramData\Microsoft\MIDI`
- Folders: `C:\Users\L5\Documents\Splice\Samples\packs`, `C:\Users\L5\Documents\Image-Line`
- Python: `py -3.11` find_spec for mido, rtmidi and aalink
