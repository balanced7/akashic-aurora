# Plugin path: a small plugin inside FL Studio that Claude plays through

- **Status:** in-flight research, not ratified
- **Date:** 2026-09-14
- **Lane:** custom plugin path (the fl-jam-bridge fan-out)
- **Question:** Can a small plugin inside FL receive Claude's patterns over localhost (WebSocket, OSC or HTTP) and play them as sample-accurate MIDI locked to FL's tempo? Could it drive any FL instrument (bass synth, drum sampler, Kontakt) while Daniel improvises on the KeyLab and the piano page keeps showing everything?
- **Method:** Read-only checks on this machine (installed-program list, plugin folders, FL's own `WhatsNew.rtf`, GitHub API reads), plus web research. Nothing was downloaded, installed, launched or changed.

---

## 0. Bottom line

1. **Yes, it can be done, and FL on this machine already supports every step.**
   - FL routes a plugin's MIDI output to other channels through matching **MIDI port numbers** (section 2).
   - FL fixed "VST3 MIDI not sent to other plugins" and "notes sent by CLAP plugins don't work" in the 2025 cycle. Daniel runs **FL Studio 2026 v26.1.3**, which includes both fixes.
   - VST3 and CLAP both give the plugin the tempo, the position in beats, and a per-event sample offset.
2. **"In time" comes from the design, not from the transport.** Claude should send *patterns* stamped in beats, not live note-ons. The plugin places each event at the exact sample, using FL's playhead. Changes start at the next bar. With that design, network jitter never reaches the audio (section 3).
3. **Building may not be necessary for a first test.**
   - **plugdata** (Pure Data as a VST3/CLAP plugin, one ~257 MB Windows installer) can receive network messages, read the host tempo and output MIDI. It needs no compiler, and Pd patches are plain text Claude can write.
   - **Birdhouse**, an existing OSC-to-MIDI plugin, turned out to be a poor fit. It has no Windows binary, maps each channel to one fixed note, and has no tempo scheduling (section 5).
4. **If we build our own:** JUCE 9 with CMake, VST3 first. It is the most-proven path inside FL, has an OSC module, and costs nothing for personal use under the free Starter licence or AGPLv3. Birdhouse's JUCE source is a ready-made example to learn from. Rust (nih-plug, or its community fork nice-plug) is the runner-up. Every compiled path needs the **Microsoft C++ Build Tools**, a multi-GB install that needs admin rights. That is the download to ask Daniel about (section 6).
5. **Recommended order:** plugdata test (one download) → timing drill → only then decide whether a JUCE build is worth it.

---

## 1. What is on this machine (read-only census, 2026-09-14)

| Item | Found | How checked |
|---|---|---|
| FL Studio 2026 | **26.1.3.5570**. FL Studio 2025 25.2.5 is also installed. | Uninstall registry keys |
| FL release notes | `C:\Program Files\Image-Line\FL Studio 2026\WhatsNew.rtf`, newest entry 26.1.3 (2026/07/24) | Read locally |
| Kontakt | Native Instruments Kontakt 8 **8.12.1**, `Kontakt 8.vst3` in `C:\Program Files\Common Files\VST3` | Registry + folder listing |
| Splice | Splice Bridge 5.1.1 (`SpliceBridge.vst3`), Splice INSTRUMENT 1.1.15 | Registry + folder listing |
| Other VST3 instruments | Serum2, SynthMaster3, Arturia Analog Lab V / Mini V4 / Piano V3 / Stage-73 V2, Nexus, Cymatics set, XLN Audio, Kilohearts, etc. | Folder listing |
| CLAP folder | `C:\Program Files\Common Files\CLAP` **does not exist**, so no CLAP plugins are installed | Test-Path |
| Arturia | USB MIDI Driver 1.7.0, MIDI Control Center 1.23.0 | Registry |
| Compilers / build tools | **None**: no `cl`, `msbuild`, `cmake`, `ninja`, `clang`, `gcc`, `cargo`/`rustc`/`rustup`, no Visual Studio install, no `~/.cargo` | `Get-Command`, Test-Path |
| Present | Git 2.53, GitHub CLI 2.92, Node 24.14, Python 3.11.9 + 3.14.7 | Registry |
| MIDI loopback tools | No loopMIDI, no Bome | Registry |

The practical consequence: **every compiled plugin path starts with a large toolchain download** (section 6). The plugdata path does not need one.

---

## 2. How FL routes a plugin's MIDI out (ports, versions, gotchas)

### 2.1 The port model

- A plugin is linked to another plugin (or to hardware) by **matching port numbers**. The official MIDI Out page says the chosen number does not matter and that there are 256 ports. For a VST target, you set the target wrapper's *input* port to the same number. Source: [Image-Line manual, MIDI Out plugin](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/MIDI%20Out.htm). The online manual is undated; it describes current FL.
- The Plugin Wrapper page lists **input and output MIDI port selectors** per plugin. Other wrapper settings on that page:
  - release velocity, pitch-bend range, poly aftertouch, and "All notes off";
  - on the Processing tab: *fixed size buffers* (documented as able to add latency), *threaded processing*, and *Smart disable* (stops processing when idle, which can break time-based plugins);
  - *Send loop position*.

  Source: [Image-Line manual, Plugin Wrapper](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/wrapper.htm).
- A search summary of the Image-Line manual says that selecting an output port "exposes the plugin's note output to FL Studio" so it can be recorded. Source: [Image-Line manual search result](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/wrapper.htm); I did not see the exact sentence on the fetched page. A 2025 JUCE forum thread describes the same practical routing: set a "track" number in each plugin's gear menu, then match source and destination. Source: [JUCE forum, 2025-04-14](https://forum.juce.com/t/midi-generator-plugin-im-distributing-a-vst3i-could-i-distribute-a-vst3-midi-effect-too-for-ableton-cubase-fl-studio/65814).
- **The rig this implies:** one generator plugin per role (Bass → out port 11, Drums → 12, Chords → 13). Kontakt's input port is set to 11, the drum sampler's to 12, and so on. Daniel's KeyLab keeps playing his lead instrument directly.

### 2.2 FL-specific shape of a MIDI generator

- **FL has no VST3 "MIDI effect" insert.** A MIDI generator must load as an *instrument* in the Channel Rack and route by port to the real instrument. Patcher or Plugin Buddy can combine the two in one slot. Source: [JUCE forum, 2025-04-14](https://forum.juce.com/t/midi-generator-plugin-im-distributing-a-vst3i-could-i-distribute-a-vst3-midi-effect-too-for-ableton-cubase-fl-studio/65814).
- The same thread reports **pitch-wheel messages behaving erratically** when routed between plugins in FL (2025). Keep the first version to notes and CCs only.
- **Use the VST3 build, not AU,** and turn on the MIDI-output flag. A 2020 JUCE thread traced "MIDI out doesn't record in FL" to exactly these two mistakes. Source: [JUCE forum, 2020-12](https://forum.juce.com/t/midi-output-to-process-block-but-does-not-record-in-fl-studio/43460).

### 2.3 Format support and the fixes that matter (from FL's own release notes on this machine)

FL on Windows supports VST 1/2, VST3, CLAP and Image-Line's native format. Source: [Image-Line manual, Plugin Standards](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins_supported.htm).

CLAP arrived publicly with FL Studio 2024 (announced 2024-06-27). Source: [rekkerd.org](https://rekkerd.org/image-line-launches-fl-studio-2024-incl-clap-plugin-support/).

The version mapping below is from the local `WhatsNew.rtf` (section headers mapped to items):

| FL build (date) | Item | Why it matters |
|---|---|---|
| 21.2.99 Beta 2 (2024/03/12) | 17071 "Added preliminary support for CLAP plugins" | CLAP start |
| 24.2.1 (2024/12/10) | 17397 "CLAP plugins don't receive song position and tempo information" (fixed) | Before this build, a CLAP generator could not follow tempo |
| 24.2.99 Beta 1 (2025/03/11) | 19370 "some MIDI messages in VST3 plugins aren't sent out to other plugins" (fixed) | VST3 plugin-to-plugin MIDI was lossy before this |
| 24.2.99 Beta 8 (2025/06/19) | 20064 "notes sent by CLAP plugins don't work" (fixed) | CLAP note output was broken before this |
| 25.1.1 (2025/07/15) | First release build after those betas | Both fixes ship from here (by inference from header order) |
| 25.2.1 RC1 (2025/12/03) | 21135 VST3 plugins not told about latency before/after (fixed) | Latency reporting |
| 26.1.2 (2026/07/16) | 22291 "MIDI Out: notes aren't sent when FL Studio isn't playing" (fixed) | Native MIDI Out now works while stopped |
| 26.1.x | 21845 "CLAP plugins don't call deinit", 22261 slow CLAP load | CLAP hosting is still being hardened |

**Verdict on format:** build and ship the **VST3** first. VST3 has more FL mileage, Kontakt here is VST3, and no CLAP plugins are installed yet. Add CLAP as a second target. The Birdhouse author recommends CLAP for MIDI effects "if your host supports it" ([Birdhouse manual](https://github.com/madskjeldgaard/Birdhouse/blob/main/manual/birdhouse-manual.md)), but FL's CLAP note output was only fixed in mid-2025.

**Not found (open):** whether FL delivers a generator's MIDI to the destination channel **in the same audio block**, or one block later. No source answered this. It needs a measured drill (section 7).

---

## 3. The design that makes it "in time"

### 3.1 Send patterns, not notes

If Claude sends live note-ons over the network, each note lands wherever the next audio block happens to start. That means jitter of up to one buffer, plus network time. Instead, **Claude sends a pattern**: a list of events stamped in beats, a length, a loop flag, and a launch rule. The plugin keeps the pattern in memory. On every audio block it asks FL where the playhead is, and emits the events that fall inside that block at the exact sample offset.

The plugin APIs provide exactly this:

- **VST3:** `ProcessContext` provides `tempo` (BPM), `projectTimeMusic` (position in quarter notes), `barPositionMusic`, cycle start/end, and flags such as `kPlaying` and `kTempoValid`. Source: [Steinberg VST3 ProcessContext reference](https://steinbergmedia.github.io/vst3_doc/vstinterfaces/structSteinberg_1_1Vst_1_1ProcessContext.html). Output `Event`s carry a `sampleOffset` measured from the block start. Source: [Steinberg VST3 Event reference](https://steinbergmedia.github.io/vst3_doc/vstinterfaces/structSteinberg_1_1Vst_1_1Event.html). Both are current SDK docs.
- **CLAP:** every event header's `time` is the sample offset within the buffer. The transport event carries `song_pos_beats`, `tempo` and an is-playing flag. Output events are pushed with `try_push`. Source: [free-audio/clap events.h](https://raw.githubusercontent.com/free-audio/clap/main/include/clap/events.h).
- **nih-plug:** the `MIDI_OUTPUT` config gives the plugin a note output port, and `NoteEvent` timings are sample offsets within the current buffer. Source: [nih-plug Plugin trait docs](https://nih-plug.robbertvanderhelm.nl/nih_plug/plugin/trait.Plugin.html) and [NoteEvent docs](https://nih-plug.robbertvanderhelm.nl/nih_plug/midi/enum.NoteEvent.html).
- **DPF:** `writeMidiEvent()` (with `DISTRHO_PLUGIN_WANT_MIDI_OUTPUT`) may only be called during `run()`. `getTimePosition()` provides bar/beat/tick. Source: [DPF Plugin class reference](https://distrho.github.io/DPF/classPlugin.html) and [MidiThrough example](https://github.com/DISTRHO/DPF/blob/main/examples/MidiThrough/MidiThroughExamplePlugin.cpp).

### 3.2 Launch rules (how Daniel feels the changes)

- `launch: "next_bar"` (the default): a new bass line starts on the next downbeat, the way clip launching works. Daniel never hears a half-applied change.
- `launch: "now_quantized"` with a grid (1/4, 1/8) for fills.
- When FL's transport is stopped (`kPlaying` false), the plugin has two options. It can stay silent, or free-run its own clock from `tempo` so a jam works without pressing Play. Pick one per session. Keep the generator's **Smart disable off**, since the manual warns it stops processing when idle.

### 3.3 Transport: which direction the socket goes

- **Real-time rule:** networking stays off the audio thread. Network callbacks push into a lock-free single-reader/single-writer FIFO, and the audio thread drains it. The 2024 JUCE forum advice on OSC in plugins says exactly this and cites Surge XT as a working example. It also warns that some hosts sandbox plugin networking, which is a Logic concern, not FL. Source: [JUCE forum, 2024-10](https://forum.juce.com/t/receive-osc-messages-in-a-vst-plugin/63740). JUCE's `OSCReceiver` offers a message-thread callback or a realtime callback that runs on the network thread. Source: [JUCE OSCReceiver docs](https://docs.juce.com/master/classOSCReceiver.html).
- **Option A, plugin listens on OSC/UDP** (`127.0.0.1:9101` for bass, 9102 for drums, ...). This is the simplest framework support (juce_osc, iPlug2 Extras/OSC, the Rust `rosc` crate). Costs: one port per instance, and a listening socket may trigger a firewall prompt (unverified here; the machine's firewall is on by posture).
- **Option B, plugin connects out to arsenal** (for example, it subscribes to a new `GET /api/fl/patterns?role=bass` event-stream, or a WebSocket, on the existing `127.0.0.1:8793` server). No ports are opened in FL, many instances share one address, and arsenal stays the single source of truth. That mirrors how `arsenal/pianocue.py` already serves `/api/piano/cues` as an SSE stream with replay. Cost: an HTTP/WS client inside the plugin (JUCE has `URL`/`WebInputStream`; Rust has plenty of crates).
- **Recommendation:** B for the custom plugin, because it matches the existing cue channel, needs no listening sockets and handles multiple roles cleanly. A is the only option for off-the-shelf OSC plugins such as plugdata or Birdhouse.
- Send **whole patterns idempotently**, not deltas. A lost or duplicated message then heals on the next send. OSC over UDP has no delivery guarantee.

### 3.4 Keeping the piano page in the loop

- **Plugin → arsenal heartbeat** about every 50 ms: `{bpm, ppq, bar, playing}` plus "pattern X armed / launched at bar N". With the clock and the pattern both known, the page can draw *upcoming* notes aligned with FL's time, not just notes as they sound.
- The reverse direction already exists as open source: **daw-out** (VST3/CLAP, MIDI out of a DAW to an OSC server, [github.com/gamingrobot/daw-out](https://github.com/gamingrobot/daw-out)) and **MIDI2OSC** (JUCE, [github.com/thomasgeissl/MIDI2OSC](https://github.com/thomasgeissl/MIDI2OSC)). Either could mirror what FL is actually playing to the page. Not evaluated in depth.

### 3.5 Pattern message sketch (aligned with the existing cue vocabulary)

```json
{
  "type": "pattern", "role": "bass", "id": "bass-verse-2",
  "launch": "next_bar", "loop": true, "length_beats": 16,
  "events": [ {"beat": 0.0, "note": 36, "velocity": 100, "length_beats": 0.5},
              {"beat": 1.5, "note": 43, "velocity": 88,  "length_beats": 0.25} ],
  "source": "claude", "label": "I-vi-IV-V walking root"
}
```

Other messages: `{"type":"clear","role":"drums"}`, `{"type":"mute","role":"bass","on":true}`. Note range and velocity bounds should reuse `pianocue.validate_cue`'s limits (notes 21..108 for piano; drums need 0..127, so widen for non-piano roles).

---

## 4. Framework comparison (custom build)

| | **JUCE 9** | **iPlug2** | **nih-plug / nice-plug (Rust)** | **DPF** |
|---|---|---|---|---|
| Latest activity | 9.0.2 released 2026-09-07 ([GitHub API](https://github.com/juce-framework/JUCE/releases)) | pushed 2026-09-11 ([repo](https://github.com/iPlug2/iPlug2)) | nih-plug pushed 2026-09-03, **maintenance mode**; nice-plug last commit 2026-09-11 | pushed 2026-09-13 ([repo](https://github.com/DISTRHO/DPF)) |
| Formats relevant to FL | VST3 (native). No native CLAP in the 9.0.0 headline list ([CHANGE_LIST](https://github.com/juce-framework/JUCE/blob/master/CHANGE_LIST.md)); JUCE projects add CLAP via extensions, as Birdhouse does (its 2026-05-01 commit "update clap extensions") | CLAP, VST2, VST3, AUv2/v3, AAX, WAM ([README](https://github.com/iPlug2/iPlug2)) | VST3 + CLAP ([nih-plug](https://github.com/robbert-vdh/nih-plug), [nice-plug](https://codeberg.org/BillyDM/nice-plug)) | LADSPA, DSSI, LV2, VST2, VST3, CLAP ([README](https://github.com/DISTRHO/DPF)) |
| MIDI out + transport | Yes (`producesMidi`, playhead). Proven in FL by many commercial plugins | Yes; ships an `IPlugMidiEffect` example ([tree](https://github.com/iPlug2/iPlug2/tree/master/Examples/IPlugMidiEffect)) | Yes: `MIDI_OUTPUT`, sample-offset `NoteEvent`, transport info | Yes: `writeMidiEvent`, `getTimePosition` |
| Networking built in | **juce_osc** (UDP OSC receive/send, [docs](https://docs.juce.com/master/classOSCReceiver.html)); raw sockets and URL streams | **Extras/OSC** (uses WDL jnetlib). The WebSocket server was **removed** ("WIP: Remove CivetWeb/WebSocket", 2024-08-18, per commit history), though the Extras README still lists it | None; use crates (`rosc` 0.11.4, 2026-09-02, MIT/Apache, encode/decode only, [docs.rs](https://docs.rs/rosc/latest/rosc/)) plus std UDP or a WS crate | None found in docs |
| Licence for Daniel's personal use | **Starter: free, revenue up to $20,000**; also dual-licensed **AGPLv3** ([JUCE 8 EULA](https://juce.com/legal/juce-8-licence/), [Get JUCE, JUCE 9 current](https://juce.com/get-juce/)). No splash-screen requirement found. Fine for a private plugin. | zlib-like, free for closed source ([README](https://github.com/iPlug2/iPlug2)) | ISC; nih-plug notes its VST3 **bindings** are GPLv3 ([README](https://github.com/robbert-vdh/nih-plug)). Irrelevant for private use. | ISC; some formats have extra terms ([LICENSING.md](https://github.com/DISTRHO/DPF)) |
| Maturity | Industry standard; most proven inside FL | Mature; smaller community | nih-plug frozen; nice-plug "experimental... expect some bugs" ([Codeberg](https://codeberg.org/BillyDM/nice-plug)) | Mature on Linux (Cardinal and others); least documented for Windows/FL |
| Claude-friendliness | CMake CLI build; huge corpus; **Birdhouse is a working OSC→MIDI JUCE template** (GPLv3) | Ships `.sln`/CMake per example; smaller corpus | `cargo xtask bundle <name> --release`, fully CLI; memory-safe | Makefiles/CMake; Windows toolchain not stated in README |
| Toolchain downloads | VS Build Tools (C++) + CMake (+ Ninja optional) + JUCE clone (~283 MB repo per GitHub API) | VS (C++) + iPlug2 clone + its dependency scripts (not inspected) | **rustup + Rust toolchain + MSVC v143 build tools + Windows 11 SDK** ([rustup Windows MSVC](https://rust-lang.github.io/rustup/installation/windows-msvc.html)) + framework clone | Compiler (MSVC or MinGW, unverified) + clone |

Background licence change: **Steinberg moved the VST 3 SDK to the MIT licence with 3.8.0 (October 2025)**, replacing the old GPLv3 / proprietary dual licence. Sources: [Sonicstate, 2025-10-30](https://sonicstate.com/news/2025/10/30/vst-3-now-available-under-mit-license/), [Steinberg VST3 licence page](https://steinbergmedia.github.io/vst3_dev_portal/pages/VST+3+Licensing/VST3+License.html). For a private plugin, no licence on this list blocks anything.

**Pick for a custom build:** JUCE 9, VST3 first. It has the most FL mileage, built-in OSC, CMake from the command line, and a direct example in Birdhouse. The free Starter tier or AGPLv3 both cover a private plugin. Rust (nice-plug) is second choice. It is cleaner and memory-safe, but its framework is "experimental", and it still needs the same MSVC download.

---

## 5. Existing plugins: is building unnecessary?

| Candidate | What it is | Fit for "Claude patterns → FL instruments, in time" | Verdict |
|---|---|---|---|
| **plugdata** v0.9.3-2 (2026-03-06) | Pure Data as a VST3/CLAP/LV2/AU plugin with a new GUI; bundles the ELSE and cyclone libraries; Windows installer `plugdata-Win64.msi` = 269,381,632 bytes (~257 MB, GitHub API). Plugin binary licensed AGPL-3.0 (JUCE), source GPL-3.0 ([repo](https://github.com/plugdata-team/plugdata)) | Can output MIDI to the host. Its DAW guide has an **FL Studio section** saying to set matching MIDI out/in ports in the wrapper, and covers syncing to host tempo ([DAW setup](https://plugdata.org/docs/book/DAWIntegration.html)). Network objects such as `[netreceive]` exist but only run while the DAW sends audio blocks (developer note, 2022-08-04, [discussion #144](https://github.com/plugdata-team/plugdata/discussions/144)); FL's engine normally runs continuously. Pd patches are plain text Claude can write and diff. Timing resolution is presumably Pd's control-block granularity; not verified here. | **Best no-compile test.** One download. Proves port routing, host-tempo lock and localhost receive before we commit to a toolchain. |
| **Birdhouse** v0.1.2 (release 2024-04-10; code pushed 2026-05-01) | JUCE OSC→MIDI bridge, VST3/CLAP/standalone, GPL-3.0 ([repo](https://github.com/madskjeldgaard/Birdhouse), [manual](https://github.com/madskjeldgaard/Birdhouse/blob/main/manual/birdhouse-manual.md)) | 8 channels per instance, one shared UDP port. Each channel has a fixed OSC path, a **fixed note or CC number**, and in/out scaling. NOTE mode fires note-on when the value rises above InMin, with the value used as velocity. **No tempo scheduling:** notes fire when the OSC arrives. Tested in Reaper, Bitwig and Ardour; **FL untested**. The **only release asset is a macOS DMG**. CI builds Windows, but Actions artifacts need a GitHub login to download. | Poor fit as-is. It works for an 8-pad drum kit if Claude does all the timing outside, but not for bass lines or chords. Its value is as **template source code** for a JUCE build. |
| **Plogue Bidule** | Modular host that runs standalone or as a VST2/VST3/AU plugin, with an OSC server ([product](https://www.plogue.com/products/bidule.html)) | The OSC server controls **parameters only**, not notes; addresses are built from module and parameter names ([manual ch. 11.2](https://www.plogue.com/bidule/help/ch11s02.html)). Paid. | No. |
| **Blue Cat's Plug'n Script** V3.61 (2026-04-29) | Scriptable plugin (AngelScript, or native C/C++ binaries), VST/VST3/AAX/AU, MIDI capable; **$99**; demo bypasses briefly every minute and exported plugins stop after 10 min ([product](https://www.bluecataudio.com/Products/Product_PlugNScript/)) | Networking is not documented. Sockets would require a native compiled script, which means the same MSVC toolchain anyway. | No, unless Daniel already owns it. |
| **Kushview Element** 1.1.0 | Open-source modular host, standalone or as a plugin; Lua MIDI scripting; MIDI in/out ([kushview.net](https://kushview.net/article/element-v1-1-0/), [GitHub](https://github.com/kushview/element)) | No OSC or network input found in the sources checked. | Open question; not a proven fit. |
| **Surge XT** 1.3.x | Free synth with a full OSC implementation since 1.3.0; the changelog lists MIDI-style `/pbend`, `/cc`, etc. ([changelog](https://surge-synthesizer.github.io/changelog/)). Search results say `/mnote` starts a note, but I did not verify that against the in-app OSC spec. | Could play *its own* bass sound from Claude over OSC, but cannot drive Kontakt or other instruments. | Niche: a quick bass-only demo at most. |
| **MIDI Agent** | LLM MIDI generator plugin (VST3/AU/AAX), $49; you drag its output into the piano roll ([site](https://www.midiagent.com/ai-midi-generator-for-fl-studio)) | No external control, and not real-time. | No. |
| **OscVstBridge** | Old VST OSC→MIDI/parameter bridge ([SourceForge](https://sourceforge.net/projects/oscvstbridge/)) | Old VST2-era project; not checked for 64-bit or VST3. | Not recommended. |

---

## 6. Effort and downloads per path (each download needs Daniel's OK)

Effort is measured in focused Claude working sessions and assumes Daniel does the one-time FL clicks (load the plugin, set ports).

| Path | Downloads (source; size) | Effort to first grooving bass+drums | Risks |
|---|---|---|---|
| **P1. plugdata test** | `plugdata-Win64.msi` from github.com/plugdata-team/plugdata releases (~257 MB). Nothing else. | **~1 session:** Pd patch (receive → pattern store → playhead-driven emitter), arsenal sender, FL port setup, timing drill | Pd GUI weight per instance; `[netreceive]` behaviour inside FL unverified; pattern logic in Pd is clumsy past simple loops |
| **P2. JUCE 9 plugin ("jam-plug")** | **Visual Studio Build Tools** (C++ workload: MSVC + Windows SDK). Microsoft says Build Tools need 2.3 GB–60 GB depending on components, and admin rights to install ([VS 2026 system requirements, updated 2026-04-01](https://learn.microsoft.com/en-us/visualstudio/releases/2026/vs-system-requirements)). **CMake** (also available as a VS component). JUCE source (~283 MB repo) via git. | **~3–5 sessions:** skeleton + VST3 build (1), SSE/OSC client + FIFO + pattern scheduler (1–2), FL routing + drill + page heartbeat (1), hardening (1) | First-time toolchain setup; unsigned DLL loaded into FL, so a plugin crash can take FL down (FL's bridging option is a mitigation to verify); CLAP as a second target adds ~1 session |
| **P3. Rust nice-plug / nih-plug** | rustup + stable toolchain, **plus the same MSVC v143 build tools + Windows 11 SDK** ([rustup docs](https://rust-lang.github.io/rustup/installation/windows-msvc.html)), plus framework clone from Codeberg/GitHub | **~3–5 sessions**, similar split | nice-plug self-describes as experimental; nih-plug in maintenance; fewer FL-specific reports |
| **P4. iPlug2** | Visual Studio C++ + iPlug2 clone + dependency scripts (not inspected) | ~4–6 sessions | WebSocket removed in 2024; smaller community; less FL evidence |
| **P5. DPF** | Compiler (MSVC or MinGW, unverified) + clone | ~5+ sessions | Windows build path not documented in README; least FL evidence |

**Shared truth:** every compiled path (P2–P5) needs the MSVC build tools. That is the single "yes" to get from Daniel. Machine posture (no AV, no Windows Update) means installers should come only from the official Microsoft and GitHub sources above.

---

## 7. Drills before calling anything done (per drill doctrine)

1. **Port routing drill:** a generator on out-port N with Kontakt on in-port N. Kontakt sounds, the FL piano roll's "burn notes" shows the notes (FL 20.7 added burning a channel's note output to its piano roll, per `WhatsNew.rtf`), and the piano page shows them.
2. **Same-block or one-block-late drill:** open question from 2.3. Put a generator hit on beat 1 into a click-like instrument, record FL's output, and measure the offset against a grid-placed audio click at several buffer sizes. If it is exactly one buffer, compensate by scheduling one block early.
3. **Tempo-change drill:** automate BPM mid-pattern; events must stay on the grid.
4. **Stop/loop drill:** pattern-loop wrap and transport stop produce no stuck notes (send note-offs for any sounding notes when playback stops or the position jumps).
5. **Two-instance drill:** bass and drums at once, separate ports, no cross-talk; the arsenal heartbeat shows both roles.

---

## 8. Open questions

- Does FL deliver plugin MIDI output to the destination channel in the same block? No source found; needs drill 2.
- Does a VST3 generator loaded in FL get `ProcessContext` with `kProjectTimeMusicValid` while the transport is stopped? VST3 3.7+ requires plugins to declare `IProcessContextRequirements` ([Steinberg dev portal](https://steinbergmedia.github.io/vst3_dev_portal/pages/Technical+Documentation/Change+History/3.7.0/IProcessContextRequirements.html)); FL's behaviour is untested.
- Does FL filter by MIDI *channel* on the receiving wrapper, or does each port carry all 16 channels to one instrument? That decides whether one plugin instance could drive several instruments.
- Does a plugin that opens a listening UDP port in FL trigger a Windows Firewall prompt on this machine? (This is why section 3.3 prefers the outbound option B.)
- plugdata inside FL: do `[netreceive]` and the host playhead objects behave as documented in FL 26.1.3?
