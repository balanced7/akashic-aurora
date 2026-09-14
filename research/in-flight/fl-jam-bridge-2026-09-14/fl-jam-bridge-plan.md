# FL jam bridge: the plan

- **Status:** in-flight research synthesis, not ratified. Nothing on this machine was installed, downloaded, launched or changed to write it.
- **Date:** 2026-09-14 (late night, after Daniel went to bed)
- **Built from the lane docs in this folder:** [local-inventory.md](local-inventory.md), [fl-scripting.md](fl-scripting.md), [virtual-midi-and-sync.md](virtual-midi-and-sync.md), [plugin-path.md](plugin-path.md), [splice-and-sounds.md](splice-and-sounds.md). A handful of new checks were added tonight (WinMM through ctypes, FL's MIDI import dialog, the KeyLab mk3 script's transport mapping). They are cited where used.
- **Labels:** **[local]** = read off this machine on 2026-09-14. **[lane]** = sourced in a lane doc, with the URL repeated here for load-bearing claims. **[inference]** = my design reasoning, not a sourced fact.

What Daniel asked for, in his words: *"think of how we can tie this into FL studio either via midi or a vst plugin and this will let us play things, you could change bass progressions and drums and I can improvise over them! you can find cool sounds on splice and we can get them and play with them"*

---

## 0. The answer on one screen

1. **FL plays the sounds, and FL keeps the time.** In every option, the bass, drums and chords come out of FL Studio through Daniel's own instruments: Kontakt, Addictive Drums 2, Serum 2, Arturia and FPC, plus Splice one-shots loaded in FL. Claude never plays audio into the mix. Claude writes **patterns**, and FL plays them. The options differ only in how a pattern reaches FL and how fast a change lands.
2. **Build one core, then swap how patterns reach FL.** A jam engine in arsenal owns three things: one **pattern contract** (roles, beats, notes, launch rule), one **jam clock** (FL's bar and beat, with an epoch that changes whenever the timeline jumps), and the **lead-sheet chart**. That lets us start with zero installs and upgrade without rewriting anything the page, the CLI or the practice log depend on.
3. **The four options:**
   - **A. Hand-delivered patterns.** Zero installs. Claude writes `.mid` files, or a self-contained piano-roll script. Daniel drags them in or presses one key. FL loops them sample-accurately. The page syncs from the KeyLab's own Play button, which both FL and Chrome already hear.
   - **B. Loopback live band.** One Microsoft download. Python sends the patterns live into FL over an in-box Windows MIDI loopback, with FL as the clock master. Changes land on the next bar, mid-take.
   - **C. FL-native conductor.** Same download as B. A `device_ClaudeBridge.py` script inside FL rewrites the step grid, switches patterns, launches clips on the bar and reports bar and tempo back.
   - **D. Plugin.** A plugdata test first (one ~257 MB download), later a custom JUCE plugin (multi-GB toolchain). A plugin inside FL receives whole patterns from arsenal and places each note at the exact sample on FL's playhead. It needs no loopback port at all.
4. **Recommended path:**
   - **MVP tonight-ready:** A. No approvals needed beyond dropping one script file into FL's user folder, which is optional.
   - **v1:** B + C together, on one download and two loopback ports, after five short drills.
   - **v2:** D only if the v1 timing drill misses the budget or we want sample accuracy. Also in v2: a "listening band" that follows what Daniel plays.
5. **Morning decisions (section 10).** The headline one is to install Microsoft's **Windows MIDI Services SDK Runtime and Tools** and create two permanent loopback ports. Recommended default: **yes**. Everything else can wait.

---

## 1. Ground truth the plan stands on

| Fact | Evidence |
|---|---|
| FL Studio 2026 **26.1.3.5570** is active; FL 2025 25.2.5 is also installed. Latest public build is 2026.1.6 (2026-09-07). | [local]; [IL forum 2026.1.6](https://forum.image-line.com/viewtopic.php?t=342331) |
| FL ships its own **Python 3.12.1** for scripts. The user script folders are empty; no custom script exists yet. | [local] |
| KeyLab 88 mk3: the **MIDI port** uses FL port 0 with Arturia's "KeyLab mk3 Arturia dev" script. The **DAW port** uses FL port 236 with "KeyLab mk3". | [local] registry `HKCU\SOFTWARE\Image-Line\FL Studio 26\Devices` |
| On the DAW port, the KeyLab mk3 script maps **Play = CC 21** (acts on release), **Stop = CC 20**, Record = CC 22, Tap tempo = CC 23, Loop = CC 24. Pads arrive as **note-ons on MIDI channel 10** (status 153). | [local] `Settings\Hardware\Arturia KeyLab mk3\KL3Process.py` lines 280-313 and 351 |
| Windows MIDI Service (`midisrv`) is running, with the loopback and virtual transports enabled. The **SDK Runtime and Tools** (MIDI Settings app, where loopbacks are created) are **not installed**. No user loopbacks exist. loopMIDI is absent. | [local]; [Microsoft get-latest](https://microsoft.github.io/MIDI/get-latest/) |
| Chrome can't see "Service Test Loopback" because it is a diagnostics endpoint, available only to SDK apps. **User-created** loopbacks are documented to work with WinMM apps (FL), WinRT apps and web pages, and every port is multi-client. | [Microsoft KB: diagnostic endpoints](https://microsoft.github.io/MIDI/kb/diagnostic-endpoints/); [Microsoft KB: create loopbacks](https://microsoft.github.io/MIDI/kb/how-to-create-loopback-endpoints-using-tools/); [Windows Experience Blog 2026-02-17](https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/) |
| FL device scripts can start and stop the transport, set tempo, switch, clone or clear patterns, edit the step grid (including per-step pitch), launch Performance-mode clips quantised to the beat or bar, and send MIDI or SysEx out. They **cannot write piano-roll notes**. Piano-roll scripts can write notes but can't be triggered remotely. | [IL API stubs](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/); [IL piano roll scripting](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_scripting_api.htm); local WhatsNew |
| The sandbox is unverified. One 2025 bridge reports threads, sockets and `OnIdle` blocked on 25.2.5; 2026 bridges still do JSON file I/O. **Assume MIDI in and out only until a probe runs.** | [Boyan253 bridge](https://github.com/Boyan253/fl-studio-2025-ai-bridge); [MadBlast0 bridge](https://github.com/MadBlast0/Fl-Studio-MCP) |
| FL has MIDI clock out (Send master sync) and clock in (since 21.1). **No Ableton Link.** | [IL MIDI settings](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_midi.htm); [IL forum Link thread](https://forum.image-line.com/viewtopic.php?t=308744) |
| A VST's wrapper **MIDI input port** can be matched to a port, so that plugin (e.g. Kontakt) receives that port's MIDI regardless of which channel is selected. Plugin-to-plugin MIDI routes by matching port numbers (0-255). | [IL plugin wrapper](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/wrapper.htm); [IL MIDI Out](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/MIDI%20Out.htm) |
| Audio: Scarlett 2i2 4th Gen, FL on Focusrite USB ASIO at 48 kHz. FL's stored ASIO buffer is 256 samples, which is 5.3 ms at 48 kHz. FL's own manual says input-to-sound delay is at least the buffer. | [local]; [IL audio settings](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_audio.htm) |
| No compiler toolchain (no MSVC, CMake or Rust). Python 3.11.9 is pinned, **without** mido or python-rtmidi. | [local] |
| Splice app 5.4.12, Splice Bridge 5.1.1 and Splice INSTRUMENT 1.1.15 are installed. There are 81 licensed WAVs in `Documents\Splice\Samples\packs`. No public API; the Terms of Use ban automated access; the licence bans AI training on Splice content. | [local]; [Splice terms](https://splice.com/terms); [Splice licensing FAQ](https://support.splice.com/en/articles/8652642-splice-sounds-licensing-faq) |

**A zero-pip MIDI path exists [inference, sourced parts].** Python's standard-library `ctypes` can call Windows DLLs and create callbacks ([Python docs: ctypes](https://docs.python.org/3.11/library/ctypes.html)). WinMM's `midiOutShortMsg` sends short MIDI messages ([Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/mmeapi/nf-mmeapi-midioutshortmsg)), and `midiInOpen` with `CALLBACK_FUNCTION` receives them ([Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/mmeapi/nf-mmeapi-midiinopen)). So the arsenal engine can talk to a loopback port **without** `pip install python-rtmidi`. The port itself still has to exist.

---

## 2. The shared core (the same in every option)

```
            chat / CLI verbs                 concept cards (jam space)          practice log + riff analysis
                  |                                   |                                   |
                  v                                   v                                   v
   +------------------------------------------------------------------------------------------------+
   |  arsenal jam engine  (new: arsenal/jam.py, routes in serve.py)                                 |
   |    - pattern generator: chart + style -> bass / drums / comp events (beats, notes, velocity)     |
   |    - pattern contract (JSON, idempotent whole patterns, launch = next_bar)                        |
   |    - jam clock: (epoch, bar, beat, bpm, meter, playing) mapped to server time with uncertainty   |
   |    - outputs (pluggable):  mid-export | winmm-port | fl-conductor | plugin-sse | browser-voice   |
   +------------------------------------------------------------------------------------------------+
         |  SSE /api/jam/clock + /api/jam/loop                         | one of the outputs
         v                                                              v
   piano page (127.0.0.1:8793/piano): lead-sheet strip,         FL Studio: Claude Bass / Claude Drums /
   role lanes, upcoming chord, Daniel's keys                     Claude Keys channels -> audio
```

### 2.1 Pattern contract (one JSON shape for every transport)

This extends the sketch in plugin-path.md §3.5 and aligns with `arsenal/pianocue.py`'s cue vocabulary [local].

```json
{
  "type": "loop", "id": "db-neosoul-01", "rev": 3, "source": "claude",
  "key": "Db major", "bpm": 84, "meter": [4, 4], "bars": 4, "swing": 0.56,
  "launch": "next_bar",
  "chart": [ {"beat": 0, "chord": "Ebm9", "nns": "2m"}, {"beat": 4, "chord": "Ab13", "nns": "5"},
             {"beat": 8, "chord": "Dbmaj9", "nns": "1"}, {"beat": 12, "chord": "Bb7(#9,b13)", "nns": "6"} ],
  "roles": {
    "bass":  {"channel": 1,  "events": [ {"beat": 0.0, "note": 39, "vel": 100, "len": 0.75} ]},
    "drums": {"channel": 10, "map": "gm", "events": [ {"beat": 0.0, "note": 36, "vel": 110, "len": 0.1} ]},
    "comp":  {"channel": 2,  "events": [ {"beat": -0.25, "notes": [54, 58, 61, 65], "vel": 70, "len": 1.5} ]}
  },
  "label": "2m - 5 - 1 - 6, lazy pocket"
}
```

Rules [inference]:
- **Notes are integers 0-127.** FL labels MIDI 60 as C5, not C4, so note names are never sent ([IL forum](https://forum.image-line.com/viewtopic.php?t=76662)).
- **Drums use GM roles:** kick 36, snare 38, closed hat 42, open hat 46 ([General MIDI](https://en.wikipedia.org/wiki/General_MIDI)). FPC's *Empty* preset and Addictive Drums 2's GM map both take them unchanged ([IL FPC manual](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/FPC.htm)).
- **Whole patterns, never deltas.** A lost or duplicated send heals on the next one. `rev` increases so a stale loop is ignored.
- **`launch: next_bar` by default.** Daniel never hears half a change.

### 2.2 Jam clock (FL is the master)

- **FL's audio clock leads.** This matches `timebase.py`'s `MASTER_BY_MODE["live_audio"] = "audio"` [local].
- A **`musical` clock** (a domain `timebase.py` already defines) carries `(epoch, bar, beat)`. Its epoch changes on Start, Stop, jump, pattern-loop wrap and tempo change. That is the "epoch changes on seek, loop..." rule from the `timebase.py` docstring [local].
- Each clock source is recorded as a `ClockMap` with its `uncertainty_ns` [local], so the page and the log know how trustworthy the bar numbers are. Details in section 6.

---

## 3. Architecture options

### Option A: Hand-delivered patterns (zero new installs)

```
 CLI / chat: "jam loop Db neo-soul 84"
        |
        v
 arsenal jam engine --writes--> state/arsenal/jam/<id>/bass.mid, drums.mid, comp.mid, chart.json
        |                       (+ optional ClaudeJam.pyscript with the notes baked in)
        |                                   |
        |                                   |  Daniel: drag each .mid onto that channel's Piano roll
        |                                   |  (or Piano roll > Tools > Scripting > ClaudeJam, then Ctrl+Alt+Y to repeat)
        |                                   v
        |                         FL Studio pattern loops Claude Bass / Drums / Keys  -> Kontakt, AD2, Stage-73 -> audio
        |
        | SSE chart + loop                        KeyLab 88 mk3 --DAW port, CC 21 (Play)--> FL starts (Arturia script)
        v                                                      \--(same port, multi-client)--> Chrome Web MIDI
 piano page: lead-sheet strip loops at the file's BPM;          page anchors bar 1 on the same CC 21 release
 Daniel's KeyLab notes drawn live as today
```

**How it works:**
- The engine writes Standard MIDI Files with the standard library: an `MThd` header, one `MTrk` per role, a tempo meta event, and ticks per quarter note ([MIDI Association SMF spec](https://midi.org/standard-midi-files-specification)).
- Dropping a `.mid` into FL opens the Import MIDI data dialog. It works from the File menu, the Piano roll, or by dragging onto the Channel Rack, Piano roll or FL's desktop; holding Shift skips the dialog ([IL manual: Import MIDI data](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/automation_midiimport.htm)).
  - **Drag each role onto its own channel's Piano roll.** Dropping on the Channel Rack creates *new* channels loaded with FLEX or MIDI Out, not Daniel's Kontakt (same page).
  - The Piano roll import is documented at [IL: piano roll MIDI import](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_midi.htm).
- **Optional script variant:**
  - Claude regenerates `ClaudeJam.pyscript` with the pattern baked in as a Python literal. That avoids depending on file I/O inside FL's sandbox.
  - A `ScriptDialog` combo picks the role and variation (A, B, fill) ([IL piano roll scripting](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_scripting_api.htm)).
  - Daniel presses the key himself, so nothing steals focus.
  - Whether FL re-reads a changed `.pyscript` without a restart is **unverified**; it is drill A2.
- **Page sync with no port:**
  - The KeyLab's **Play button sends CC 21 on the DAW port** [local], and FL starts from that same message.
  - Web MIDI ports are multi-client under the new Windows service. Tonight the page already reads KeyLab notes while FL plays them (known fact).
  - So the page can open the DAW port and set bar 1 of the strip on CC 21's release. The expected error is a steady few ms (FL's buffer plus script handling) [inference].
  - Drift between FL's audio clock and Chrome's `performance.now()` is ppm-level, so a re-anchor on every Play is plenty [inference].
  - Two optional refinements: a "tap downbeat" key on the page, and later onset-locking to FL's audio through the Scarlett's **Loopback L+R** input [local; inference].

| | |
|---|---|
| **Needs installed** | Nothing. Optional: one file `ClaudeJam.pyscript` in `Documents\Image-Line\FL Studio\Settings\Piano roll scripts\`. It is not a download, but it is Daniel's FL folder, so ask (decision D1). |
| **Latency / sync** | Audio is **sample-accurate**, because FL's own sequencer plays everything. Changes land **between takes** (a drag or keypress, a few seconds). The page strip aligns within a few ms of FL's start, pending drill A1. Page alignment is visual only, so it never affects the sound. |
| **Effort** | ~1 session: SMF writer + generator + `/api/jam/*` + DAW-port Play anchor + strip. The strip and jam space are already being built. |
| **Risks** | No mid-take changes. Daniel does the clicks. Drag-and-drop may re-open the import dialog every time (Shift skips it). If he starts FL from the mouse or spacebar instead of the KeyLab, the page misses the anchor (fallback: tap key). Stock FL tools (Loop Starter, the Chord Progression tool with Bassline Generator) remain a manual fallback ([IL FL 2025 news](https://www.image-line.com/fl-studio-news/fl-studio-2025-whats-new-2)). |

### Option B: Loopback live band (virtual MIDI, Python sequencer, FL clock master)

```
                                  FL "Send master sync" (MIDI clock 24 ppq, start/stop)
 FL Studio ----------------------------------------------------------> loopback "FL Bridge" --> jam engine (ctypes WinMM in)
    ^                                                                                            | smooth BPM, count beats,
    |                                                                                            | plan one bar ahead
    |  Kontakt wrapper MIDI-in port = N, AD2 port = N (ch 10), Keys port = N (ch 2)               v
    +<------------------------------- loopback "Claude Backing" <---- jam engine (ctypes WinMM out, hi-res sleep)
                                             |
                                             +--(multi-client listen)--> piano page draws Claude's notes as FL gets them
 jam engine --SSE /api/jam/clock {epoch, bar, beat, bpm, playing}--> piano page (strip playhead, upcoming chord)
 KeyLab 88 mk3 --USB--> FL (port 0) + Chrome (as today)
```

**How it works:**
- Two **permanent in-box loopbacks** are made in MIDI Settings: "Claude Backing" and "FL Bridge".
- FL sends clock out on FL Bridge. The engine smooths tempo over 24-96 ticks and sends each role's notes on its own MIDI channel into Claude Backing.
- In FL, each target plugin's wrapper **MIDI input port** is set to Claude Backing's port number. Inside Kontakt, instruments can split by MIDI channel.
- Python 3.11 sleeps with 100 ns resolution on Windows ([CPython issue 45429](https://github.com/python/cpython/issues/89592)). Scheduling therefore stays in Python, never in a Chrome tab: hidden tabs are throttled to once per second or per minute ([Chrome timer throttling](https://developer.chrome.com/blog/timer-throttling-in-chrome-88)).

| | |
|---|---|
| **Needs installed** | **Windows MIDI Services SDK Runtime and Tools** (Microsoft, admin install; the page listed 1.0.14-rc.1.209 on 2026-09-14; size to state when asking) ([get-latest](https://microsoft.github.io/MIDI/get-latest/)). Plus two permanent loopbacks, a persistent configuration change. **No pip install** (ctypes). FL settings: enable the two ports, set wrapper input ports, turn on Send master sync. Alternative to the SDK: loopMIDI ([tobias-erichsen.de](https://www.tobias-erichsen.de/software/loopmidi.html)), not recommended (virtual-midi lane §3). |
| **Latency / sync** | Microsoft claims low-microsecond service jitter ([microsoft.github.io/MIDI](https://microsoft.github.io/MIDI/)). Output to ear is ~6-10 ms steady, which is FL's buffer plus the driver. Jitter is probably a few ms, mostly from FL rounding events to buffer boundaries [inference; **no measurement yet**]. The perceptible-jitter threshold is about 1-5 ms ([Expressiveness 2012](https://expressiveness.org/2012/12/04/midi-jitter)). Bar sync comes from counting clock ticks from Start; the absolute bar number comes from the Option C beacon. Changes land **next bar, mid-take**. |
| **Effort** | ~2 sessions: WinMM ctypes in/out + scheduler + clock follower (1), FL routing checklist + drills + page wiring (1). |
| **Risks** | (1) FL or Chrome may not list the user loopback on build 26200: documented, untested. (2) **Double-trigger:** a generic-controller input may also play the *selected* channel (Daniel's piano) as well as the matched wrapper [inference]. Mitigate by binding the port to the bridge script with `event.handled = True`; drill B3. (3) Clock-out jitter reports on FL's forum ([t=336310](https://forum.image-line.com/viewtopic.php?t=336310)). (4) Stuck notes on Stop: all-notes-off on every epoch bump. (5) Nothing records Claude's lines unless FL records the input (FL 2026.1.6 claims better MIDI record timing). (6) WinMM identifies ports by name, so keep the names stable ([Steinberg forum, Pete Brown](https://forums.steinberg.net/t/loopmidi-loopbe-etc-virtual-ports-replacement-for-windows/1025292/3)). |

### Option C: FL-native conductor (same loopback, FL's sequencer plays)

```
 jam engine --short SysEx / CC commands--> loopback "FL Bridge" --> device_ClaudeBridge.py (inside FL)
                                                                        |  transport.start/stop, tempo (REC_Tempo)
                                                                        |  patterns.jumpToPattern / clone / clear
                                                                        |  channels.setGridBit / setStepParameterByIndex
                                                                        |  playlist.triggerLiveClip (snap 1 bar)
                                                                        v
                                                                FL sequencer plays prepared patterns sample-accurately
 device_ClaudeBridge.py --SysEx beacon on OnUpdateBeatIndicator (bar/beat) + tempo + song pos--> FL Bridge --> jam engine
 jam engine --SSE clock (bar-exact, epoch)--> piano page
```

**How it works:**
- Claude **edits what FL is looping** instead of streaming notes. It flips drum grid steps and per-step pitch for a step-mode bass, switches to a prepared pattern, or launches a Performance-mode clip on the bar.
- Chords and expressive bass lines are written into patterns ahead of time (Option A's script or `.mid`), so the conductor only chooses between them live.
- The same script sends a small bar/beat/tempo beacon back.
- APIs: [transport](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/transport/), [sequencer](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/sequencer/), [performance](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/playlist/performance/), [callbacks](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/callbacks/), [device](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/device/device/). The new set-tempo, pattern-length and clear-pattern functions arrived in 25.2.4-26.1.3 per local WhatsNew.

| | |
|---|---|
| **Needs installed** | Same loopback as B, so no extra download. One file `Settings\Hardware\ClaudeBridge\device_ClaudeBridge.py`, assigned in MIDI Settings (Daniel's OK). |
| **Latency / sync** | Audio is **sample-accurate** (FL's sequencer). Command latency is a few ms plus FL's handling, and launches are quantised, so it doesn't matter. The beacon is **bar-exact**; `OnUpdateBeatIndicator` fires on bar and beat, and `OnIdle` fires about every 20 ms if it fires at all. |
| **Effort** | ~1-2 sessions after B's port exists: probe script (drill C1), command set, beacon, page wiring. |
| **Risks** | Sandbox unknowns (sockets and threads assumed blocked, `OnIdle` uncertain). The step grid is one pitch per step per channel, so chords need patterns or clips. FL scripting freezes were fixed only in 26.1.3 RC1, so update to 2026.1.6 first (D5). Windows MIDI silently drops over-long SysEx, so keep messages tens of bytes ([Flapi Unmaintained.md](https://github.com/MaddyGuthridge/Flapi/blob/main/Unmaintained.md)). Arturia's scripts own ports 0 and 236; never touch them. |

### Option D: Plugin inside FL (plugdata test, then a JUCE "jam-plug")

```
 jam engine --SSE /api/fl/patterns?role=bass (plugin connects OUT; no listening port in FL)--> jam-plug (Channel Rack "instrument")
                                                                                             | lock-free FIFO -> audio thread
                                                                                             | reads host tempo + projectTimeMusic
                                                                                             | emits notes at exact sampleOffset
                                                                                             v  MIDI out port 11
                                                                          Kontakt (wrapper MIDI-in port 11) -> audio
 jam-plug --heartbeat ~50 ms {bpm, ppq, bar, playing, armed/launched}--> jam engine --SSE--> piano page
 (plugdata test variant: Pd patch receives OSC/Pd messages; host tempo from the plugin; same port routing)
```

**How it works:**
- Each role gets a generator plugin whose MIDI out port matches the target instrument's input port.
- The plugin schedules against FL's playhead:
  - VST3: `ProcessContext`, plus a `sampleOffset` per event ([Steinberg](https://steinbergmedia.github.io/vst3_doc/vstinterfaces/structSteinberg_1_1Vst_1_1ProcessContext.html)).
  - CLAP: event `time` plus the transport event ([CLAP events.h](https://raw.githubusercontent.com/free-audio/clap/main/include/clap/events.h)).
- FL fixed VST3 plugin-to-plugin MIDI in 24.2.99 Beta 1 and CLAP note output in Beta 8 (local WhatsNew), so 26.1.3 has both fixes.

| | |
|---|---|
| **Needs installed** | Test: **plugdata MSI**, ~257 MB ([plugdata](https://github.com/plugdata-team/plugdata)). Custom: **Visual Studio Build Tools (C++)**, 2.3-60 GB with admin rights ([Microsoft Learn](https://learn.microsoft.com/en-us/visualstudio/releases/2026/vs-system-requirements)), plus CMake and a JUCE 9 clone ([JUCE](https://juce.com/get-juce/)). All need Daniel's OK. |
| **Latency / sync** | **Sample-accurate against FL's own playhead.** Tempo and bar sync come for free from the host, with no clock following and no loopback. Open question: does FL deliver generator MIDI to the target in the same audio block or one block late (drill D2)? |
| **Effort** | plugdata ~1 session. JUCE plugin ~3-5 sessions. |
| **Risks** | Toolchain size. An unsigned DLL loaded into FL: a plugin crash takes FL down. plugdata's `[netreceive]` only runs while the DAW processes audio ([plugdata discussion #144](https://github.com/plugdata-team/plugdata/discussions/144)). FL has no MIDI-effect slot, so the plugin loads as an instrument. Pitch-bend routing between plugins is reported erratic ([JUCE forum 2025](https://forum.juce.com/t/midi-generator-plugin-im-distributing-a-vst3i-could-i-distribute-a-vst3-midi-effect-too-for-ableton-cubase-fl-studio/65814)). A listening UDP port in FL may prompt the firewall (unverified), hence the outbound SSE design. |

### 3.5 Side by side

| | A. Hand-delivered | B. Loopback live band | C. FL conductor | D. Plugin |
|---|---|---|---|---|
| New downloads | **none** | MIDI Services SDK tools | (same as B) | plugdata ~257 MB; later MSVC multi-GB |
| Mid-take changes | no (between takes) | **yes, next bar** | **yes, next bar** (prepared material) | **yes, next bar** |
| Audio timing | sample-accurate | ~ms jitter (to measure) | sample-accurate | sample-accurate |
| Bar sync to page | KeyLab Play anchor (few ms, visual) | clock ticks (+ C beacon for bar no.) | bar-exact beacon | playhead heartbeat |
| Daniel's clicks per change | 1 drag or key | 0 | 0 | 0 |
| Chords / polyphony | full | full | via prepared patterns | full |
| Records into FL as notes | yes (it *is* notes) | only if FL records input | yes (patterns) | via "burn notes" / recording |
| Effort | ~1 session | ~2 | +1-2 on B | 1 (plugdata) / 3-5 (JUCE) |
| Biggest risk | friction between takes | loopback visibility, double-trigger | sandbox | toolchain, plugin crash |

---

## 4. How it ties into the arsenal pieces

### 4.1 Cue channel and CLI verbs

- **Keep `pianocue` as is.** Its cue notes are limited to 21..108 and its voice belongs to the page [local]. Add a sibling **`arsenal/jam.py`**, reachable through `py -m arsenal.jam <verb>`, with its own routes in `serve.py` in the same style as `/api/piano/cues` (SSE, heartbeat, replay of recent events):
  - `POST /api/jam/loop`: set or replace a loop (pattern contract, idempotent by `id` + `rev`)
  - `POST /api/jam/cmd`: `start | stop | tempo | mute | solo | fill | section | clear`
  - `GET /api/jam/events`: SSE of `loop-armed`, `loop-launched {bar}`, `clock {epoch, bar, beat, bpm, playing, source, uncertainty_ms}`
  - `GET /api/jam/status`: output backend, ports seen, listeners, last clock
- **Verbs** (flags mirror `pianocue progression`: `--key`, `--bpm`, `item:beats`, `--voicing`, `--voice-lead` [local]):
  - `loop "Ebm9 | Ab13 | Dbmaj9 | Bb7#9b13" --key "Db major" --bpm 84 --style neo-soul`: builds all three roles
  - `bass --style walk|pulse|pocket|pedal|gospel-run`, `drums --style half-time|pocket|12-8|toms|brushes`, `comp --style pad|stabs|pulse|arp`: regenerate one role, launching on the next bar
  - `fill [--bar 4]`, `mute drums`, `solo bass`, `tempo 80`, `section B`, `transpose +1` (the gospel lift from Db to D)
  - `export [--dir state/arsenal/jam/<id>]`: Option A's `.mid` and `.pyscript` files
  - `status`, `drill timing|visibility|double-trigger|sandbox`: each drill writes a dated receipt
- **Chord voicings reuse `pianocue_voicing.mjs`** [local], so names, Nashville numbers and voicings match the page exactly. Only drums need the wider 0..127 range.

### 4.2 Jam loops and concept cards

- A **concept card** = a named loop (the pattern contract) plus a teaching point, a sound brief and an FL recipe. Example card: *"Common-tone pad, moving bass"*, F minor ostinato (section 9, example 4). The upper voices barely move while the bass walks F → Db → Ab → G, and the card explains why that sounds cinematic.
- **Card actions:**
  - **Play** sends the loop to whichever output backend is live.
  - **Export** writes `.mid` files.
  - **Brief** shows Splice search phrases.
  - **Vary** asks Claude for a B section or fill.
- **Sound brief on each card** (from the Splice lane): keyword phrases, a "Describe a Sound" sentence, BPM, key, one-shot vs loop, and first **packs Daniel already owns** (e.g. "Sounds of KSHMR Vol 5 - Drums" [local]) so no credits are spent. Daniel auditions in the Splice app through **Splice Bridge on a spare FL channel**, which is tempo- and key-synced with the running groove ([Splice: using Bridge](https://support.splice.com/en/articles/8652857-how-do-i-use-splice-bridge)). Claude then reads the new files under `Documents\Splice` and proposes which FPC pad each goes on (GM 36/38/42/46). Claude never touches splice.com.

### 4.3 The piano visualizer

- **Stays a pure display.** No audio-critical scheduling in the tab; the browser voice schedules ahead only in the "jam without FL" fallback.
- **Lead-sheet strip:**
  - The chart comes from `/api/jam/loop`.
  - The playhead comes from the jam clock (anchor + BPM, evaluated on `performance.now()`).
  - The **next chord is shown a bar ahead**, which is the payoff of sending patterns in advance.
- **Role lanes:**
  - Claude's bass and comp appear on the 3D keys as ghost or tinted notes: a colour per role, distinct from Daniel's.
  - Drums are a pulse lane above the strip (kick, snare, hats), not keys.
  - In Option B the notes can come straight off the "Claude Backing" port (multi-client), so the page draws exactly what FL received. In A, C and D they come from the pattern plus the clock.
- **Daniel's notes:** unchanged (KeyLab via Web MIDI). In v2 the page's existing chord detection (`nashville.js`) feeds the listening band (section 7).

### 4.4 Practice log and riff analysis

- **Stamp musical time.** Practice events stay `t_ms`-based. `validate_event` lets unknown fields pass through [local], so each event can carry an optional `jam: {loop_id, rev, epoch, bar, beat}` without breaking the v0 schema. Session meta stores the loop spec and clock anchors, so a replay can re-sound the backing (`pianocue replay` + `jam` loop at the same bar).
- **New findings the analyzer can report** once events carry bar and beat [inference]:
  - **Placement:** an onset histogram against the beat, e.g. "you anticipate beat 3 by a 16th", "your turnaround rushes by ~40 ms".
  - **Target tones per chart chord**, e.g. "over 5sus you land on the sus4 60% of the time; over 6m you favour the 11".
  - **Space:** where Daniel leaves gaps, which is input for v2 call-and-response fills.
  - **Loop to groove:** `performance.py` already detects 3-4 chord loops played back to back [local]. When the log shows a loop, Claude offers "turn this into a jam card" with a matching groove.
- **Key and tempo:** `estimate_key` and the rough IOI tempo in the practice analyzer [local] can seed `--key` and `--bpm` for the next loop.
- **Boundary:** the Splice licence forbids AI training on Splice content. The analyzer runs on Daniel's playing and Claude's generated MIDI only, **not** on Splice WAV audio, unless Daniel rules otherwise (D9).

---

## 5. Where the sounds come from (FL recipe for a "Claude Jam" template)

Recommended default channel set. Daniel saves it once as an FL template; this is his GUI action.

| Channel | Default instrument | Why | Alternates |
|---|---|---|---|
| Daniel's piano (selected) | his usual Kontakt piano (e.g. The Grandeur) | unchanged workflow | Arturia Piano V3 |
| Claude Bass | **Serum 2** (a sub or finger-bass patch) or Arturia Mini V4 | plain vendor installs, reliable when automated (inventory note) | Kontakt bass libraries, keeping notes out of keyswitch zones (e.g. DjinnBass II force-string keyswitches at G8) |
| Claude Drums | **Addictive Drums 2** with its GM map preset | kick 36 and snare 38 by default; GM preset exists ([XLN MIDI mapping](https://support.xlnaudio.com/hc/en-us/articles/16593408783389-MIDI-Mapping-Window)) | FPC *Empty* preset + Splice one-shots on GM pads |
| Claude Keys | **Arturia Stage-73 V2** (EP) or a Kontakt pad | neo-soul and gospel comping | Splice INSTRUMENT (LABS content), Analog Lab V |
| Splice Bridge | Splice Bridge | in-time, in-key auditioning of Splice sounds during the jam | — |

Bass register for generated lines: MIDI **28-55** (splice lane §7.3), with library-specific ranges checked before use. Transistor Bass needs All Plugins Edition, so check the edition (D10).

---

## 6. Tempo and bar sync: making the strip, Claude and Daniel line up

**One timeline: FL's.** Every source below produces the same thing: an anchor `(epoch, bar, beat)` at a server time, a BPM, and an uncertainty.

| Source (best first) | Gives | Granularity / uncertainty | Available in |
|---|---|---|---|
| Plugin heartbeat (VST3 `projectTimeMusic`) | exact ppq, bpm, playing | sample-accurate in FL; ~50 ms heartbeat to the page | D |
| Conductor beacon (`OnUpdateBeatIndicator` + `transport.getSongPos`) | absolute bar/beat, bpm, loop mode | bar and beat ticks; few ms | C (with B) |
| MIDI clock ticks (Send master sync) | tempo + phase from Start (24 ppq); no absolute bar | ~ms jitter, smoothed over 24-96 ticks | B |
| KeyLab Play (CC 21 on DAW port) | "bar 1 starts now" + the loop's BPM | steady few-ms offset; visual only | **A** (and a sanity check in all) |
| Tap / audio-onset via Scarlett Loopback | manual or detected downbeat | tap ±20-30 ms; onset lock to be measured | fallback |

**Rules [inference]:**

1. **Epochs.** A new epoch starts on FL Start, Stop, jump, tempo change and pattern-loop wrap (or wraps are modelled as `bar mod loop_bars` within one epoch; pick one and test). Anything stamped with an old epoch is dropped: cues, drawn notes, pending launches. This is `timebase.StaleEpoch` [local].
2. **Server ↔ page clock.** Each SSE clock event carries `server_ns`. The page keeps a running offset estimate to `performance.now()`, taking the minimum delay over the last N heartbeats, and shows `uncertainty_ms` in a debug overlay.
3. **What "on the beat" means.** A note's musical time is when **FL receives it**. Daniel's KeyLab notes reach Chrome and FL at about the same moment (same USB event, multi-client), so no correction is applied to his notes. Claude's notes are drawn at their scheduled beat. The ~5-10 ms audio output latency applies to both equally, so nothing needs compensating for alignment.
4. **Launch quantisation.** The engine sends a new loop at least one beat before the bar line. Launch is `next_bar` measured on the jam clock. If a change arrives later than that, it waits a bar rather than landing late.
5. **Tempo changes.** FL leads. The engine re-plans the next bar on a beacon or clock BPM change. In A, the `.mid` carries tempo, but FL's project tempo wins; the CLI prints "set FL to 84 BPM".
6. **Loop lengths.** The chart's `bars` defines the strip's loop. FL's pattern length should match. The conductor can set pattern length (`setPatternLength`, 26.1 Beta 1, local WhatsNew); in A, Daniel's pattern length follows the imported notes.
7. **Pattern vs song mode.** V1 assumes pattern loop mode. Song mode with markers comes in v2 (markers and Performance-mode clips).

---

## 7. Roadmap

### MVP ("tonight-ready": buildable next session with no approvals)

**Scope: Option A plus page sync.**
1. `arsenal/jam.py`:
   - pattern generator (styles in section 9)
   - stdlib SMF writer
   - `export`, `loop`, `bass`, `drums`, `comp`, `status` verbs
   - `/api/jam/loop` and `/api/jam/events`
2. Page:
   - lead-sheet strip with bar playhead and next chord
   - role lanes
   - **KeyLab Play anchor**: the page opens the "KeyLab 88 mk3 DAW" input and listens for CC 21 release and CC 20
   - tap-downbeat fallback
3. `ClaudeJam.pyscript` generator with baked-in notes. It is written to `state/arsenal/jam/<id>/`. Daniel copies it or approves the drop (D1).
4. Two concept cards to start: the Db neo-soul and Eb worship loops below.

**Drills (each with a dated receipt under the drill doctrine):**
- **A1:** page strip vs FL metronome offset over 32 bars. Record the page flash with the FL click; target a steady offset under 15 ms.
- **A2:** does FL pick up an edited `.pyscript` without a restart?
- **A3:** does the DAW port open multi-client in Chrome without disturbing the Arturia script (display, transport)?

**Done when:** Daniel drags three files, presses Play on the KeyLab, and improvises over Claude's groove while the strip tracks bars.

### v1 (one download: Option B + C)

1. Daniel approves and installs the **SDK Runtime and Tools**, then creates permanent loopbacks **"Claude Backing"** and **"FL Bridge"**, before launching FL and Chrome.
2. Drills, in order, each with a receipt:
   - **B1 visibility:** both ports listed in FL and in Chrome.
   - **C1 sandbox probe:** `device_JamProbe.py` tries `socket`, `threading`, `os` and file write, and counts `OnIdle` per second and beat-indicator calls (fl-scripting lane §4).
   - **B3 double-trigger:** does a generic input also sound the selected piano channel?
   - **B2 timing:** clicks from the engine through the loopback into an FL sampler, recorded against FL's metronome; report mean offset and spread at 256 samples.
   - **B4 stuck notes:** stop mid-note and jump; no hanging notes.
3. Build:
   - ctypes WinMM out/in
   - clock follower + bar-ahead scheduler (hi-res sleep plus a short busy-wait)
   - `device_ClaudeBridge.py`: beacon plus start, stop, tempo, `jumpToPattern`, `triggerLiveClip` bar-snapped, grid edits
   - CLI `start`, `stop`, `tempo`, `fill`, `section`, `mute`
   - page draws from the Claude Backing port or the clock SSE
4. Practice log gets the `jam` stamps; the riff analysis adds placement and target-tone findings.

**Timing budget to pass:** spread under ~3 ms on drums at 256 samples. If B2 misses, keep B for bass and comp, move drums to C (FL-played patterns), and schedule Option D.

**Also in v1 (D5):** update FL to 2026.1.6 before the drills, so they measure the version he will jam on.

### v2 (the band listens, sound gets deeper)

- **Listening band:**
  - **Chord following:** if Daniel reharmonises (the page's chord detection says Gbmaj7 where the chart says Ebm9), the bass follows next bar.
  - **Register ducking:** comp thins when his left hand is below C4.
  - **Call and response:** drum or bass fills in the gaps he leaves.
  - **Modulation following:** if he lifts Db → D, the whole band transposes next bar.
- **Option D bake-off:** plugdata test (D6). JUCE jam-plug only if it clearly wins on timing or removes a pain point (D7).
- **Arrangement:** Performance-mode clips per section, and KeyLab pads (channel-10 notes on the DAW port [local]) mapped in the page to "fill / next section / mute". The Arturia script also reacts to pads, so pad mapping needs a check first.
- **Capture:**
  - FL 2026's **Audio Logger** keeps the last 60 s of master ([IL FL 2026](https://www.image-line.com/fl-studio/release/2026)).
  - Merge that with the practice log into a "session record" card: loop, his take, the analysis.
  - Replay the session with the backing re-sounded.
- **Sound loop:** card briefs, then Bridge auditions, then Claude maps the new Splice files to pads. The Splice Sounds Plugin beta is optional (D8).

---

## 8. The jam session from Daniel's side

1. He opens FL's **"Claude Jam"** template: his piano selected, plus Claude Bass, Claude Drums, Claude Keys and Splice Bridge channels. Then he opens `127.0.0.1:8793/piano`.
2. He says, in chat or with a card tap: *"Db, neo-soul, 84, something lazy."* Claude replies with a chart (`Ebm9 | Ab13 | Dbmaj9 | Bb7#9b13`, numbers 2m–5–1–6) and the strip appears on the page.
   - MVP: "drag these three" (or "run ClaudeJam"), then he presses Play on the KeyLab.
   - v1: nothing to drag; FL starts or the loop simply arrives on the next bar.
3. He plays. The strip shows the current bar and the **next chord a bar early**. Claude's bass and comp glow as ghost keys in their own colours, and his own notes glow as they do now.
4. He talks to the band between phrases:
   - *"half-time"*, *"walk the bass"*, *"gospel fill into the top"*, *"drop the drums for 4"*
   - *"take it up a half step"*: Db → D, the gospel lift, which lands on the next loop
   - *"darker keys"*: a patch suggestion plus a Splice brief card
   - In the MVP these take effect between takes; in v1, on the next bar.
5. He stops. The practice log closes with a musical-time summary: where he lands, what he targets over each chord, which riff he kept returning to. Claude offers to save the loop and his favourite moment as a concept card. The FL Audio Logger holds the last minute if the take was a keeper.

---

## 9. What Claude can generate, with examples in his colour

### 9.1 Generator vocabulary

| Role | Styles | Rules |
|---|---|---|
| **Bass** | `pulse` (8th ostinato), `pocket` (syncopated neo-soul with ghosts and octave pops), `walk` (chromatic approaches into each change), `gospel-run` (triplet walk-ups/downs into the 1), `pedal` (cinematic pedal under moving chords), `root-fifth` (worship half-time) | roots on chart downbeats unless it's a slash chord; approach tones a half step from below or above in the last 8th/16th/triplet; register 28-55; velocity accents on downbeats, ghosts ~40; avoid keyswitch zones |
| **Drums** | `half-time` (worship/cinematic), `pocket` (neo-soul, lazy snare, swung 16th hats), `12-8` (gospel ballad triplet feel), `toms` (cinematic build, no hats), `brushes` (ballad), `four-floor` (for fun) | GM notes; hat velocity patterns; fills every 4 or 8 bars on request; micro-timing as tick offsets (snare +8-12 ms "lay back"); crash only on the loop top after a fill |
| **Comp** | `pad` (sustained, voice-led), `stabs` (anticipated "and of 4" pushes), `pulse` (8th EP), `arp` (harp-like cinematic), `shells` (3rd+7th with 9/13 colour) | rootless voicings above the bass, between ~Eb3 and ~G4, leaving his upper register free; voice-led with least movement (reuses `--voice-lead` [local]); pushed chords are written at beat -0.25 of the bar |

**Notation below:** notes are MIDI integers (FL shows 60 as C5). Beats count from 0 at bar 1. `len` is in beats. Drum grids are 16 steps per 4/4 bar (steps 0/4/8/12 = beats 1/2/3/4), or 12 triplet steps in the 12/8-feel example. These are starting points for Daniel's ears, not rules.

### 9.2 Example 1: "Grandeur lift", Eb major, 68 BPM, half-time worship

Chart: `| Abmaj9 | Bb13sus4 | Cm11 | Ebmaj9/G |`, numbers **4 – 5sus – 6m – 1/3**

Bass (Serum sub or a finger bass):

| beat | 0 | 2.5 | 3 | 3.5 | 4 | 6.5 | 7 | 7.5 | 8 | 10.5 | 11 | 11.5 | 12 | 14.5 | 15 | 15.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| note | Ab1 32 | Eb2 39 | Ab1 32 | A1 33 | Bb1 34 | F2 41 | Bb1 34 | B1 35 | C2 36 | G2 43 | Bb1 34 | Ab1 32 | G1 31 | D2 38 | Eb2 39 | G1 31 |
| len | 2.5 | .5 | .5 | .5 | 2.5 | .5 | .5 | .5 | 2.5 | .5 | .5 | .5 | 2.5 | .5 | .5 | .5 |

A1 33 and B1 35 are chromatic approaches into Bb and C; Bb–Ab–G walks down into the 1/3.

Comp (pad, whole notes, rootless):
- Abmaj9 `[51, 55, 58, 60]`
- Bb13sus4 `[51, 55, 56, 60]`
- Cm11 `[51, 53, 58, 62]`
- Ebmaj9/G `[51, 58, 62, 65]`

Drums (AD2; bars 1-3, then a bar-4 fill):
```
step    1 . . . 2 . . . 3 . . . 4 . . .
kick36  X . . . . . . . . . X . . . . .
snr38   . . . . . . . . X . . . . . . .
hat42   x . x . x . x . x . x . x . x .      (vel 72 / 46 alternating)
bar 4:  kick 0,6,10; toms 50@12 48@13 45@14 41@15; crash49 on the next loop's step 0
```

### 9.3 Example 2: "Lazy pocket", Db major, 84 BPM, neo-soul (16th swing ~56%)

Chart: `| Ebm9 | Ab13 | Dbmaj9 | Bb7(#9,b13) |`, numbers **2m – 5 – 1 – 6** (V of 2 back to the top)

Bass (Stage-73 or Serum finger bass, pocket):
- **Bar 1 (Ebm9):** Eb2 39 @0 len .75 · Eb2 39 ghost vel 40 @.75 len .25 · Bb1 34 @1.5 · Db2 37 @2.5 · Eb2 39 @3 · G1 31 @3.75 len .25 (approach)
- **Bar 2 (Ab13):** Ab1 32 @4 len 1 · Eb2 39 @5.5 · Ab2 44 @6 len .25 (octave pop) · Gb2 42 @6.5 · C2 36 @7.5 (approach)
- **Bar 3 (Dbmaj9):** Db2 37 @8 len 1.5 · Ab1 32 @9.75 · Db2 37 @10.5 · F2 41 @11 · Ab2 44 @11.5 · A1 33 @11.75 (approach)
- **Bar 4 (Bb7alt):** Bb1 34 @12 len 1 · D2 38 @13.5 · Gb2 42 @14 · F2 41 @14.5 · E2 40 @15.5, falling into Eb2 at the top

Comp (EP stabs, voice-led, pushed a 16th early):
- Ebm9 `[54, 58, 61, 65]`
- Ab13 `[54, 58, 60, 65]` (only Db → C moves)
- Dbmaj9 `[53, 56, 60, 63]`
- Bb7(#9,b13) `[50, 56, 61, 66]`

Each chord hits at bar start − 0.25 (len 1.5) and again at beat 2.75 (len .75).

Drums:
```
step    1 . . . 2 . . . 3 . . . 4 . . .
kick36  X . . . . . . X . . X . . . . .
snr38   . . . . X . . . . . . g . . . g      (X = backbeat, laid back ~10 ms; g = ghost vel 30)
hat42   x x x x x x x x x x x x x x x x      (vel 80/35/55/35, swung)
```

### 9.4 Example 3: "Sunday walk", D major, 12/8 feel (FL at 60 BPM, triplet grid)

Chart: `| Gmaj9 A/G | F#m9 Bm9 | Em9 A13sus4 A7b9 | Dmaj9 D/F# |`, numbers **4 5/4 – 3m 6m – 2m 5sus 5 – 1 1/3**

Bass (triplet walks, the gospel signature):
- **Bar 1:** G1 31 @0 len 3, then the walk-down A1 33 @3 · G#1 32 @3.33 · G1 31 @3.67 → F#
- **Bar 2:** F#1 30 @4 len 1.67 · C#2 37 @5.67 · B1 35 @6, then the walk-up C#2 37 @7 · D2 38 @7.33 · D#2 39 @7.67 → E
- **Bar 3:** E2 40 @8 len 1.67 · B1 35 @9.67 · A1 33 @10 len 1 · A1 33 @11 len .67 · C#2 37 @11.67 → D
- **Bar 4:** D2 38 @12 len 2 · E2 40 @14.67 · F#1 30 @15 len 1 → G at the top

Comp (organ or EP, triplet pushes):
- Gmaj9 `[59, 62, 66, 69]`
- A/G `[57, 61, 64]`
- F#m9 `[57, 61, 64, 68]`
- Bm9 `[57, 61, 62, 66]`
- Em9 `[55, 59, 62, 66]`
- A13sus4 `[55, 59, 62, 66]` (same notes as Em9 over A, a nice card point)
- A7b9 `[55, 58, 61, 66]`
- Dmaj9 `[54, 57, 61, 64]`
- D/F# `[57, 62, 66]`

Drums (12 triplet steps per bar):
```
step    1 . . 2 . . 3 . . 4 . .
kick36  X . . . . x X . . . . .      (x = soft pickup)
snr38   . . . X . . . . . X . .
hat42   x x x x x x x x x x x x      (accent on 1 2 3 4)
bar 4:  toms 48/45/41 on the last three triplets; crash49 at the top
```

### 9.5 Example 4: "Common-tone pad, moving bass", F minor, 90 BPM, cinematic

Chart: `| Fm(add9) | Dbmaj7(#11) | Abmaj9 | Eb6/G |`, i – VI – III – VII6/2; in Ab-major numbers **6m – 4 – 1 – 5/7**

- **Bass:** straight 8ths with a 3+3+2 accent (steps 0, 3, 6 of the 8), on F1 29 · Db2 37 · Ab1 32 · G1 31.
- **Comp (strings or Albion-style pad):**
  - bars 1-2 hold `[48, 53, 55, 56]` (C F G Ab); over F it is Fm(add9), over Db it is Dbmaj9(#11)
  - bars 3-4 hold `[48, 51, 55, 58]` (C Eb G Bb); over Ab it is Abmaj9, over G it is Eb6/G
  - **The top voices move once in four bars. The bass does the storytelling.**
- **Drums (no hats in section A):**
  ```
  step    1 . . . 2 . . . 3 . . . 4 . . .
  tom41   X . . . . . X . . . X . . . . .
  tom45   . . . . . . . . . . . . x . x .
  kick36  X . . . . . . . . . . . . . . .      (loop top only)
  bar 4:  16th toms 45/43/41 crescendo, crash49 + kick36 at the top; section B adds hat42 8ths
  ```

### 9.6 Example 5 (sketch): "Gb evening", Gb major, 64 BPM, lush ballad

- **Chart:** `| Gbmaj9 | Ebm11 | Cbmaj9(#11) | Db13sus4 Db7b9 |`, numbers **1 – 6m – 4 – 5sus 5**
- **Bass:** whole-note roots Gb1 30 · Eb2 39 · B1 35 (Cb) · Db2 37, with the fifth on beat 3 and an octave lift on the last 8th of bar 4.
- **Drums:** brushes feel. Soft kick on 1, cross-stick 37 on 3, pedal hat 44 on 2 and 4.
- **Comp:** a slow `arp` in the Keys channel.

**Riff-analysis hook.** If the practice log shows Daniel looping, say, 1–6m–4–5 in Db (the loop detector already exists [local]), the jam engine offers that exact chart with the "Lazy pocket" groove, closing the loop from practice to jam.

---

## 10. Decisions and downloads for Daniel (morning list, each with a recommended default)

| # | Decision | Download / change | Recommended default |
|---|---|---|---|
| **D1** | Let Claude drop `ClaudeJam.pyscript` (MVP) into `Documents\Image-Line\FL Studio\Settings\Piano roll scripts\` | a file in his FL user folder; no download | **Yes.** Otherwise Claude leaves it in `state/arsenal/jam/` and he drags `.mid` files instead |
| **D2** | Install **Windows MIDI Services SDK Runtime and Tools** and create two permanent loopbacks, "Claude Backing" and "FL Bridge" | Microsoft download (GitHub or WinGet `Microsoft.WindowsMIDIServicesSDK`), admin install; 1.0.14-rc.1.209 listed 2026-09-14; size stated at ask time; persistent MIDI config | **Yes** (the v1 enabler). Create the ports before starting FL and Chrome |
| D3 | loopMIDI instead of D2 | third-party driver download | **No** (Windows 7-10 listed; in-box loopbacks survive reboot) |
| D4 | FL settings for v1: enable the two ports, Send master sync on FL Bridge, wrapper input ports on Claude Bass/Drums/Keys, assign `device_ClaudeBridge.py` | FL settings changes | **Yes, by Daniel with a one-page checklist** (Claude never drives the FL GUI) |
| D5 | Update FL 26.1.3 → **2026.1.6** | FL installer download | **Yes, before the v1 drills,** at a quiet moment with the current project saved |
| D6 | **plugdata** for the plugin bake-off | ~257 MB MSI from GitHub | **Defer** until the v1 timing drill says we need it |
| D7 | **VS Build Tools (C++) + CMake + JUCE 9** for a custom jam-plug | multi-GB, admin | **No for now** (a v2 decision after D6) |
| D8 | **Splice Sounds Plugin** beta | download + login | **No.** Bridge already gives in-sync auditioning |
| D9 | May the riff/loop analyzer run on Splice WAV audio (tempo/key detection)? | policy | **No:** file names and tags only; analysis stays on his playing and Claude's MIDI (licence bans AI training) |
| D10 | Default instruments: Serum 2 or Mini V4 bass, Addictive Drums 2 (GM map), Stage-73 V2 keys; check FL edition for Transistor Bass | GUI choices | **Yes to those defaults.** He swaps freely |
| D11 | Add `Documents\Splice` to FL's browser search paths (and remove the stale `E:\Sample Packs\`) | FL setting | **Yes, by Daniel** |
| D12 | Freesound account + personal API key | account creation (his) | **No** (not needed; FL stock packs + his Splice library suffice) |

---

## 11. Open questions (each closes with a drill or a primary source)

1. Do FL 26.1.3 / 2026.1.6 and Chrome 152 list a user-created in-box loopback, by name, on build 26200? (B1)
2. Does a generic loopback input also play the selected channel on top of the matched wrapper port? (B3)
3. FL device-script sandbox: sockets, threads, file I/O, `OnIdle`? (C1)
4. Real jitter from the ctypes WinMM scheduler through the loopback into FL at the Focusrite buffer. The actual ASIO buffer is set in Focusrite's panel, and FL's stored 256 may be FL ASIO's. (B2)
5. Can Chrome open the KeyLab DAW port alongside FL without upsetting the Arturia script, and does CC 21 arrive on release as the script implies? (A3)
6. Does FL re-read an edited `.pyscript` without a restart? (A2)
7. Does FL send a Song Position Pointer on mid-song start or pattern loop wrap, or is the beacon the only source of absolute bar? (B2 capture)
8. Does FL deliver generator-plugin MIDI to the target in the same block? (D2, only if Option D proceeds)
9. KeyLab pads (channel-10 notes on the DAW port) as band controls: does the Arturia script consume them in a way that conflicts? (v2)
10. Which Splice plan and credits does Daniel have, and which FL edition? (ask)

---

## 12. Sources

**New checks for this plan (fetched or read 2026-09-14):**
- Microsoft Learn, midiOutShortMsg: https://learn.microsoft.com/en-us/windows/win32/api/mmeapi/nf-mmeapi-midioutshortmsg (page updated 2024-02-22)
- Microsoft Learn, midiInOpen: https://learn.microsoft.com/en-us/windows/win32/api/mmeapi/nf-mmeapi-midiinopen (page updated 2024-02-22)
- Python 3.11 docs, ctypes: https://docs.python.org/3.11/library/ctypes.html
- MIDI Association, Standard MIDI Files specification: https://midi.org/standard-midi-files-specification
- Image-Line manual, Import MIDI data dialog: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/automation_midiimport.htm
- Image-Line manual, MIDI file formats: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/fformats_other_mid.htm
- Local: `C:\Users\L5\Documents\Image-Line\FL Studio\Settings\Hardware\Arturia KeyLab mk3\KL3Process.py` (Play = CC 21, Stop = CC 20, pads on status 153); `E:\AI-Setup\arsenal\pianocue.py`, `timebase.py`, `performance.py`, `practice.py`, `web\piano\cues.js`

**Carried from the lane docs (full lists there):**
- Image-Line:
  - MIDI scripting https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/midi_scripting.htm
  - MIDI settings https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_midi.htm
  - audio settings https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_audio.htm
  - plugin wrapper https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/wrapper.htm
  - MIDI Out https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/MIDI%20Out.htm
  - piano roll scripting https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_scripting_api.htm
  - piano roll MIDI import https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_midi.htm
  - FPC https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/FPC.htm
  - FL 2026 https://www.image-line.com/fl-studio/release/2026
  - FL 2025 https://www.image-line.com/fl-studio-news/fl-studio-2025-whats-new-2
  - forum 2026.1.6 https://forum.image-line.com/viewtopic.php?t=342331
  - Link thread https://forum.image-line.com/viewtopic.php?t=308744
  - clock jitter https://forum.image-line.com/viewtopic.php?t=336310
  - note naming https://forum.image-line.com/viewtopic.php?t=76662
- IL API stubs:
  - index https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/
  - transport https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/transport/
  - callbacks https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/callbacks/
  - sequencer https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/sequencer/
  - performance https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/playlist/performance/
  - device https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/device/device/
- Microsoft MIDI:
  - home https://microsoft.github.io/MIDI/
  - get-latest https://microsoft.github.io/MIDI/get-latest/
  - diagnostic endpoints https://microsoft.github.io/MIDI/kb/diagnostic-endpoints/
  - create loopbacks https://microsoft.github.io/MIDI/kb/how-to-create-loopback-endpoints-using-tools/
  - Windows Experience Blog https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/
  - Pete Brown on port names https://forums.steinberg.net/t/loopmidi-loopbe-etc-virtual-ports-replacement-for-windows/1025292/3
- Timing:
  - CPython hi-res sleep https://github.com/python/cpython/issues/89592
  - Chrome throttling https://developer.chrome.com/blog/timer-throttling-in-chrome-88
  - jitter perception https://expressiveness.org/2012/12/04/midi-jitter
- Community bridges:
  - Flapi https://github.com/MaddyGuthridge/Flapi/blob/main/Unmaintained.md
  - Boyan253 https://github.com/Boyan253/fl-studio-2025-ai-bridge
  - MadBlast0 https://github.com/MadBlast0/Fl-Studio-MCP
- Plugins:
  - Steinberg ProcessContext https://steinbergmedia.github.io/vst3_doc/vstinterfaces/structSteinberg_1_1Vst_1_1ProcessContext.html
  - CLAP events https://raw.githubusercontent.com/free-audio/clap/main/include/clap/events.h
  - JUCE https://juce.com/get-juce/
  - plugdata https://github.com/plugdata-team/plugdata
  - plugdata #144 https://github.com/plugdata-team/plugdata/discussions/144
  - JUCE forum MIDI generator https://forum.juce.com/t/midi-generator-plugin-im-distributing-a-vst3i-could-i-distribute-a-vst3-midi-effect-too-for-ableton-cubase-fl-studio/65814
  - VS requirements https://learn.microsoft.com/en-us/visualstudio/releases/2026/vs-system-requirements
  - loopMIDI https://www.tobias-erichsen.de/software/loopmidi.html
- Splice and sounds:
  - terms https://splice.com/terms
  - licensing FAQ https://support.splice.com/en/articles/8652642-splice-sounds-licensing-faq
  - Bridge https://support.splice.com/en/articles/8652857-how-do-i-use-splice-bridge
  - XLN MIDI mapping https://support.xlnaudio.com/hc/en-us/articles/16593408783389-MIDI-Mapping-Window
  - General MIDI https://en.wikipedia.org/wiki/General_MIDI
