# Virtual MIDI and timing on Windows 11 (FL jam bridge lane)

- Date: 2026-09-14 (research done late at night, read-only on this machine)
- Author: claude (research subagent, lane "virtual MIDI and sync")
- Status: in-flight research. Nothing was installed, downloaded, created or changed.
- Question: how can Claude (Python and/or the piano page in Chrome) send bass, drums and chords into FL Studio in time while
  Daniel improvises on the KeyLab 88 mk3, and how does everything follow FL's tempo and bar position?

## TL;DR

1. **This machine already has the new Windows MIDI stack running.** Windows 11 25H2 build 26200.9168; `midisrv` is running;
   the loopback transport and the app-to-app ("virtual device") transport are both installed and enabled. What is missing is
   the separate **Windows MIDI Services SDK Runtime and Tools** download. It contains the MIDI Settings app and the `midi`
   console, which are the tools that create loopback ports. No user loopback ports exist yet. Installing that download needs
   Daniel's OK.
2. **The "Service Test Loopback" Chrome cannot see is a diagnostics endpoint.** Microsoft says diagnostics endpoints are
   only for apps that use the new SDK. **Loopback pairs you create yourself are different.** Microsoft says they work with
   WinMM apps, WinRT MIDI 1.0 apps and web sites. So Chrome Web MIDI and FL Studio should both see a loopback made in MIDI
   Settings. This is documented but not yet tested here.
3. **Choosing between the in-box loopback and loopMIDI.** Prefer Microsoft's in-box loopback: it survives reboots when made
   in MIDI Settings, needs no third-party driver, and every port can be opened by several apps at once. loopMIDI still
   works: the "ports vanish until the service restarts" bug was fixed in a phased update that began 30 April 2026. But
   loopMIDI's own page still only lists Windows 7 to 10, and it runs through the old compatibility layer.
4. **Latency is set by FL's audio buffer, not by the virtual port.** Microsoft says jitter through the service is in the
   low microseconds. FL's audio buffer here is 256 samples (about 5-6 ms), and FL's manual says what you hear is at least
   that late. The real jitter risk is *who schedules the notes*:
   - JavaScript `setTimeout` can be tens of ms late.
   - Hidden Chrome tabs get throttled to one timer check per second, or per minute.
   - Python 3.11 on Windows sleeps with 100 ns resolution.

   **So the sequencer should live in Python, and the piano page should only display.**
5. **Tempo sync: make FL the master.** Ableton Link is not in FL Studio: Image-Line said only that they are "aware" of the
   request (Jan 2025), and forum requests carry on to May 2026. MTC gives time, not bars. The recommended design:
   - FL sends MIDI clock (24 ticks per beat, plus start/stop) out a loopback port. Python counts ticks for tempo and phase.
   - Optionally, a small FL controller script sends FL's exact song position and tempo about every 20 ms as a sysex message
     through the same loopback. That corrects the bar number.
   - Python schedules the backing notes into FL on a second loopback, and pushes tempo, bar and notes to the page over SSE.

## 1. What this machine has today (local, read-only evidence, 2026-09-14)

| Check | Result |
|---|---|
| OS | Windows 11 Pro 25H2, build 26200, update revision 9168 |
| `midisrv` (Windows MIDI Service) | Running (start type Manual, so it starts when an app needs it) |
| `HKLM\SOFTWARE\Microsoft\Windows MIDI Services\Transport Plugins` | `Midi2KSTransport`, `Midi2KSAggregateTransport`, `Midi2LoopbackMidiTransport` (Enabled=1), `Midi2VirtualMidiTransport` (Enabled=1) |
| `C:\Windows\System32\Midi2.*.dll` | Loopback, VirtualMidi, Scheduler transform, Diagnostics and KS transports present; files dated 2026-08-12 (August cumulative update) |
| Legacy WinMM driver list (`Drivers32`) | `midi1 = wdmaud2.drv`, `MidisrvTransferComplete = 1`, so old WinMM apps are routed through the new service |
| Software devices | "MIDI 2.0 Loop Devices", "MIDI 2.0 Virtual Devices", "MIDI 2.0 Service Tests" (the diagnostics loopbacks), "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW" endpoints |
| SDK Runtime and Tools | **Not installed**: no `C:\Program Files\Windows MIDI Services`, no `midi.exe`, no MIDI app package |
| Loopback config file | None found under `%ProgramData%\Microsoft\MIDI`, so **no user loopbacks exist** |
| loopMIDI / teVirtualMIDI / rtpMIDI | Not installed |
| FL Studio | FL Studio 2026 **26.1.3.5570** and FL Studio 2025 25.2.5 installed. Latest public release is 2026.1.6 (7 Sept 2026) |
| FL 26 MIDI inputs (`HKCU\Software\Image-Line\FL Studio 26\Devices`) | "KeyLab 88 mk3 MIDI" uses port 0 with script "KeyLab mk3 Arturia dev"; "KeyLab 88 mk3 DAW" uses port 236 with script "KeyLab mk3". FL has **never** recorded a loopback, loopMIDI or "Service Test" device |
| FL 26 MIDI outputs | Only "MIDIOUT2 (FLkey MIDI)" has `Sync = 1` (send master sync). Nothing is sent to any virtual port |
| FL ASIO (`HKCU\Software\Image-Line\ASIO`) | `bufferSize = 256`. The sample rate was not read; 256 samples is 5.3 ms at 48 kHz or 5.8 ms at 44.1 kHz. Which audio driver FL actually uses (FL ASIO or Focusrite) was not confirmed |
| Python | 3.11.9 pinned (3.14 also present). **mido / python-rtmidi / aalink not installed** |
| Other MIDI software | Arturia MIDI Control Center 1.23 and Arturia USB MIDI Driver 1.7; Kontakt 8.12.1; Splice Bridge 5.1.1; Splice INSTRUMENT 1.1.15 |

The FL device list is the best local explanation for tonight's Chrome finding. The only virtual endpoints on the box are the
built-in diagnostics loopbacks ("MIDI 2.0 Service Tests"), and Microsoft documents those as SDK-only (section 2.3). No
user-created loopback exists, so neither Chrome nor FL has anything app-to-app to see.

## 2. Windows MIDI Services status (2025-2026)

### 2.1 What shipped and when
- Windows MIDI Services began rolling out to retail Windows 11 in **February 2026**. Microsoft's announcement lists:
  - every MIDI 1.0 port and MIDI 2.0 endpoint can be opened by several apps at once;
  - built-in loopback;
  - app-to-app MIDI;
  - timestamps "accurate to under a microsecond".

  The SDK Runtime, Tools, MIDI Console and MIDI Settings app ship **separately**, through GitHub and WinGet
  (`Microsoft.WindowsMIDIServicesSDK`).
  Source: Windows Experience Blog, 2026-02-17 — https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/
- Microsoft's project home page says the in-box service is on retail Windows 11 **24H2, 25H2 and 26H1** with updates enabled.
  The old WinMM and WinRT MIDI 1.0 APIs "have been repointed to the new Windows Service". Loopbacks are set up "via dedicated
  setup tool".
  Source (undated live page, read 2026-09-14): https://microsoft.github.io/MIDI/
- The SDK Runtime and Tools download page lists version **1.0.14-rc.1.209** (a release candidate, dated 5 Dec 2025 or
  later). It needs admin rights to install and includes MIDI Settings, MIDI Console, PowerShell 7 cmdlets and diagnostics
  tools. It also mentions Developer Mode, but only for *preview* transport plugins.
  Source: https://microsoft.github.io/MIDI/get-latest/
- In the RtMidi pull request (below), Microsoft's Pete Brown said the out-of-band SDK will stop being offered after
  **November 2026**, as the API moves in-box to Windows 11 25H2. This came from a summary of that PR thread and should be
  confirmed before planning around the date.
  Source: https://github.com/thestk/rtmidi/pull/382
- The GitHub releases page mostly shows older 2024 developer previews. Use the get-latest page above for the current build.
  Source: https://github.com/microsoft/MIDI/releases

### 2.2 Loopback endpoints (the loopMIDI replacement)
- A loopback is two endpoints wired to each other, A and B: whatever goes out on A comes in on B, and the other way round.
  There is "no practical limit" on the number of pairs.
  Source: https://microsoft.github.io/MIDI/kb/virtual-loopback/
- There are two ways to create them, and both need the SDK Runtime and Tools download:
  - **MIDI Settings app**: the pair is saved in the service config, so it **survives service restarts and reboots**.
  - **MIDI Console**, e.g. `midi loopback create --name-a "..." --name-b "..."`: the pair only lasts until the service
    restarts or the PC reboots.

  Microsoft says loopbacks work with "desktop apps, web sites, apps using WinMM MIDI 1.0 WinRT MIDI 1.0" and the new SDK.
  Source: https://microsoft.github.io/MIDI/kb/how-to-create-loopback-endpoints-using-tools/
- Hand-editing the config file is described as **not supported**. (It would also be a settings change this lane may not
  make.) Source: https://microsoft.github.io/MIDI/kb/virtual-loopback/
- Pete Brown (Microsoft) on the Steinberg forum, 28 Feb 2026: you can give a new loopback the **same name as an old
  loopMIDI port**, and older apps keep working, because WinMM apps identify ports by name. The new loopbacks also run on
  arm64.
  Source: https://forums.steinberg.net/t/loopmidi-loopbe-etc-virtual-ports-replacement-for-windows/1025292/3
- A third-party help page (SideshowFX, updated 13 Apr 2026) shows the tool flow: MIDI Settings, then "MIDI 1.0 Loopback
  Endpoints", then create a named port. That guide predates the April fixes and also installed a separate Basic Loopback
  plugin plus Developer Mode. On current retail builds the loopback transport is already in-box (this machine has
  `Midi2.LoopbackMidiTransport.dll`), so those extra steps are probably unnecessary. **Confirm before touching Developer
  Mode.**
  Source: https://sideshowfx.kb.help/windows-midi-interim-solution-loopmidi-failure/

### 2.3 Why Chrome cannot see "Service Test Loopback"
- Microsoft: diagnostics endpoints "are available only to applications using the Windows MIDI Services SDK and service".
  Chrome and FL use the old APIs, so they will never list them. This explains tonight's finding exactly.
  Source: https://microsoft.github.io/MIDI/kb/diagnostic-endpoints/

### 2.4 App-to-app "virtual device" endpoints
- The new SDK lets an app publish itself as a MIDI 2.0 device. The endpoints live only while that app runs. Microsoft says
  the old WinMM and WinRT MIDI 1.0 APIs "cannot support" *creating* such devices.
  Source: https://microsoft.github.io/MIDI/overview/
- So for Claude this would need a small native or .NET helper using the SDK. There is no Python or browser binding for it,
  and the RtMidi backend for the new stack is still a draft (section 4.2). Treat it as a future option. **Loopbacks are the
  practical path now.**

### 2.5 Can Chrome and FL both see a loopback?
- **FL Studio:** FL uses the old WinMM API (its registry device names such as "MIDIIN2 (FLkey MIDI)" are classic WinMM
  names). Microsoft says every WinMM app sees loopbacks without changes. Confidence is high from the documentation; there
  was no test on this machine.
- **Chrome:** Chromium's Windows MIDI code uses the old WinMM calls (`midiOutShortMsg`, `midiInOpen`). It also contains a
  WinRT alternative behind the `kMidiManagerWinrt` feature flag.
  Source: https://chromium.googlesource.com/chromium/src/media/midi/+/refs/heads/master/midi_manager_win.cc
  - A third-party README says Chromium on Windows "uses the WinRT MIDI 1.0 API, also replumbed through WMS", and that a
    port which appears after the browser started only shows up after a tab refresh.
    Source: https://github.com/mayerwin/Perfect-Bluetooth-MIDI-For-Windows
  - Whether Chrome uses WinMM or WinRT by default is **unresolved**. Either way both APIs go through the service, and
    Microsoft's Feb 2026 blog says "WebMIDI pages in the browser can work with your loopback endpoints".
  - Chrome has asked permission for *all* Web MIDI use since Chrome 124 (gradual rollout, 2024). Web MIDI needs a secure
    context, and localhost / 127.0.0.1 counts as one.
    Source: https://developer.chrome.com/blog/web-midi-permission-prompt
- **Startup caveat:** apps usually list MIDI ports only when they start. Create the loopbacks *before* launching FL and
  before loading the page. Otherwise use FL's device refresh or reload the tab. Forum reports say FL's "send master sync"
  can stop working after a device refresh, so prefer permanent loopbacks made in MIDI Settings, then restart FL.
  Source: https://forum.image-line.com/viewtopic.php?t=196992

### 2.6 Known issues relevant to us
Microsoft's known-issues post (last updated 30 Apr 2026) lists these as fixed in a 30-day staged rollout starting 30 April:
- loopMIDI, loopBE, virtualMIDI, rtpMIDI and NI Service ports disappearing intermittently;
- WinRT MIDI 1.0 timestamps landing "in the future", so no messages were received;
- apps opening the wrong one of several identical devices.

It also warns against uninstalling updates.
Source: https://devblogs.microsoft.com/windows-music-dev/windows-midi-services-rollout-known-issues-and-workarounds/

This machine's MIDI binaries are dated 2026-08-12, well after that rollout window, so the fixes should already be present.
That is inferred from file dates, not verified against a KB number.

## 3. loopMIDI / teVirtualMIDI status

- loopMIDI's page lists version **1.0.16.27** and support for "Windows 7 up to Windows 10"; its copyright line reads 2022.
  Ports exist only while the app runs and belong to one user. It needs the virtualMIDI driver.
  Source: https://www.tobias-erichsen.de/software/loopmidi.html (read 2026-09-14)
- Microsoft GitHub issue #835 (opened 30 Jan 2026): ports created in loopMIDI did not appear in the new service until the
  service restarted. Suspected cause: loopMIDI sends a device-update event rather than a device-arrival event. The issue is
  closed and marked "fixed-windows-release-april2026". Source: https://github.com/microsoft/MIDI/issues/835
- Flapi, a project for remote-controlling FL over MIDI, needed loopMIDI on Windows for its two ports. It is now marked
  unmaintained. Source: https://github.com/MiguelGuthridge/Flapi/blob/main/README.md
- **Verdict:** loopMIDI should work again on current 25H2, but it is a third-party driver sitting on a compatibility layer,
  its site no longer lists Windows 11, and its ports vanish when the app closes. The in-box loopback does the same job with
  fewer moving parts and survives reboots. **Both need a download, so Daniel decides.** Recommendation: Microsoft's SDK
  Runtime and Tools (for MIDI Settings), then two permanent loopbacks.

## 4. Latency and jitter: browser or Python to FL through a virtual port

### 4.1 Where the time goes (one note from Claude to sound)

| Stage | Expected | Evidence |
|---|---|---|
| Scheduler wake-up (JavaScript) | Can be **tens of ms late** on the main thread | web.dev, "A tale of two clocks" (Chris Wilson, 2013, still the standard reference): https://web.dev/articles/audio-scheduling |
| Scheduler wake-up (hidden Chrome tab) | Timers checked **once per second**; after 5 min hidden, **once per minute**. Pages playing audible sound are exempt; silent audio does not count | Chrome for Developers, Chrome 88 (2021-01-18): https://developer.chrome.com/blog/timer-throttling-in-chrome-88 |
| Web MIDI `send(data, timestamp)` | The browser queues the message for a time measured on the `performance.now()` clock | MDN: https://developer.mozilla.org/en-US/docs/Web/API/MIDIOutput/send |
| How Chrome releases a timestamped message on Windows | A delayed task works out the wait from the timestamp. Its real precision depends on Windows timer resolution (historically 1 ms to 15.6 ms). **Not measured for current Chrome** | Chromium source (link in 2.5); Windows timer background: https://humanwhocodes.com/blog/2011/12/14/timer-resolution-in-browsers/ |
| Scheduler wake-up (Python 3.11) | `time.sleep()` uses a high-resolution timer on Windows 8.1+, with 100 ns resolution (was 1 ms before 3.11) | CPython issue 45429: https://github.com/python/cpython/issues/89592 |
| Windows MIDI service hop (loopback) | Jitter "in the low microsecond range" (Microsoft's claim; varies by transport). Microsoft has not published loopback-specific numbers; GitHub issue #56 only aims to be "as good or better than WinMM" | https://microsoft.github.io/MIDI/ and https://github.com/microsoft/MIDI/issues/56 |
| FL Studio input to audio out | At least the audio buffer. FL's manual: the delay between playing a MIDI keyboard and hearing it is "at least equal to this setting". Here that is 256 samples, about 5.3-5.8 ms plus driver/converter latency | https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_audio.htm |
| FL live-MIDI timing | FL 2026.1.6 (7 Sep 2026) claims much less jitter when recording incoming MIDI. Daniel is on 26.1.3 | https://forum.image-line.com/viewtopic.php?t=342331 |

**Perception budget:** studies cited by Expressiveness (2012) put noticeable jitter at about **1-5 ms, weighted around
2-3 ms**. A steady delay is easy to adapt to; uneven timing is what bothers a player.
Source: https://expressiveness.org/2012/12/04/midi-jitter

**What to expect:**
- **Python sequencer, loopback, FL at a 256-sample buffer:** a steady delay of about 6-10 ms from output to ear. Jitter is
  probably a few ms at most, and much of that is FL rounding events to buffer boundaries. That is comfortable for playing
  along. (This is an inference from the figures above; there is no bench measurement yet.)
- **Browser sequencer using `setTimeout` with no lookahead:** audible slop, and a hidden tab falls apart. If the browser
  must schedule, schedule ahead: wake every ~25 ms, queue anything due in the next ~100 ms with `send(data, timestamp)`
  (web.dev pattern), and keep the tab visible or playing audible sound.

**Drill needed before trusting any of this:** send clicks through the loopback and record FL's output against its own
metronome. Measure the average offset and the spread. This repo's drill doctrine requires a dated receipt.

### 4.2 Python libraries
- **python-rtmidi 1.5.8** (20 Nov 2023) has wheels for Python 3.8-3.12 on Windows x64 and uses WinMM. It **cannot create
  virtual ports on Windows**; it only opens existing ones, such as the loopback. Not installed here.
  Source: https://pypi.org/project/python-rtmidi/
- The RtMidi backend for the new Windows MIDI stack (PR #382) is still a **draft**, MIDI 1.0 only, off by default at build
  time, and falls back to WinMM. Source: https://github.com/thestk/rtmidi/pull/382
- `mido` would run on top of python-rtmidi. Installing any of these needs Daniel's OK.
- WinMM identifies ports by *name*, so pick stable loopback names and match on them.

### 4.3 The piano page as a listener
Every port is multi-client under the new service (Feb 2026 blog). So the piano page can open the **same** loopback FL is
listening on and draw Claude's backing notes exactly as FL receives them. The page stays a pure viewer, fed by the port
(or by the SSE cue channel), and does no timing-critical work.

## 5. Tempo and position sync options

### 5.1 FL as MIDI clock master (recommended backbone)
- FL's MIDI Settings let each output port send master sync. The manual says "MIDI clock is normally used", covering
  start, stop and pause. The global sync option in the Options menu must also be on. Output ports are numbered 0-255.
  Source: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_midi.htm
- FL has offered MTC as a sync type (a 2017 thread on FL 12.5 used "MTC 25 fps"), with unreliable results for that user.
  MTC carries clock time, not bars and beats, so it is a poor fit for musical backing.
  Source: https://forum.image-line.com/viewtopic.php?t=178360
- **Reported problems with FL's clock output** (older Image-Line forum threads, plus one from Sept 2025):
  - jitter with USB hardware;
  - drift against hardware sequencers;
  - sync stopping after a device refresh;
  - a Sept 2025 case (FL 25.1.3) where unstable sync to a hardware sequencer was "greatly improved" by changing FL's audio
    settings, which suggests clock output is tied to audio buffer timing.

  Sources: https://forum.image-line.com/viewtopic.php?t=336310 , https://forum.image-line.com/viewtopic.php?t=195310 ,
  https://forum.image-line.com/viewtopic.php?t=190501
- **What Python does with the clock:**
  - Read 0xF8 ticks (24 per quarter note) and 0xFA start / 0xFB continue / 0xFC stop.
  - Smooth BPM over 24-96 ticks, so FL's clock jitter never reaches the backing.
  - Count ticks from Start to get beat and bar.

  MIDI clock has no position of its own, and sending a Song Position Pointer is the standard way to say where playback is.
  Whether FL sends one when you start mid-song or loop is **unverified** (see open questions).
  SPP background: https://en.wikipedia.org/wiki/MIDI_beat_clock and https://www.sweetwater.com/insync/song-position-pointer-spp-2/

### 5.2 FL controller script as a position beacon (recommended add-on)
FL's Python controller scripting can read the transport directly:
- `transport.getSongPos(mode)` returns position as a fraction, ms, seconds, absolute ticks, or bars / steps / ticks;
- `transport.isPlaying()`, `transport.getLoopMode()` (pattern or song);
- `start`, `stop`, `setSongPos`;
- `mixer.getCurrentTempo()`.

The script is notified through `OnIdle` ("roughly once every 20ms") and `OnUpdateBeatIndicator` (bar / beat / off). It can
send a sysex message out the linked output port with `device.midiOutSysex`; FL ignores sysex that lacks the F0 start and F7
end bytes.
Sources: https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/transport/ ,
https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/callbacks/ ,
https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/device/device/ ,
https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/midi_scripting.htm

- **Design:** a script named `device_ClaudeBridge.py`, assigned to the loopback's *input* port, with the output port set to
  the same number. On each beat indicator (and at most every ~20 ms while playing) it sends a small sysex packet: song
  ticks, bar, step, BPM, play state, loop mode.
  - Python uses this for the **absolute bar number and loop jumps**, and the clock for smooth phase between packets.
  - The page gets both over SSE.
- **Two-way control:** Python can send sysex commands back (start / stop / jump to bar), which the script runs via
  `transport.*`. This is the same idea as Flapi. The script can also play notes on a given channel with
  `channels.midiNoteOn(index, note, velocity)`.
  Source: https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/notes/
  For plain note playback it is simpler to set each FL channel's MIDI input port to match the backing loopback.
- **Limits:**
  - FL's script interpreter is a cut-down Python. A community guide says it does not guarantee standard-library parity and
    blocks code that could change the PC, so **plan on no sockets or files; MIDI is the only way out**. Medium confidence;
    Image-Line's own manual does not list the Python version or which stdlib modules exist.
    Source: https://flmidi-101.readthedocs.io/en/latest/scripting/fl_midi_api.html
  - `OnIdle` must stay cheap, or it delays FL's handling of MIDI (callbacks page).
  - Each port takes one controller script, so keep this bridge script on its own loopback port and leave the KeyLab ports
    (0 and 236) alone.

### 5.3 FL as clock slave (Python or Claude as master)
- Since FL 21.1 (2023), FL can follow an external MIDI clock. You pick the source device, and a millisecond offset moves
  FL's response earlier (positive) or later (negative). The manual warns that clock wobble can make tempo-based effects
  misbehave.
  Source: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_midi.htm
- Reported limitation (Aug 2023): FL's transport **always starts from the beginning of its timeline**, wherever the master
  starts. Users asked for MTC or SPP support to fix this.
  Source: https://forum.image-line.com/viewtopic.php?t=310469
- **Verdict:** possible, but it hands FL's timeline to Claude, and FL's own tempo automation stops mattering. Keep it as a
  mode for "Claude runs the jam at a fixed tempo", not the default.

### 5.4 Ableton Link
- **Not supported in FL Studio as of this research.**
  - Image-Line staff: "we're aware of the feature request" (2 Jan 2025).
  - Site admin: "No news" (22 Aug 2025).
  - User requests continue to 31 May 2026.

  Source: https://forum.image-line.com/viewtopic.php?t=308744
- The FL Studio 2026.x release notes (through 2026.1.6, 7 Sep 2026) mention no Link. Ableton's Link product list does not
  include FL Studio.
  Sources: https://forum.image-line.com/viewtopic.php?t=342331 , https://www.ableton.com/en/link/products/
- Python can still join Link: **aalink 0.2.3** (3 Jul 2026, asyncio, Windows wheels, GPLv3+). Its `await link.sync(beat)`
  resumes within a few milliseconds of the target beat.
  Source: https://pypi.org/project/aalink/
  Carabiner is a small helper that exposes Link to other programs over local TCP; its prebuilt binaries are macOS-only.
  Source: https://github.com/Deep-Symmetry/carabiner/blob/main/README.md
- **Verdict:** Link only matters if a Link-native app (phone app, Bitwig, Ableton) joins later. Then a Python helper
  (aalink) would bridge Link to MIDI clock into FL's external sync, with the same "starts at the timeline beginning"
  limitation. It is not needed for one PC with FL alone.

### 5.5 Recommended topology (proposal, not built)

```
KeyLab 88 mk3 --USB--> FL Studio (port 0, Arturia script) --> Kontakt / FL channels --> audio
      \--(multi-client)--> piano page (Web MIDI in)

FL "Send master sync" --> loopback "FL Clock" A->B -----------> Python jam engine (tempo/phase)
FL script device_ClaudeBridge.py --sysex--> "FL Bridge" A->B --> Python (bar, ticks, BPM, loop)
Python --commands sysex--> "FL Bridge" B->A --> FL script (start/stop/jump)
Python sequencer --notes ch1 bass / ch10 drums / ch2 chords--> loopback "Claude Backing" A->B --> FL channels (MIDI input port N)
      \--(multi-client listen on Claude Backing B)--> piano page draws backing notes
Python --SSE {bpm, bar, beat, playing, upcoming notes}--> piano page (arsenal/web/piano.js on 127.0.0.1:8793)
```

- FL Clock and FL Bridge could share one loopback pair if port numbering allows. Keep Claude Backing separate so a crashed
  script never blocks notes.
- Scheduling rule: Python plans a bar ahead from the smoothed tempo and phase. It sends each note on time using
  high-resolution sleep plus a short busy-wait, and corrects the bar from beacon packets at bar boundaries.
- The page never schedules audio-critical events. If the built-in browser voice is used as a fallback, it should also
  schedule ahead.

## 6. Open questions (need a drill or a primary source)
1. Does current Chrome on Windows use WinMM or WinRT by default (is `kMidiManagerWinrt` on)? What real timing precision
   does `send(data, timestamp)` achieve through the loopback? Measure it.
2. Does FL send a Song Position Pointer when playback starts mid-song or loops in pattern mode, or only Start at the
   timeline beginning? Capture FL's clock output on the loopback to find out.
3. Does FL 26 list loopback pairs under their MIDI Settings names, and does "Send master sync" survive a device refresh on
   the new stack?
4. Which audio driver and sample rate does FL actually use (FL ASIO at 256 samples, or Focusrite ASIO)? This sets the
   minimum delay.
5. Is the MIDI Settings app still needed to create loopbacks after the SDK moves in-box (after Nov 2026), and does the
   standalone installer stop being offered?
6. Which Python version and standard-library modules does FL's embedded interpreter have in 2026.x? This decides whether
   the bridge script can only talk over MIDI.

## 7. What needs Daniel's OK (nothing done)
1. Download and install the **Windows MIDI Services SDK Runtime and Tools** (Microsoft, GitHub or WinGet). This is an
   admin install; version 1.0.14-rc.1.209 at time of reading. Size was not checked; state it when asking.
2. Create two or three **permanent loopback pairs** in MIDI Settings, named e.g. "Claude Backing", "FL Clock",
   "FL Bridge". This is a persistent configuration change.
3. `pip install python-rtmidi mido` into the 3.11 environment. Optionally `aalink`.
4. In FL: set port numbers for the loopbacks, turn on Send master sync for "FL Clock", and drop
   `device_ClaudeBridge.py` into `Documents\Image-Line\FL Studio\Settings\Hardware\ClaudeBridge\`. These are FL settings
   changes, so Daniel does them or approves them.
5. Consider updating FL to 2026.1.6 for the improved MIDI input timing. That is a download.
