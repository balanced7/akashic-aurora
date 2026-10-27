# KeyLab mk3 developer guidance, the hang's likely cause, and a doctor design (2026-10-27)

Workflow run wf_03a6ad2d-86e (task wqtpg4zgq), started after the live hang study (keylab-hang-study-2026-10-26.md). Daniel's ask, verbatim: "can you read the guide as well as any developer guidance that they may have". Four read-only lanes (Arturia's official material, the DAW integrations as de facto documentation, Windows MIDI Services, community hang reports), then one synthesis: a guide for Daniel and Rill. Verbatim; local paths shortened. Nothing was changed on the device, the repo or the system by this run; one lane's web tool saved two Arturia PDFs into the session's tool-results folder by accident (listed in the guide's section 5.6).

Vandor's read: the guide corrects the hang study -- the hang began before about 21:18 on 2026-10-26, before any of that evening's probes, so none of them caused it; the leading suspects are the USB link (Arturia's driver or the KeyLab's USB interface firmware) as the place it stuck, and days of constant SysEx traffic as the trigger. It also finds real defects in our own code: the burst governor is per process, not per port; MidiIn's lpData type truncates replies at the first 00 byte and never re-queues buffers; send_sysex's timeout is silent. None of these fixes is applied yet.

---

## The guide (verbatim)

# Reading the KeyLab 88 mk3: layers, hangs, recovery and a doctor (2026-10-27)

This is for Daniel and Rill. It draws on:
- the hang study (`research/reviewed/keylab-liberation-2026-10-22/keylab-hang-study-2026-10-26.md`);
- four research lanes from tonight (Arturia's own material, the DAW integrations, Windows MIDI Services, the community);
- my own read-only checks on this machine.

Nothing touched the KeyLab, its MIDI ports, FL Studio or ports 8793/8794/8796. Nothing was downloaded, installed or edited.

**Grades:**
- **[S]** a cited source says it. Web sources were read by the lanes tonight and are cited as they reported them.
- **[S:local]** a read-only look at this machine: a file, a log or the registry.
- **[I]** my inference.

All times are local (UTC−4). mem_watch stores UTC; I converted its times.

---

## Start here: what tonight's checks changed

**1. The hang started well before 23:15: before about 21:25, and probably before 21:18 [I].** The evidence:
- **21:18.** Rill wrote that "pad sysex does not land", with FL closed [S:local: bus handoff 21:18:32, note `handoff-spill:dsh_agent:20261026-211831`].
- **21:25 to 21:50.** FL ran twice, from 21:25 to 21:30 and from 21:35 to 21:50 [S:local: FL64 processes in `state/mem-watch/mem_watch.jsonl`].
  - Rill noted that FL "goes deaf to pads AND keys" and blamed our script [S:local: bus note 21:55:27].
  - But keys arrive on the MIDI input, and FL gives that input to Arturia's "KeyLab mk3 Arturia dev" script, not ours [S:local: registry `HKCU\Software\Image-Line\FL Studio 26\Devices\MIDI input`].
  - After the power cycle the same saved settings played fine: "it works!" [S: hang study].
  - So FL being deaf to keys was almost certainly the hang itself [I].
- **About 21:20.** Rill stopped the screen service, and Daniel then pressed a key. The screen showed "Dbadd9 in Cm, 132 BPM", the same frame that was frozen at 23:23 [S:local: bus note 21:22:39; S: hang study].
  - When the screen service exits normally, it sends a "live readout stopped" card [S:local: `arsenal/keylab/screen.py:806-816`].
  - If Rill stopped it normally, that card never arrived, and the device was already hung [I; this depends on how he stopped it].

**What follows:** every test from 21:18 to 23:29 ran on a device that was already hung. That covers Rill's probes, his sweep of every bank and our 7-step test card. None of them can have caused the hang [I].

The cause lies earlier. FL had been open without a break from 10-24 10:05 to 10-26 about 21:05 [S:local: mem_watch, FL64 pid 63876]. Through that time the screen service was re-sending frames.

**2. Switching programs did not cure it.** During the hang, Daniel switched Prog to Arturia and back to DAW. The pads went to their dim-white DAW resting state, but the hang stayed [S:local: Rill's note 21:55:27].

**3. Our burst governor works per process, not per port.**
- Each `MidiOut` builds its own `BurstGovernor` [S:local: `arsenal/keylab/winmidi.py:95-101`; `governor.py` docstring: "every producer in the process"].
- So each of these gets its own budget of 12 per 100 ms:
  - the screen service;
  - the VJ engine's LED output;
  - every CLI call;
  - FL's script.
- Their combined traffic on the DAW port has no ceiling.
- The README's burst row says "shared by every producer on the port" [S:local: `arsenal/keylab/README.md:32`]. That overstates it.

**4. Our FL script now paints a hue ramp on the pads every time FL starts.**
- Its header still says it "never colours a pad" [S:local: `arsenal/keylab/fl/device_AuroraKeyLab.py` header lines 21-22, against `OnInit` lines 305-310]. The installed copy is byte-identical to the repo copy (sha1 0432d794) [S:local].
- Its diagnostic log, `aurora_fl_script.log`, is nowhere on disk [S:local: Everything search]. So either FL's Python cannot write it, or this version's `OnInit` has never run [I].

**5. Windows logged nothing when the hang began.**
- From 10-24 until the 23:31 power cycle, the System log has no USB, Plug and Play, driver or sleep event for the KeyLab or the PC [S:local: Get-WinEvent, System log].
- The only device events were for other devices: a mouse on 10-24 at 18:34, Bluetooth on 10-25 at 20:30, and a phone plugged in on 10-26 at 22:00.
- There is no Windows MIDI Services event log on this machine [S:local].
- So today a silent stall leaves no trace in Windows [I].

**6. Memory on the PC was not close to running out.**
- Commit peaked at 79% (10-26 09:05). From 20:30 to midnight it ran at 62-68%, with no mem_watch alerts [S:local: mem_watch].
- The kernel's non-paged pool roughly doubled over the uptime, from 2.3 GB to 4.2 GB. The growth is in file-system tags (FMfn, File, Toke, IoNm), not USB or audio tags [S:local].
- For comparison, the 09-11 house outage happened at 6.5 GB non-paged [S:local: memory note house-outage-2026-09-11].

**7. The zeros in the identity reply come from our capture code, not the device.**
- `MIDIHDR.lpData` is declared as `c_char_p`. That type stops reading at the first `00` byte, and Arturia's maker ID starts with `00` [S:local: `winmidi.py:43` and `:258`; a ctypes test in the session scratchpad, `lpdata_probe.py`].
- The replies themselves are 17 bytes long (`liveness_fresh.txt`), the standard length for this reply shape [S:local; I].

**8. FL's saved setup.**
- FL 26 runs our script ("KeyLab mk3 Akashic") on the DAW input. FL 25 is still set to Arturia's "KeyLab mk3" [S:local: registry].
- Both versions run "KeyLab mk3 Arturia dev" on the MIDI input [S:local].
- USB selective suspend is on in the active power plan, both on AC and on battery [S:local: powercfg].

---

## 1. How to read the KeyLab: the layers

Every message passes through a stack of layers. A failure in one layer has its own look from above, which is what lets you tell them apart.

| Layer | What it is on this machine | Healthy | Broken looks like |
|---|---|---|---|
| **L0 Device firmware** (the keyboard's own computer) | Runs the screen, the menus, sleep, and the keys and pads | Menus respond. The screen sleeps after 5 min untouched and wakes on a key [S: manual p.60 §5.4.1.8, via manualslib] | **Burst freeze** (10-22): black screen, buttons dead [S: hang study]. **Silent hang** (tonight): menus, sleep and wake all still work, so this layer was alive [S: hang study; I] |
| **L1 USB link and driver** | USB-C straight into the root hub, with no hub [S:local]. Arturia's own driver, `arturiausbmidi` 1.7.0.0, plus a kernel-streaming child, `arturiausbmidiks`. Probably built on Thesycon's USB audio framework [S: lanes, PnP query; I] | The device is listed in Device Manager with status OK | Unplugged: the ports vanish. A **silent stall**: the ports are still listed but nothing moves either way (tonight's best fit [I]) |
| **L2 Windows MIDI Services** (`midisrv`) | Every WinMM app, ours and FL, goes through it. It reaches the KeyLab through its "kernel streaming aggregate" path [S:local; S: microsoft.github.io/MIDI kb/kernel-streaming-aggregate] | Ports open. Each `midiOutLongMsg` returns 0 | An error code on send: 1 means the service's write waited more than 1 s; 6 (`MMSYSERR_NODRIVER`) means the device left and came back [S: microsoft/MIDI `MidiXProc.cpp`, #1267]. Other signs: replies arriving within 5 ms of `midiInStart` are dropped [S: #1263]; `Restart-Service midisrv` hangs [S: #1084, #1195] |
| **L3 The two ports** | "KeyLab 88 mk3 MIDI" carries the Arturia and User programs: keys, wheels, pedals, bank pads. "KeyLab 88 mk3 DAW" carries the DAW program, plus our LED and screen SysEx going out [S: Arturia KB 15604245986460; S:local: README:36] | A DAW-bank pad press arrives on the DAW input as `99 00 7F` (seen at 23:34) [S:local: `liveness_fresh.txt`] | Writing to the right port while the unit is in the wrong program: nothing lands. After a re-plug, port names can gain a prefix such as "2- KeyLab 88 mk3 DAW" [S: Bitwig `KeylabMk3ControllerExtensionDefinition.java:81-111`] |
| **L4 SysEx envelope** | Arturia: `F0 00 20 6B 7F 42 <payload> F7`. The universal Device Inquiry is `F0 7E 7F 06 01 F7`; the reply is `F0 7E 7F 06 02 00 20 6B 02 00 0A xx v v v v F7` (17 bytes) [S: protocol doc; Bitwig and Live id bytes; S:local: length] | Any reply at all means L0 to L4 all work, in both directions | A byte above 127 inside a message froze a KeyLab Essential mk3 [S: forum.arturia.com/t/3273]. A SysEx left open (no `F7`) makes the service swallow the messages after it [S: microsoft/MIDI #1267 comment]; the fix is to send a lone `F7` |
| **L5 DAW handshake and program** | Connect `00 02 05 01`, disconnect `00 02 05 00`. The physical program (Prog, middle option = DAW) must already be set; no SysEx can switch programs [S: protocol doc; S:local: Rill note 21:55] | DAW-bank pads show colours we send | A disconnect clears every LED, which looks exactly like a script that failed to load [S:local: Rill lesson 21:40]. Connect does nothing outside DAW mode [S: saxofonbrian/keylab-mk3-sysex, "Mode and handshake"] |
| **L6 LEDs** | `00 02 03 <id> R G B 00`: buttons 0-33, banks A-D 34-81, **DAW bank 82-93** (the only bank shown in DAW mode). Request byte `00` [S:local: README:30-31] | Colours show | Wrong bank: accepted but never shown. White instead of a colour: request byte `02`. Uniform dim white: nobody has painted since DAW mode began [S:local: README; Rill note] |
| **L7 Screen** | `00 02 04 <screenId> fields…`. Popups 23-25 vanish after about 1 s; the full two-line page (12) stays. **Never send screens 38, 43 or 44** [S: LCD capability doc §2] | The text changes when the music does | Dark: sleep, and a key wakes it. Host SysEx does **not** count as activity [S: hang study]. **A frame on the screen proves nothing about now.** Tonight's frozen frame was read as "the path works" at 21:18 [S:local: handoff; I] |

**In one sentence:** if the device answers the Device Inquiry, every layer from L0 to L4 works both ways, and any remaining problem is in L5 to L7 (program, bank, port, or another writer). If it does not answer, the fault is in L0 to L2, and only the recovery ladder below can say which layer [I].

---

## 2. Troubleshooting and recovery

### 2.1 Symptom → likely layer → separating test → fix

| Symptom | Likely layer | Test that separates the causes | Fix, cheapest first |
|---|---|---|---|
| Screen and pads dark | L0 sleep | Press a key | None needed. The screen always darkens after 5 min [S: manual p.60] |
| Pads or screen don't change, but the device answers the inquiry | L3, L5 or L6 (program, bank, port or another writer) | Check that Prog is on DAW. With FL **closed**, run `keylab led 82 blue` | Write to bank 82-93. Use request byte `00`. Stop the other writer |
| Nothing goes in or out, no inquiry reply, menus still work | L1 or L2: **silent hang** | The ladder in 2.2 | The ladder |
| Black screen and buttons dead | L0: **burst freeze** | None | Power cycle |
| KeyLab ports missing | L1 | Device Manager; the cable; no hub [S: Arturia KB 15604245986460] | Replug |
| A long-lived process gets error 6 after a KeyLab reboot | L2: stale WinMM handle | None | Close, wait 2-3 s, reopen by name [S: microsoft/MIDI #1267, #696] |
| A send returns error 1 | L2 waiting on a device that isn't draining | Run `doctor` | Treat it as a hang: the ladder |
| Our tools see keys, FL hears nothing | FL settings | FL > MIDI settings | Arturia's layout: DAW port has the same port number for input and output; MIDI input on "KeyLab mk3 Arturia" [S: Arturia KB 15637916754204] |
| Identity reply shows zeros after `06 02` | Our capture code | — | Fix `lpData` (section 4.1) [S:local] |

### 2.2 The ladder for a silent hang

The ladder runs from the least disruptive step to the most. At each step:
- run `doctor` (or tonight's `keylab_liveness.py`) and note the time;
- stop at the first step that brings the device back;
- that step tells you which layer was stuck [I].

0. **Wake it with a key, then probe.** The screen may just be asleep. Free.
1. **Try the device's own menus** (Prog, Settings). If they respond, the firmware is running.
   - Tonight they responded. Switching Prog to Arturia and back did not cure it [S:local: Rill note].
2. **Close everything that holds a KeyLab port:** FL, the screen service, the VJ engine's LED output, any probe. Wait 3 s and probe from a fresh process.
   - **If it comes back:** one app's session with the port was stuck, on the host side [I].
   - **Restart afterwards:** the services you closed, one at a time, probing after each.
3. *(Only with the Windows MIDI Services Tools installed; see section 5.6.)* Run `midi endpoint monitor` on the KeyLab and press a key.
   - **If the monitor sees the key but WinMM does not:** the fault is in the WinMM layer [S: windows-midi lane, citing the console docs and Pete Brown's method in #1177].
4. **Keep evidence before resetting anything** (Daniel's call; the file is large): Task Manager → midisrv → "Create memory dump file". Microsoft asks for this [S: microsoft/MIDI #1195].
5. **Restart `midisrv`** (Daniel, as admin; Arturia's own advice is to disable it and re-enable it [S: Arturia KB 6878166158108]). This disconnects every MIDI app.
   - **If it comes back:** the Windows MIDI service was stuck.
   - **If the restart itself hangs:** that is a finding too. A device that stops draining its input wedges midisrv until it is unplugged [S: #1084].
   - **Restart afterwards:** FL (or rescan its MIDI devices), the screen service, the VJ engine.
6. **Device Manager → KeyLab 88 mk3 → Disable, wait 5 s, Enable.** This reloads Arturia's driver and re-configures the KeyLab's USB interface without cutting its power [I].
   - **If it comes back:** the driver or the device's USB interface was stuck, not the main firmware [I].
   - Users report this step fixed a KeyLab mkII on Windows 11 [S: Gearspace thread 1454200, search summary only].
   - **Restart afterwards:** every port holder.
7. **Unplug the USB-C cable for 10 s, then replug.**
   - **If the KeyLab runs on its 12 V supply** [S: manual p.10/p.14; cheatsheet shows the jack and switch]: the firmware keeps running, so this separates "USB link state" from "the whole firmware" [I].
   - **If it is powered over USB only:** this is the same as step 8.
8. **Power switch off for 10 s, then on.** Everything resets, so this step tells you nothing about where the fault was [S: arturia and community lanes; I].
   - The unit boots showing a yellow-to-red pad gradient [S: hang study].

**After any step that recovers it:**
- Run `doctor` again.
- Restart every long-lived holder, because WinMM apps never reconnect on their own [S: #696; hang study: the screen service died].
- Re-arm DAW mode, with FL **closed** (`keylab connect`), or let FL's script do it when FL starts.
- Write down which step worked and the time.

### 2.3 Tonight as a worked example

| Step | What happened tonight |
|---|---|
| 0 | Wake worked [S: hang study] |
| 1 | Menus worked; switching Prog did not cure it [S:local: Rill note] |
| 2 | Only partly done. At about 21:20 FL was closed and the screen service stopped, but the only probe was Rill's writes to bank A, which can't be seen [S:local: Rill notes]. At 23:22 the inquiry probe ran while the screen service was still running [S: hang study] |
| 3-7 | Skipped |
| 8 | Fixed it |

So tonight's evidence cannot say which layer was stuck [I]. Next time, stop at each step and probe.

---

## 3. What causes the hang: ranked hypotheses and safe experiments

### Ground rules for every experiment

- **At most 12 SysEx per 100 ms, counted across all producers.** The governor only counts within one process, so either stop every other KeyLab producer first, or give each one a share of the 12 (for example, two producers at 5 each).
- **Never send a DAW connect while FL is open.**
  - `screen --connect` already refuses this [S:local: `__main__.py` help at 720-722].
  - The plain `led`, `pad` and `all` verbs do **not** check. They send a connect on every call unless given `--no-connect` [S:local: `__main__.py:72-76`].
  - Tonight's test card respected the rule only because FL happened to be closed from 21:55 to 23:36 [S:local: mem_watch].
- **Daniel's eyes are the receipt.** Every experiment shows him something he can check (a counter, a colour), and `doctor` runs before and after.
- **Build the watchdog first** (section 4). The experiments that wait for a hang are worthless without the time it started.

### 3.1 Where it got stuck

**M1. The USB link: Arturia's driver or the KeyLab's USB interface firmware. Most likely.**
- **For:**
  - the firmware's own work kept running: menus, sleep and wake;
  - both directions died, on both ports;
  - Windows logged no error;
  - a power cycle cured it [S: hang study; S:local: logs].
- **Against:** nothing yet.
- **Experiment:** at the next hang, ladder steps 6 and 7.
  - Recovery at step 6 or 7 points here.
  - A USB capture (USBPcap) would show whether the host stopped asking the device for data or the device stopped answering [S: #1195 follow-ups; I].

**M2. Windows MIDI Services' connection to the KeyLab only. Possible, but weaker.**
- **For:** documented precedents:
  - the service stuck while receiving, with the device still talking [S: #432];
  - a device that stops draining its input wedges the service [S: #1084];
  - input dying when no SysEx buffers are queued [S: #957].
  - This Windows build lacks several fixes that ship from late November 2026 [S: #1084, #1157, #1263].
- **Against:**
  - Fresh processes opened the ports fine.
  - midisrv was never restarted, yet a device power cycle cured it. That fits only a stall limited to the KeyLab's own endpoint, which the power cycle rebuilt [I].
  - If the service's send had stalled, our sends would have failed with error 1 after about 1 s [S: windows-midi lane, `MidiXProc.cpp`]. The test card prints `!! keylab` on any failure [S:local: `keylab_testcard.py`]. Whether any appeared is open (see the questions at the end).
- **Experiment:** ladder step 5.

**M3. The device's SysEx reader stuck halfway through a message. Unlikely.** That would block host messages, but not the keys going out [I].

### 3.2 What set it off, ranked

| # | Hypothesis | For | Against | Safe experiment |
|---|---|---|---|---|
| T1 | **Long run with constant traffic** wears out something in the firmware or driver | The KeyLab had run about 4 d 15 h since its last start (10-22 06:54) when the hang began, before 21:25 [S: arturia lane, System log; I]. The screen service sends a 66-byte frame on every beat with `--pulse`, plus a resend every 2 s [S:local: `screen.py`; frame length measured offline]. That is about 190k frames a day while music plays [I] | No direct evidence; no forum report of the same | **Soak test.** The screen service alone, run exactly as before (`--pulse --reassert 2`), FL closed when not in use, with the watchdog probing every 5 min, for up to 7 days. Receipt: the watchdog's time-to-hang, and Daniel glancing at the beat marker each day |
| T2 | **Several writers on the DAW port**, each governed alone | Section "Start here" point 3 [S:local]. Windows does nothing to stop two apps' SysEx from colliding [S: #60]. Screen hangs in Ableton and Reaper were eased by turning KeyLab outputs off [S: forum.arturia.com/t/5073, /t/5470] | Each send of 2 KB or less is converted as one locked unit, and all of ours are smaller [S: windows-midi lane, `Midi2.UMP2BSMidiTransform.cpp:90`; I] | **With FL closed:** two producers at 5 per 100 ms each (alternating pad colours plus the screen) for 60 min, watchdog every 60 s. Then one producer at 10 per 100 ms as the control. Daniel watches the alternation |
| T3 | **FL starts and stops** (connect, pad-port property, disconnect, and now our hue ramp) | Every FL start sends this [S:local: our FL script `OnInit`/`OnDeInit`]. Arturia's script sends about 48 SysEx back to back at start [S: integrations lane, `device_KL3.py:83-100`, `KL3Return.py:92-147`] | FL had been open for 2.5 days before the onset, so start/stop activity just before it is unknown [S:local: mem_watch] | Screen service stopped. Open and close FL (FL 26, our script, which paces itself) 20 times, running `doctor` after each. **Do not run the FL 25 / Arturia-script variant:** its 48-message start breaks the 12-per-100 ms rule, so it needs Daniel's explicit waiver |
| T4 | **Sleep and wake while host traffic keeps flowing** | It sleeps after 5 min untouched, and host SysEx does not wake it [S: manual p.60; hang study], so there are hundreds of sleeps over days [I] | None | FL closed, screen service running. Leave the keys untouched; every 15 min wake it with a key and check the screen shows the current beat marker, and that `doctor` says alive. Run for 2-3 h |
| T5 | **USB power saving** | Selective suspend is on in the power plan [S:local]. Arturia staff advise "always on" ports [S: forum.arturia.com/t/2869]. A 2015 KeyLab freeze was fixed by turning USB power saving off [S: legacy-forum.arturia.com/index.php?topic=84324.15] | Ports were held open the whole time, which normally keeps a device awake [I] | Read-only first: Daniel opens Device Manager → KeyLab → Power Management tab, if there is one. Turning selective suspend off is a system setting, so it is Daniel's call; change it alone, then run the T1 soak |
| T6 | **PC memory pressure** (the PC was past the house's 82-92 h low-memory point) | Pools grew [S:local] | Commit 62-68% at the onset; growth was in file-system tags; no alerts [S:local] | No device test needed. Compare future onset times against mem_watch rows; costs nothing |
| T7 | **A burst over about 36, or bytes above 127** | Documented freezes [S: saxofonbrian "Send limits"; forum t/3273] | Those look different (black screen, or dead buttons with live faders). Our encoders guard against both [S: arturia lane, `screen.py:166-168`, `protocol.py:234`] | None. Confirm in code that every screen producer goes through `ascii_clean` |

**About the "~36 freezes" rule.** That number was inherited from saxofonbrian's notes [S:local: `bpm-sources-and-fusion-2026-10-22.md:89`]. Arturia's own FL script, used by FL owners every day, sends about 48 at start [S: integrations lane]. So the freeze must depend on what is sent, the path, or the firmware [I]. The 10-22 black screen on Daniel's unit is real [S:local: README:32], but it was a different kind of failure from tonight's.

---

## 4. A `py -m arsenal.keylab doctor` verb and a watchdog

### 4.1 Fix these first, or the probe will lie

These are findings from the lanes, which I checked against the code. All are in `arsenal/keylab/winmidi.py`, and none were applied.

1. **`lpData` should be `c_void_p`** (line 43). The identity reply's contents are lost at the first `00` byte (line 258) [S:local].
2. **`MidiIn` never re-queues its buffers** (lines 239-247). It has 24 by default. A long-lived watchdog would run out after 24 replies and then report a false "hung" [S:local; I].
   - Re-queue them from a normal thread, never from the callback. Microsoft warns that calling multimedia functions inside the callback can deadlock [S: Learn, MidiInProc].
   - Wait at least 20 ms after `midiInStart` before sending the inquiry [S: #1263].
3. **`send_sysex` gives up silently after 1 s and frees the header anyway** (lines 143-147). It should report the timeout and the result code. On the new Windows stack the wait never actually waits, because the "done" flag is already set when the call returns [S: windows-midi lane; I].
4. **`MidiIn.close` calls `midiInReset` without `midiInStop` first, and ignores the result codes** (lines 267-273). NAudio fixed exactly this ordering [S: NAudio PR #1478]. Ignoring the codes hides the input-handle leak after a power cycle [S: #1157].

### 4.2 `doctor`: what it checks

`doctor` never sends a DAW connect, an LED or a screen frame. It runs these checks in order, cheapest and read-only first:

1. **Ports.**
   - Lists the KeyLab inputs and outputs, accepting "N- " name prefixes [S: Bitwig].
   - If none is found: "not present, check the cable and Device Manager."
2. **Service.** Whether midisrv is running, its start type and its start time.
   - Arturia recommends start type Automatic; ours is Manual [S: Arturia KB 6878166158108; S:local].
3. **USB and driver.**
   - The status of `USB\VID_1C75&PID_02CE`, its driver and version.
   - **The last arrival time**, taken from the `arturiausbmidi` event 3 that is logged at every start of the device. This gives how long the device has been running [S:local: event log; I].
4. **Port holders.**
   - Whether FL64 is running.
   - Our long-lived services, found by their command lines (the way mem_watch finds processes).
   - With the Tools installed, `midi.exe` can list the apps connected right now [S: windows-midi lane, console docs].
5. **Liveness.**
   - Send **one** Device Inquiry on the DAW port, which is where Bitwig asks [S: Bitwig `MidiProcessor.java:44-45, 56`]. Listen on **both** inputs for 1.5 s.
   - If nothing comes back, retry once after 0.5 s, the way Live does [S: decompile `identification.py:119-129`].
   - Only if still silent, ask once on the MIDI port too. This separates "the DAW path is stuck" from "the whole link is stuck."
   - Accept any reply starting `F0 7E xx 06 02 00 20 6B`.
   - Print the model byte and the four version bytes raw. The mapping to a version like "1.5.0" is unknown until Daniel reads the version off the Settings > Global page once and we compare [S: manual p.61; I].
6. **Send results.** Report each send's result code and how long it took.
   - Code 1: the service gave up waiting.
   - Code 6: the device left and came back; close, wait and reopen by name.

**What it prints.** This is an illustrative example:

```
KeyLab doctor  2026-10-27 01:12
  ports     OK    out: KeyLab 88 mk3 MIDI, KeyLab 88 mk3 DAW   in: both
  service   OK    midisrv running since 10-22 03:18 (start type Manual)
  usb       OK    KeyLab 88 mk3 on arturiausbmidi 1.7.0.0; up 1 h 40 m (arrived 10-26 23:31:45)
  holders   INFO  FL Studio running; screen service pid 12720
  liveness  OK    reply on DAW in 4 ms; Arturia 02 00 / 0A 08; version bytes 01 05 00 00
  verdict   ALIVE
```

When the device is hung, the last lines become:

```
  liveness  FAIL  no reply on DAW or MIDI (2 tries each); sends returned 0
  verdict   NOT ANSWERING. Don't power-cycle yet: work through the ladder (doctor --ladder)
```

- **`--json`** gives machine-readable output for Rill.
- A **receipt** goes to `state/arsenal/keylab/receipts/doctor-<stamp>.json`.
- **Exit codes:** 0 alive, 1 not answering, 2 not present, 3 host error.
- **`--ladder`** walks section 2.2 in the terminal: prompt, probe, record. The screen can't be used for this, because it is the thing that's stuck.

**How it stays out of the way.**
- Each probe is a 6-byte message and goes through the governor.
- The inquiry does not wake the device, because host SysEx is not "activity" [S: hang study].
- The reply also reaches FL. Our FL script discards SysEx (`OnSysEx` sets `handled`) [S:local]. Arturia's script has no SysEx handler at all [S: integrations lane].

### 4.3 The watchdog inside the long-lived services

| Aspect | Design |
|---|---|
| **Where** | Inside the process that already owns the DAW output (the screen service, the VJ engine). It reuses that open port and its governor, because each open and close costs about 400 ms and takes locks across the whole service [S: #1195] |
| **At start-up** | Probe before sending any frame, and paint only after a reply. Bitwig and Live both do this [S: Bitwig `MidiProcessor.java:129-143`; Live `on_identified`] |
| **How often** | Every 5 min, and also: immediately after any send error (at most once per 30 s); after the port list changes; every 60 s while the device is not answering |
| **Load** | About 288 probes a day of 6 bytes each, against roughly 190k screen frames a day [I]. There's no need to skip probes when keys are arriving: a key only proves one direction |
| **On failure** | Two failed probes 0.5 s apart mean "not answering." Then: stop painting, so no traffic goes into a dead link [I]; print one line, `KeyLab stopped answering; last answer HH:MM:SS, first silence HH:MM:SS`; and post a bus alert for Daniel and Rill |
| **Recovery** | When the port disappears and comes back, wait 2 s, then reopen by name [S: #1267 workaround]. Probe. If FL is closed, send the DAW connect; if FL is open, let FL's script do it. Then repaint the current frame |
| **Log** | A ring buffer of every send's result code and duration, written out on failure [S: windows-midi lane, test 2] |
| **What it gives us** | The onset window, ready to line up with mem_watch rows, FL starts and sleep. Tonight that window had to be pieced together from bus notes [I] |

**Longer term:** one process that owns the KeyLab ports, with every other producer sending through it. That single change closes the per-process governor gap and tests T2 [I].

### 4.4 What the integrations do, and what we take from them

| Integration | Handshake | Liveness | Recovery | What we take |
|---|---|---|---|---|
| FL Studio itself | Sends the Device Inquiry when it connects a device and matches the reply against `supportedHardwareIds` [S: IL API stubs `script_metadata.md`] | none | none | The inquiry is FL's own ID check |
| Arturia's FL script | Connect at `OnInit` only; never reads anything back [S: `device_KL3.py:83-87`] | none | none | Don't copy its unpaced bursts |
| Bitwig | Inquiry first; DAW connect only after a reply; no retry [S: `MidiProcessor.java`] | none | none | Gate all writing on a reply |
| Bitwig, Essential mk3 (sibling device) | Holds all SysEx in a queue until the handshake is done [S: `SysExHandler.java`] | 1 s timeout | Disconnect, wait 100 ms, inquiry again [S: `SysExHandler.java`] | The only recovery loop in the family |
| Ableton Live | Inquiry twice, wait 0.5 s [S: decompile] | none | Identifies again when the ports change | Retry once; re-check after port changes |

None of them sends anything periodic at idle, and none can recover a unit that goes silent mid-session [S: by absence in all four]. So the watchdog is ours to invent; the tools for it are borrowed.

---

## 5. Developer guidance: what exists, and what doesn't

### 5.1 Arturia

- **No SysEx specification, SDK, developer programme or MIDI implementation chart for the KeyLab mk3** [S: arturia lane, by searching].
  - On 2026-09-09 forum moderator lily.arturia said she had passed the community's reverse-engineering on to the product team. She offered no documentation [S: forum.arturia.com/t/9327, post 3].
  - The only partner programme is NKS, which is an integration, not an SDK [S: KB 20090258446620].
- **Their real developer guidance is their own DAW scripts** [I].
  - The FL script is already on this machine. Its licence is mixed: three files carry an MIT header, and Arturia's id files say "All rights reserved". Read it for facts only [S: integrations lane].
- **Manual:** https://www.manualslib.com/manual/3648617/Arturia-Keylab-Mk3.html (version not stated). Relevant pages:
  - p.60: sleep, brightness, Low Power Mode;
  - p.61: factory reset, the firmware version display;
  - p.21: panic, three quick presses of Stop.
- **Downloads page** (firmware 1.5.1 of 2026-10-16, manual 1.0.4, cheatsheet, DAW scripts and guides): https://www.arturia.com/support/downloads-manuals/product/keylab-88-mk3 [S].
  - No release note mentions a freeze, a USB hang or SysEx.
  - 1.5.1 fixes only random notes from certain chords on the 88 [S: fwradar.com/p/arturia-keylab-61-mk3, second-hand].
- **Help-centre articles** [S: support.arturia.com, articles by number]:
  - 15604245986460, General Questions: the two ports; avoid hubs.
  - 15604324005916, Troubleshooting: factory reset; driver 1.4.0 or newer required.
  - 15637916754204, FL setup.
  - 6878166158108, USB detection: midisrv steps.
  - 4407871884818, Windows 11: the driver is "Multi-Client".
  - 4405748009362, failed-update recovery: hold F#, G and G# of the 2nd octave while powering on to reach the bootloader. This is for a broken firmware update, never for this hang.
  - 19499946683932, common MIDI issues.

### 5.2 Other integrations (facts only, unless the licence is MIT)

- **Bitwig** extensions, MIT: https://github.com/bitwig/bitwig-extensions, in the `arturia/keylab/mk3/` folder and its `essentialMk3` sibling [S].
- **Ableton Live 12.1** decompile, no licence, facts only: https://github.com/chiakibeats/AbletonLive12.1_MIDIRemoteScripts, `KeyLab_mk3/` [S].
- **FL Studio API stubs**, LGPL-3.0, docs only: IL-Group FL-Studio-API-Stubs, `docs/midi_controller_scripting/` [S].

### 5.3 Microsoft

- **Windows MIDI Services documentation:** https://microsoft.github.io/MIDI/ (kb/api-back-compat, kb/kernel-streaming-aggregate, kb/best-practices, tools/console, tools/mididiag) [S].
- **The repo**, MIT: https://github.com/microsoft/MIDI. Issues worth reading: #60, #432, #696, #957, #1078, #1084, #1157, #1195, #1263, #1267 [S].
- **Learn pages:** `midiOutLongMsg`, `midiOutReset`, `midiInAddBuffer`, MidiInProc [S].

### 5.4 Community

- **saxofonbrian/keylab-mk3-sysex**, MIT, https://github.com/saxofonbrian/keylab-mk3-sysex. Sections: "Send limits", "Sending, in practice", "Mode and handshake", "The configuration family 21 03 40". The last describes a read-back message (`20 09 40 lo hi` → `21 09 40 lo hi value`), but its safety on our unit is unknown, and writes in that family switch the unit to User mode [S].
- **saxofonbrian/KeyLabLive**, MIT [S].

### 5.5 Our own documents

- `arsenal/keylab/README.md`
- `research/reviewed/keylab-liberation-2026-10-22/keylab-mk3-sysex-protocol-2026-10-22.md`
- `…/keylab-lcd-full-capability-2026-10-24.md`
- `…/keylab-full-surface-map-2026-10-23.md`
- `…/keylab-hang-study-2026-10-26.md`

### 5.6 Downloads, installs and settings for Daniel's approval (none done)

| Priority | What | Source | Size | Why |
|---|---|---|---|---|
| 1 | Windows MIDI Services Tools 0.99.94-preview.12 (x64). A preview; it also installs the Windows App SDK 2.5.1 runtime | https://github.com/microsoft/MIDI/releases/tag/inbox-preview-12 | 223,376,824 bytes (about 213 MiB) [S] | Gives `midi.exe` (monitor, list connected apps), `mididiag` and the troubleshooter. Enables ladder step 3 and better `doctor` checks |
| 2 | KeyLab mk3 manual 1.0.4 (English) | https://www.arturia.com/api/download/products/keylab-49-mk3/manual/keylab-mk3_Manual_1_0_4_EN.pdf | 98.9 MB [S] | The current wording of the settings pages; the manualslib copy's version is unknown |
| 3 | Firmware 1.5.1 | https://www.arturia.com/api/download/products/keylab-49-mk3/firmware/KeyLab3_FW__1_5_1.kl3 | 7.2 MB [S] | **Not a hang fix.** Read the current version off Settings > Global first; flashing would go through MIDI Control Center 1.23, which is already installed |
| 4 | Arturia Cubase 1.1.0, Logic 1.1.0 and Ableton 1.0.0 scripts | the downloads page above | 3.77 MB / 654.5 KB / 743.55 KB [S] | Other start-up and reconnect habits to study. Licence unknown, so facts only |
| 5 | USBPcap 1.5.4.0, plus Wireshark | https://github.com/desowin/usbpcap | 195,040 bytes; Wireshark not checked [S] | Installs a kernel USB filter driver. Only if ladder steps 3 to 6 don't settle M1 versus M2 |
| — | Not recommended: "midifixreg" | a Google Drive link | unknown [S] | The ports already work |
| setting | midisrv start type → Automatic | services.msc | — | Arturia's advice [S]; low value for this hang |
| setting | USB selective suspend → off | Power Options | — | Experiment T5 [S]. Change it alone |

One lane broke the no-saving rule by accident. Two Arturia PDFs were saved by the web tool and are still on disk; deleting them is Daniel's call:
- `%USERPROFILE%\.claude\projects\E--\88c7ecac-d149-46ae-8e9a-612d5ba3736a\tool-results\webfetch-1793072921849-fyt929.pdf` (FL guide 1.2)
- `…\webfetch-1793072921808-kqyggq.pdf` (cheatsheet)

---

## Questions only Daniel or Rill can answer

**For Daniel:**
1. Before 21:00 on 10-26, when did the KeyLab last work for certain: keys making sound in FL, or the screen changing chord? That sets the earliest the hang could have started.
2. Between 21:25 and 21:50, did the keys make sound in FL?
3. Does your KeyLab run on its 12 V supply, or on USB power only? This decides whether ladder step 7 tells us anything.
4. What firmware version does Settings > Global show? Reading it needs no SysEx.

**For Rill:**
1. How did you stop the screen service at about 21:15: with Ctrl-C, or by killing the process?
2. Did any probe or test card print `!! keylab` or an `MMRESULT` code?
3. Does FL's Script output window show the line "Aurora KeyLab v0: FL keeps the transport…"? If it doesn't, the 21:38 script version may never have loaded.

## Corrections our documents need (not applied)

- **README burst row** (line 32):
  - The "~36" number was inherited, not measured on this unit.
  - The governor is per process.
  - Arturia's own script sends about 48 at start.
- **Hang study:**
  - The onset was before about 21:25, not around 23:15.
  - Switching Prog was tried and failed.
  - The zeros in the reply came from our capture code, not the device.
- **Our FL script:** the header says "never colours a pad", but `OnInit` paints a hue ramp.
- **LCD capability doc, lines 514-515:** Bitwig always writes 0 into the "blink" byte [S: `RgbLightState.java:67-72`].

---

## Lane: Arturia's official material (verbatim)

I found no official Arturia material that covers or fixes tonight's hang. Arturia publishes no SysEx documentation, SDK or developer programme for the KeyLab mk3. No firmware release note mentions a freeze, a USB hang or SysEx; the newest firmware, 1.5.1 (2026-10-16), fixes only a chord bug on the 88. Arturia's support pages do have Windows guidance that fits the hang study: their own USB MIDI driver is required on Windows, and they give steps for the Windows MIDI Service (midisrv). Two read-only checks on this machine also bear on the hang. A power cycle is not proof that the KeyLab itself was the part that hung. And the Windows event log shows the KeyLab had been running without a restart for about 4 days 16 hours before it hung.

Grading: [S] means a source I cite says it. [S:local] means a read-only query on this machine says it (the query is named). [I] means my inference.

**1. What Arturia publishes for the KeyLab 88 mk3**

Source for this section: https://www.arturia.com/support/downloads-manuals/product/keylab-88-mk3 (read in the browser pane with "Show all versions" opened).

- Firmware, all one `.kl3` file per version, hosted under `/api/download/products/keylab-49-mk3/firmware/` [S]:

| Version | Date | Size |
|---|---|---|
| 1.5.1 | 2026-10-16 | 7.2 MB |
| 1.5.0 | 2026-05-11 | 7.2 MB |
| 1.3.8 | 2026-05-05 | 7.2 MB |
| 1.3.7 | 2026-05-05 | 7.2 MB |
| 1.2.1 | 2026-01-12 | 7.36 MB |
| 1.2.0 | 2025-12-16 | 7.37 MB |
| 1.1.1 | 2024-12-02 | 7.23 MB |
| 1.0.4 | 2024-08-14 | 7.1 MB |

- The 49, 61 and 88 share one firmware file [S, the shared download path]. Our own `keylab-lcd-full-capability-2026-10-24.md` line 83 says the 1.5.0 zip holds an image for each size [S].
- Manual, English: version 1.0.4, 98.9 MB, dated 2024-09-30. The French, Spanish, German and Japanese versions are 1.0.3 [S].
- Cheatsheet 1.0.0, 233.83 KB, dated 2025-11-25 [S].
- DAW scripts [S]:
  - MainStage 1.1.0 (2026-05-19)
  - Cubase 1.1.0 and Logic Pro 1.1.0 (2025-03-05)
  - Ableton Live, FL Studio and Bitwig 1.0.0 (2024-08-26); the FL script is 986.41 KB.
- DAW guides: the FL Studio guide online is version 1.2 (2024-12-02, 1.15 MB). Daniel's local copy is the 1.0 of 2024-08-27 [S].
- MIDI Control Center 1.23.0.134 (2026-06-10) [S, https://www.arturia.com/support/downloads-manuals/product/mccu].
- Arturia USB MIDI Driver 1.7.0.0, 3.74 MB, dated 2026-01-13; the file name says it was built 2025-08-20 [S, https://www.arturia.com/support/downloads-manuals/product/midi-driver].
- No release notes appear on any Arturia download page. A script search of the rendered page found none [S]. The release-note text in section 3 is therefore second-hand.

**2. The user manual: what it says about settings and modes**

I read the copy on manualslib (https://www.manualslib.com/manual/3648617/Arturia-Keylab-Mk3.html). Its version is not stated; Arturia's current English manual is 1.0.4. Page numbers below are manualslib viewer pages.

- **Sleep (p.60, section 5.4.1.8)** [S]:
  - After an idle time you set, the KeyLab goes to sleep and all controls go dark. A "Vegas Mode" variant cycles rainbow colours instead.
  - Note: "The screen will always be darkened after 5 minutes of inactivity", whatever you set, to protect against burn-in.
  - The manual does not say whether USB MIDI coming in counts as activity [S, absence]. The hang study observed that host SysEx does not [I, consistent].
- **Other global settings on p.60** [S]:
  - Display Brightness (5.4.1.7).
  - Welcome Page (5.4.1.9): turn it off and the last-used User Program loads at power-up.
  - Low Power Mode (5.4.1.10): halves pad and button brightness, and is available only when the unit runs on a power supply.
  - These are global and apply to every program, Arturia, DAW or User [S, p.55].
- **DAW protocol (p.59–60, 5.4.1.6)** [S]: presets for Live, Logic, Bitwig, FL Studio and Cubase, plus Standard MCU and Standard HUI.
- **MIDI Thru (p.58–59)** [S]: routes are DIN In to USB, USB to DIN Out, DIN In to DIN Out, plus an "Apply MIDI FX" option.
- **Factory Reset (p.61)** [S]: in Global settings, with a confirm step.
- **Firmware version (p.61)** [S]: the same page shows the installed firmware version. Updates come through Analog Lab or MIDI Control Center.
  - The firmware on Daniel's unit is not recorded anywhere in our repo [S:local, grep of the research folder and `arsenal/keylab`]. He can read it there by hand, with no SysEx.
- **Panic (p.21, 2.11.1)** [S]: three quick presses of Stop send a panic, which includes note-off on all channels. Ports are not specified.
- **Programs (p.19, 2.8)** [S]: long-press Prog and hit a pad to jump programs. The Arturia and DAW programs can't be edited or deleted [S, cheatsheet].
- **DAW mode (p.51, section 4.1)** [S]: Arturia, DAW and User modes coexist, and DAW-specific controls keep working in the other modes. The manual never names which USB port DAW mode uses; Arturia's support pages do (section 4).
- **Power (p.10 and p.14)** [S]:
  - USB-C carries power, MIDI and control.
  - An optional 12 V DC 1.0 A power supply is needed only to run without a computer.
  - The cheatsheet's rear-panel drawing shows the 12 V 1.0 A jack and a power switch.
- **Windows driver (p.10)** [S]: Windows needs the Arturia USB MIDI Driver, installed with Analog Lab, for Analog Lab and DAW integration. On Mac the unit is class-compliant.
- **MIDI Control Center (p.75)** [S]: it shows 6 User memories plus read-only Analog Lab and DAW memories. The manual says the MCC chapter was still being finalised.
- **FL guide 1.2 online** [S, read in full]: same 6-page user-level content as Daniel's 1.0 copy. It covers the setup steps, the feature list and the script link https://link.arturia.com/klmk3re, and adds nothing about the screen, pad colours, sleep or freezes.

**3. Firmware release notes**

Arturia's pages show no notes, so these come from fwradar, which says it took them from arturia.com: https://fwradar.com/p/arturia-keylab-61-mk3 [S, second-hand].

- **1.5.1:** on the 88 only, fixed random notes being triggered by certain chords.
- **1.5.0:** new features were MainStage integration, better Analog Lab browsing and a refreshed on-screen look [S, https://www.arturia.com/products/hybrid-synths/keylab-mk3/update and press release]. Fixes, via a community post (not staff, 2026-05-12, https://forum.arturia.com/t/new-mk3-firmware-1-5-0-released/9128) [S]:
  - sustain-pedal value drops;
  - pedal detection range;
  - legato note-killing with Chord, Arp and Hold together;
  - stuck notes during glissando, and while changing Strum;
  - wheels and pedals hard-mapped to channel 1 in Arturia mode.
- **1.3.7 and 1.3.8:** no notes published anywhere I found.
- **1.2.1:** velocity fix on some keys of the 88.
- **1.2.0:** pedal responsiveness, a sustain-related key latency, a Scale-mode cutout, unwanted sustain messages on the MIDI Out and USB ports, a Chord+Scale stuck note, and two fixes specific to the 88.
- **1.1.1:** this is the only release touching anything near our symptoms:
  - no more crash when an external clock runs outside 30–300 BPM;
  - no more inconsistent pad LED states;
  - no more MIDI Control Center lag while connected;
  - in the DAW program, pedals now go out the MIDI port instead of the DAW port;
  - wheels and pads now send on the MIDI port in every program;
  - Transpose and Octave now work with a DAW script loaded.
- **1.0.4:** split point, arpeggiator and scale, colour picker and touch-sensitivity fixes.
- Across all versions, I found no fix for freezes, USB hangs, sleep or SysEx handling [S, absence; I, as far as published notes go].

**4. Arturia's support knowledge base**

The KeyLab mk3 section has five articles: General Questions, How to use and Guidelines, DAW Integration, Software Bundle and Troubleshooting [S, via the help-centre API at support.arturia.com/api/v2/help_center/en-us/sections/15604138149404/articles.json; the HTML pages answer 403].

- **General Questions** (updated 2026-10-16, article 15604245986460) [S]:
  - Plug straight into the computer; avoid hubs, adapters and extension cables, or use a powered hub.
  - The MIDI port carries everything from the Arturia and User programs. The DAW port carries only the DAW program.
  - MCU/HUI is set in MIDI Control Center under Device Settings.
- **Troubleshooting** (updated 2026-10-23, article 15604324005916) [S]:
  - Factory reset is Settings > Global > Factory Reset, then confirm; it erases User programs and settings.
  - Firmware can be reinstalled through MIDI Control Center.
  - On Windows 10/11, "Arturia MIDI Driver" must be installed, minimum version 1.4.0.
  - There is no entry for a freeze, a stuck screen or unresponsive pads.
- **DAW Integration, FL Studio part** (updated 2026-10-24, article 15637916754204) [S]:
  - FL 24.1.1 or later ships the script.
  - "KeyLab mk3 DAW" goes on the same port number for input and output, with Controller Type "KeyLab mk3".
  - "KeyLab mk3 MIDI" input gets Controller Type "KeyLab mk3 Arturia".
  - Load the DAW program on the unit, and connect Arturia plugins to MIDI input 10.
- **Recovery after a failed firmware update** (MCC Firmware Update, updated 2026-10-26, article 4405748009362) [S]:
  - For the 88 mk3, hold F#, G and G# of the 2nd octave while powering on to enter bootloader mode. In bootloader mode all LEDs and the screen are off.
  - Connect directly, with no hub.
- **Common MIDI issues** (updated 2026-10-26, article 19499946683932) [S]:
  - First step: restart the computer and the device.
  - Use the MIDI Console in MIDI Control Center as a monitor.
  - Make sure no MIDI loopback or patchbay apps are in the path.
  - Missing or corrupted MIDI can come from USB 3.0 backward-compatibility or USB controller driver problems.
- **USB detection / communication** (updated 2026-10-19, article 6878166158108) [S]:
  - Since Windows 11 24H2/25H2, the new Windows MIDI Service "may possibly prevent" devices from talking to apps; a sign is MIDI Control Center saying "Failed to open the device".
  - Fix: in services.msc set "Windows MIDI Service"/midisrv to Automatic. If it already is, disable and re-enable it.
  - Failing that, run a "midifixreg" tool from a Google Drive link, then unplug, reboot and replug.
  - The KeyLab mk3 is not on Arturia's class-compliant list. It needs MIDI Control Center, which installs the driver into `C:\Program Files\Arturia\USBMidiDriver`.
  - Class-compliant devices on Windows can serve only one app at a time.
  - Some USB 3.x ports don't fall back to USB 2.0 cleanly; options are a powered USB 2.0 hub or BIOS xHCI settings.
  - "Compatibility with Windows 11" (article 4407871884818, updated 2026-10-11) repeats the midisrv steps and calls Arturia's MIDI drivers "Multi-Client".
- **MIDI Control Center General Questions** (updated 2026-10-22, article 6104313005340) [S]:
  - To open the MIDI Console: open MCC, click SYNC if it isn't greyed out, then View > MIDI Console.
  - With SYNC on, MCC edits go live into the device's working memory.
  - "Failed to open the device" can mean corrupted firmware or driver, or a connection problem.
- **Factory reset article** (20640848513820) [S]: for the KeyLab mk3, the steps are the same as above. The "Firmware / Exit / Reset" power-up menu (hold display buttons 1+2 while plugging in) is for the KeyLab Essential mk3, not ours.
- Searching the help centre for "freeze" and "sysex" found nothing about the KeyLab [S].

**5. Developer programme, SysEx documentation, SDK**

- None found. No help-centre article covers developers or SysEx for the KeyLab [S, searches], and Arturia's sites have no MIDI implementation chart for it [S, absence].
- The only partner programme is NKS with Native Instruments. It is an integration, not an SDK. The KeyLab mk3 article (20090258446620) asks for MCC 1.20 or later plus a template, and Prog + Pad 3 [S].
- Arturia's official stance on the community's reverse-engineering is approval only. Forum moderator lily.arturia wrote on 2026-09-09 that she had shared it with the product team, with no documentation offered [S, https://forum.arturia.com/t/9327.json post 3]. The original thread (t/9326) says Arturia neither publishes nor approves the protocol [S].
- In practice Arturia's developer guidance is its own DAW scripts. The FL one is the Python script already installed on this machine [I]. Licences are as already noted in our repo; this lane copied no code.

**6. Forum reports that bear on hangs**

These are user reports, not Arturia statements.

- **KeyLab Essential mk3 in Cubase** (2024-02-22, https://forum.arturia.com/t/3273.json) [S]:
  - A German umlaut (a byte above 127) in the script's screen text froze the unit: buttons and display stopped, faders still sent. Unplugging fixed it.
  - There was no Arturia reply and no firmware fix.
  - Our encoder already refuses such bytes (`arsenal/keylab/screen.py` lines 166–168 and 400–401; `protocol.py` line 234 masks to 7 bits) [S:local]. So this route to a freeze is closed for our writers [I].
- **A user on firmware 1.5** (2026-07-12, https://forum.arturia.com/t/9252.json) [S]: says that since the first firmware they have had to restart the KeyLab every time they start Logic. Unverified.
- **KeyLab mk3 49, screen dead with the backlight on** (https://forum.arturia.com/t/7164.json) [S]: Arturia support called it a hardware defect and replaced the unit.
- **A firmware update that froze at about 5%** (https://forum.arturia.com/t/firmware-update-for-keylab-61-mk3-froze-12-hours-and-counting/6002) [S, search summary]: switching off and on cleared it.
- **"MIDI port error" thread** (2025, https://forum.arturia.com/t/7572.json) [S]:
  - Admin Leo.arturia advised disabling the KeyLab's DAW output port in the DAW.
  - Users credit MCC 1.20.0.172 and MIDI Driver 1.5.0. One user relays from Arturia support that 1.5.0's only change over 1.4.1 was KeyLab 88 mk3 support.
  - It is unresolved for some people.

**7. This machine against Arturia's guidance (read-only queries)**

- **Installed software matches Arturia's current versions** [S:local, uninstall registry]:
  - Arturia USB MIDI Driver 1.7.0, MIDI Control Center 1.23.0 (both installed 2026-06-11).
  - Analog Lab V 5.12.6 (installed 2026-10-06).
  - Arturia Software Center 2.13.0.
- **How the KeyLab is connected** [S:local, Get-PnpDevice and its properties]:
  - Arturia's driver owns the USB device (`USB\VID_1C75&PID_02CE`): service `arturiausbmidi`, version 1.7.0.0, `oem22.inf`.
  - There is also a kernel-streaming child (`TUSBAUDIO_ENUM\...`, service `arturiausbmidiks`).
  - Windows MIDI Services sits on top as a MidiEndpoint `SWD\MIDISRV\MIDIU_KSA_...`, with port entries "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW".
  - So the path is app → midisrv → Arturia kernel-streaming driver → Arturia USB driver → device [I].
- **No hub** [S:local, parent chain]: the KeyLab sits on "USB Root Hub (USB 3.0)" on an AMD USB 3.20 host controller (Port_#0008.Hub_#0002). That follows Arturia's first rule.
- **midisrv startup type** [S:local, Get-Service]: midisrv, arturiausbmidi and arturiausbmidiks are all Running with StartType Manual. Arturia's article recommends Automatic for midisrv. Changing it is a system setting, so it is Daniel's call.
- **Uptime before the hang** [S:local, System log]:
  - The Arturia driver logs event 3 "Audio Controller initialization failed." each time the device starts. There are 124 of them since the log begins on 2026-06-16, which makes it an arrival marker rather than a fault [I].
  - The last PC boot was 2026-10-22 03:09:40, with a matching KeyLab arrival at 03:09:58.
  - The next arrivals were 2026-10-22 06:54:08 (no PC boot, so a KeyLab power cycle, likely the burst-freeze recovery [I]) and 2026-10-26 23:31:45, which is Daniel's power cycle.
  - So the KeyLab ran for about 4 days 16.6 hours without a restart before tonight's hang was found [I, from these logs]. That supports the long-uptime candidate without proving it.

**8. What this means for the hang (inference)**

- **A power cycle doesn't prove where the fault was.** Re-powering the KeyLab also re-initialises its driver instance; event 3 at 23:31:45 shows the driver started fresh [S:local]. Every symptom in the study, including the screen holding its last frame, sleep and wake on a key, pads at resting white, no input and no reply to the Device Inquiry, would also appear if the host side stalled: the Arturia driver instance or midisrv [I].
- **A ladder that would tell device from host next time.** Each step is drawn from Arturia's own advice, and each needs Daniel's yes because it changes services or devices:
  1. Check whether the KeyLab's own menus (Prog, Settings) still respond.
  2. Open MIDI Control Center: does it say "Failed to open the device", and does its MIDI Console show key presses?
  3. Restart midisrv (Arturia's disable/enable step).
  4. Disable and re-enable the KeyLab in Device Manager.
  5. Only then power-cycle.

  If step 3 or 4 recovers it, the stall was on the host side.
- **No firmware update addresses this.** 1.5.1 fixes only the 88's chord bug. The installed version should be read off the Global page before any update; flashing is Daniel's decision through MCC 1.23, which is already installed [S and I].
- **Analog Lab and Arturia plugins also talk to the KeyLab.** The FL guide routes them to MIDI input 10 and Arturia mode can be entered from the unit, so in FL they are possibly another host-side party in the device conversation [I, not verified].
- **The hang study's port findings stand.** Arturia calls its driver multi-client, so the one-app-at-a-time limit doesn't apply. "Many writers on one port" stays a timing or firmware question, not a driver rule [I].

**9. Downloads worth Daniel's approval (none done, nothing installed)**

1. The current manual 1.0.4 (98.9 MB), to check the settings wording against the manualslib copy, whose version is unknown: `https://www.arturia.com/api/download/products/keylab-49-mk3/manual/keylab-mk3_Manual_1_0_4_EN.pdf`, which redirects to dl.arturia.net.
2. Firmware 1.5.1 (7.2 MB), to compare its strings with 1.5.0 or to flash: `https://www.arturia.com/api/download/products/keylab-49-mk3/firmware/KeyLab3_FW__1_5_1.kl3`.
3. Not recommended now: Arturia's "midifixreg" tool. It comes from Google Drive (`drive.google.com/file/d/1bvLC23koR_Is7DzN96GbXORsipFr7qxT`, size unknown), the ports already work, and if it were ever needed it should come from Microsoft's own Windows MIDI Services release, which I believe ships it [I].

**10. Rule slip and actions taken**

- **Rule slip:** I broke the "don't save downloads to disk" rule by accident. Fetching two Arturia PDFs with the web tool automatically saved copies, which I then read:
  - `%USERPROFILE%\.claude\projects\E--\88c7ecac-d149-46ae-8e9a-612d5ba3736a\tool-results\webfetch-1793072921849-fyt929.pdf` (FL guide 1.2, 1.2 MB)
  - `%USERPROFILE%\.claude\projects\E--\88c7ecac-d149-46ae-8e9a-612d5ba3736a\tool-results\webfetch-1793072921808-kqyggq.pdf` (cheatsheet, 414 KB)

  I left them in place; deleting them is Daniel's call. I didn't fetch the 98.9 MB manual for that reason.
- **Browser:** I opened one tab in the built-in browser on the Arturia downloads page and closed it afterwards.
- **What I did not do:** no repo edits, no commits, and nothing touched the KeyLab, its MIDI ports, FL Studio or ports 8793/8794/8796.

---

## Lane: the DAW integrations as developer documentation (verbatim)

**KeyLab 88 mk3: what the DAW integrations do about the handshake, liveness, pacing and recovery (integrations lane, 2026-10-26)**

None of the integrations has a keep-alive, a heartbeat, a device reset or any way to recover a unit that stops answering in the middle of a session. Each one connects once and then trusts the device. FL Studio, Bitwig and Live all use the same Device Inquiry we use as our liveness check, and two of them wait for its reply before sending anything else.

The most useful new finding for the hang is on the Windows side, not in the integrations. This machine's Windows MIDI Services build predates three WinMM fixes Microsoft made between August and October 2026. One of them is a bug where an app's output stays broken after the device disconnects and comes back. A second is relevant too: Arturia's own FL script sends about 48 SysEx messages back to back at startup, which contradicts our "about 36 in one burst freezes it" rule.

Grades: [S] means a cited source says it. [I] means it is my inference. I touched no device, MIDI port, FL Studio or service port. I downloaded nothing and edited nothing. I read GitHub files through `gh api` to stdout only. On the machine I made three read-only checks: file versions, one registry value and the service status.

## 1. Sources and licences
- **Arturia's FL scripts, local copy** at `%USERPROFILE%\Documents\Image-Line\FL Studio\Settings\Hardware\Arturia KeyLab mk3\`. `device_KL3.py` says "Version 1.1", while Arturia's website offers FL script v1.0.0 from 2024-08-26 [S]. The licence is mixed, so I treated it as facts only:
  - `KL3Dispatch.py`, `KL3Display.py` and `KL3Pages.py` carry a two-line "MIT License, Copyright (c) 2020 Ray Juang" header (lines 3-4, 12-13 and 6-7) [S].
  - `LedId.py`, `ScreenId.py`, `ParamId.py` and `IntegrationPatchId.py` say "Copyright (c) 2024 Arturia. All rights reserved" [S].
- **Arturia's FL user guide, local PDF** `KeyLab_mk3__1_0__2024_08_27__FL_Studio__DAW_User_Guide.pdf`, read in full (6 pages).
- **The sibling Arturia FL scripts on this machine** (KeyLab Essential mk3, MiniLab 3), used for Arturia's general habits. Facts only.
- **Bitwig's extension** at github.com/bitwig/bitwig-extensions, `.../arturia/keylab/mk3/`. MIT [S, GitHub licence API]. Newest commit touching the folder: 1a5951b9, 2025-10-26. The sibling `essentialMk3` and `minilab3` handlers in the same repo were also read.
- **saxofonbrian/keylab-mk3-sysex** at 6321b072a1, `keylab-mk3-sysex.md`, MIT [S]. Also saxofonbrian/KeyLabLive, MIT [S].
- **The Ableton Live 12.1 decompile**: chiakibeats/AbletonLive12.1_MIDIRemoteScripts, `KeyLab_mk3/` plus `ableton/v3/control_surface/`. The repo has no licence, so facts only.
- **Windows side**:
  - microsoft/MIDI repo, MIT [S].
  - The Microsoft Learn page for `midiOutReset`.
  - FL Studio API stubs (IL-Group, LGPL-3.0), docs quoted only.

## 2. Connection handshake and liveness
- **FL Studio, the host itself**: FL sends the standard Device Inquiry when it connects a device and matches the reply against `supportedHardwareIds` using `bytes.startswith` [S: FL-Studio-API-Stubs `docs/midi_controller_scripting/script_metadata.md`, section "supportedHardwareIds"; `device.getDeviceID()` docstring, "as determined by FL Studio when connecting the device"].
  - Arturia's IDs are `00 20 6B 02 00 0A 02|04|08 7F 7F 7F 7F` [S: `device_KL3.py:2`].
  - With plain `startswith`, the trailing `7F 7F 7F 7F` would only match if the device reports those version bytes. Either FL treats `7F` as a wildcard or the reply carries `7F`s [I]. This is open.
- **FL Studio, Arturia's script**: `OnInit` sends DAW connect `00 02 05 01` and nothing else as a handshake [S: `device_KL3.py:83-87`; `KL3Connexion.py:25-27`].
  - There is no `OnSysEx`, `OnDoFullRefresh`, `OnFirstConnect` or `OnProjectLoad` [S, absent from the file].
  - The script never reads anything back from the device [S].
- **Bitwig**:
  - `init()` sends `F0 7E 7F 06 01 F7` [S: `MidiProcessor.java:27, 55-58`].
  - Only when a reply starting `f07e7f06020020` arrives does it send DAW connect, then 1000 ms later the "Bitwig / Connected" screen [S: `MidiProcessor.java:129-143`].
  - There is no retry. If the first inquiry goes unanswered, Bitwig never connects [S, from the code paths].
- **Ableton Live**:
  - The KeyLab spec sets `identity_response_id_bytes = (0,32,107,2,0,10)`, `hello_messages = (CONNECTION_MESSAGE,)` and `goodbye_messages = (DISCONNECTION_MESSAGE,)` [S: `KeyLab_mk3/__init__.py:32-35`; `midi.py:11-13`].
  - The framework sends the inquiry twice (delay 0.0), waits 0.5 s, then stops [S: `identification.py:119-129`].
  - On a valid reply it sends the hello (DAW connect) and calls `refresh_state()` [S: v3 `control_surface.py`, `on_identified`].
  - Until then the display shows nothing: `DisconnectedView` renders `None` while not identified [S: `display/view/view.py:58-70`; `KeyLab_mk3/display.py`, `create_root_view`].
- **Bitwig's KeyLab Essential mk3 handler (sibling device)** has the only connect watchdog in the family:
  - If there is no reply 1000 ms after start, it sends disconnect, pauses 100 ms and sends a new inquiry. The reply re-activates it [S: `essentialMk3/components/SysExHandler.java:95-104, 126-139, 180-194`].
  - All outgoing SysEx waits in a queue until the handshake completes [S: same file, `processMidi` and `sendSysex`].
- **What a healthy reply looks like**:
  - It starts `F0 7E 7F 06 02 00 20 6B 02 00 0A` [S: Bitwig's prefix plus Live's id bytes]. The standard layout follows with a size byte and four firmware-version bytes [S: `getDeviceID` docstring example].
  - So our capture printing zeros after `06 02` is a bug in our capture code, not the device [I, strong].
  - Fixing it would also answer "firmware version on the unit: UNKNOWN" (LCD capability doc §10.8) [I].
  - A zero-risk way to see FL's own copy: Daniel runs `device.getDeviceID()` from FL's script output console [S: the docstring says to; I that it suits us].
- **saxofonbrian on the handshake**:
  - Connect is a handshake, not a mode switch, and only works when the unit is already in that mode [S: `keylab-mk3-sysex.md`, "Mode and handshake", measured].
  - "Without it the screen stayed dead whenever the keyboard was powered on after the DAW" [S: same section, from their code].

## 3. Keep-alive, heartbeat and reconnect
- **No integration sends anything periodic at idle** [S, by absence in all four code bases].
  - FL's `OnIdle` sends only when the song step changes, or while Rewind or Forward is held [S: `KL3Return.py:258-293`].
  - Bitwig's 50 ms tick only advances blink phases and timers [S: `MidiProcessor.java:64-80`].
- **Reconnect exists only in Live**: `port_settings_changed()` re-runs identification, then sends the hello plus a full refresh [S: v3 `control_surface.py`, `port_settings_changed` and `on_identified`]. That Live calls it on hot-plug is [I].
- **Port names after re-plug**: Bitwig auto-detects the port names with Windows prefixes `2-` through `5-`, for example "2- KeyLab 88 mk3 DAW" [S: `KeylabMk3ControllerExtensionDefinition.java:81-111`]. Matching by exact name can miss a device that re-appears under a prefixed name [I].
- **The handshake is repeatable**: Arturia's MiniLab 3 FL script re-sends connect or disconnect on every `OnRefresh` [S: `Arturia MiniLab 3\device_MiniLab3.py`, `OnRefresh`]. Repeating the handshake is normal in Arturia's own code [I].

## 4. Startup, shutdown, sleep and the device re-appearing
- **FL startup sends about 48 SysEx back to back with no delays**:
  - connect: 1
  - transport and screen-button LEDs: 17
  - DAW command LEDs: 4
  - bank A and B pad LEDs: 24
  - the "Pad MIDI Port" property `00 02 00 14 02 01 00`: 1
  - the "Connected" card on screen 31: 1

  [S: `device_KL3.py:83-100`; `KL3Return.py:92-147`; the count is mine.]
- **FL shutdown**: `OnDeInit` sends only DAW disconnect. It clears no LEDs [S: `device_KL3.py:120-124`].
- **Bitwig**: shutdown sends DAW disconnect [S: `MidiProcessor.java:94-96`; `KeylabMk3ControllerExtension.java:213-216`].
- **Live**: sends its goodbye after the framework disconnect (`send_goodbye_messages_last = True`) [S: `control_surface_specification.py`; v3 `control_surface.py`, `disconnect`].
- **Arturia's Essential mk3 FL script** pauses around connect: 2 s, then connect, then 2 s, then the LED setup, then 1 s, then "Connected" [S: `Arturia KeyLab Essential mk3\device_KLEss3.py:108-117`]. The mk3 script has no pauses [S].
- **Sleep**: no integration and not the FL guide mentions or handles device sleep [S, by absence].

## 5. How they pace LED and screen updates

| Who | Pacing | Dedup | Notes |
|---|---|---|---|
| FL (Arturia) | none; every call goes straight to `midiOutSysex` [S: `KL3Dispatch.py:64-66`] | none | `OnRefresh` sends up to about 40 messages per call for any flag value except 4 and 4096 [S: `device_KL3.py:141-152` and the Return functions; count I]. During playback each step change sends 13 (about 100/s at 120 BPM, 16th steps) [S: `IdleSequencer`; rate I]. Holding Rewind or Forward sends a screen popup on every `OnIdle`, "roughly once every 20ms" [S: `KL3Return.py:275-293`; FL callbacks doc]. |
| Bitwig | 50 ms tick for blinks; host flush otherwise | yes, the framework's light state; `refreshLight()` forces a resend [S: `RgbButton.java:48-67`; that it fires only on change is I] | A fast blink resends a pad every 50 ms [S: `MidiProcessor.java:98-112`]. Screens are sent on each value change, unpaced. |
| Live | messages are collected inside a component guard and flushed together; SysEx is never collapsed [S: v2 `control_surface.py:344-356`] | LEDs, the home screen and button labels `optimized=True` [S: v3 `elements/button.py:63-73`; `KeyLab_mk3/elements.py:52,58`; `elements/sysex.py:61-72`] | Popups and parameter screens are not deduplicated [S]. |
| saxofonbrian | 60 ms queue between screen packets; LEDs not queued [S: "Sending, in practice", item 2] | yes, their Live script keeps a per-LED cache [S: KeyLabLive `keylab_live.py:838-840`] | "36 freezes the device", 12 is fine; send each packet as one complete message [S: items 1 and 3]. |
| Bitwig MiniLab 3 (sibling) | 2 ms after each pad SysEx, 3 ms between start-up requests, 20 ms after disconnect | drops repeats of the last message [S: `minilab3/SysExHandler.java`, `sendSysex`, `sendColorBytes`, `requestInitState`] | |

Windows MIDI Services itself has "no built-in speed caps or throttling" [S: microsoft.github.io/MIDI].

## 6. Messages that reset or query the device, and what it sends back
- **No integration sends a reset, a state dump or a firmware query to the KeyLab mk3** [S, by absence].
  - Bitwig defines `SET_DAW_PAD_BANK = 00 02 06 01` and never sends it [S: `MidiProcessor.java:37`; no other use in the folder].
- **A real query exists in the configuration family** [S: `keylab-mk3-sysex.md`, "The configuration family 21 03 40"]:
  - read one byte: `20 09 40 <lo> <hi>`
  - the device's reply: `21 09 40 <lo> <hi> <value>`
  - commit: `06 03`

  A read could serve as an Arturia-native liveness probe, but its safety on our unit is UNKNOWN [I]. Writes in that family throw the unit into User mode [S].
- **What the device sends back, as far as these sources show**: only the identity reply. There is no acknowledgement after DAW connect; Bitwig simply waits a fixed 1 s [S]. No integration handles any error or other unsolicited SysEx from the KeyLab mk3. Bitwig only logs unknown SysEx, and that logging is switched off [S: `MidiProcessor.java:135`; `KeylabMk3ControllerExtension.java:53`].
- **Sibling devices do send unsolicited mode changes**:
  - Essential mk3: `21 11 40 02 00 <mode>`
  - MiniLab 3: `02 00 40 62 01/02`

  [S: `essentialMk3/.../SysExHandler.java:27-28, 140-147`; `MiniLab3Process.py`, `_sysex_dispatcher`.] Whether the KeyLab mk3 does: UNKNOWN. A capture while Daniel presses Prog would settle it [I].
- **Screen ids we must never send** are confirmed by name in Arturia's own list: `eScreenWelcome` 37, `eScreenBoot` 38, `eScreenPedalCalibration` 43 and `eScreenBootloader` 44 [S: `ScreenId.py:63-71`]. Our gate already refuses 38, 43 and 44 [S: LCD capability doc §9]; 37 is "leave for last" there.

## 7. What could explain the hang, and recovery without a power cycle
1. **Our usage is outside every integration's pattern** [I]. Every DAW holds one long-lived handle and is the only writer. We use many short-lived processes on the DAW port, sometimes alongside FL, plus a service re-sending a frame every 2 s for days. No integration sends idle traffic for days. "Many writers" and "days of resends" remain the leading candidates.
2. **This machine has known host-side MIDI bugs** [S for the bugs; I that this build lacks the fixes].
   - It runs Windows build 26200.9168, with Windows MIDI Services in full mode (`UseLegacyMidi` not set), `Midi2.BS2UMPTransform.dll` 1.0.15.0 and `wdmaud2.drv` 10.0.26100.7705, both dated 2026-08-12.
   - microsoft/MIDI issue #1267, closed:
     - Bug one: after a USB device disconnects and returns during a long SysEx send, that process's WinMM output stays broken until the app restarts. It was fixed in the repo as beaacd6 on 2026-10-10, not yet in retail Windows. Workaround: on `MMSYSERR_NODRIVER`, close, wait a couple of seconds, look the device up by name and reopen.
     - Bug two, in a comment on #1267: inside an open SysEx (F0 sent, no F7) the service swallows following messages. Fix ee026eed2 (2026-08-11) is not in retail Windows; Microsoft says build 26200.9457 lacks it, and ours is older. Workaround: send a lone `F7` after abandoning a SysEx.
   - A separate fix, a90a704af (2026-09-02), repaired "WinMM SysEx failure" for 32-bit apps such as MIDI-OX.
   - These bugs explain "every long-lived holder must restart after a KeyLab reboot". They do not explain a fresh process receiving no key presses [I].
3. **`midiOutReset` is not the flood**:
   - Microsoft's documentation says it sends a note-off for every note on every channel plus sustain-off on each channel, and never an end-of-SysEx byte [S: Learn, `midiOutReset`, Remarks].
   - But through Windows MIDI Services, `CMidiPort::Reset()` does nothing for output ports [S: microsoft/MIDI `src/in-box/Client/WinMM/MidiSrvPort.cpp`, `CMidiPort::Reset`, repo HEAD]. That retail Windows matches the repo is [I].
4. **The device sent nothing at all during the hang**, on the MIDI port too, and our SysEx never touches that port. A stall at the USB link or in the Windows service fits better than a stuck SysEx parser [I].
5. **What to try next time, in order, before power-cycling.** All are untested [I]; the hang study's "prog 2 selected" does not say Daniel toggled modes.
   1. Physically switch Prog to Arturia and back to DAW.
   2. Send DAW disconnect, wait about 100 ms, then the inquiry. This is Bitwig's Essential mk3 recovery.
   3. Close every handle, wait 2 s, reopen by name.
   4. Restart the `midisrv` service, or disable and re-enable the KeyLab's USB device. This also tells a host-side hang from a device-side one. It kills every MIDI holder (FL, our services) and is Daniel's call to make.

## 8. Corrections and contradictions for our documents
- **The burst limit.** Arturia's FL script sends about 48 messages back to back on start, up to about 40 per refresh, and bursts of 13 during playback [S code, counts I]. FL users run this daily. So "about 36 at once freezes the device" cannot be unconditional. It may depend on content (saxofonbrian's 36 were all LED packets), on the path, or on firmware [I].
  - Our README "Confirmed facts" burst row should say this.
  - Whether Arturia's script has run on Daniel's unit recently is unknown: our "KeyLab mk3 Akashic" script also sits in the FL Hardware folder [S: folder listing].
- **The Bitwig "blink byte".** `RgbLightState.apply()` always writes `0` into byte 13 [S: `RgbLightState.java:67-72`]. The `BlinkState` codes are never sent, so LCD capability doc lines 514-515 overstate it.
- **Dead code in Arturia's FL script.** `PartOn`, `PadOn` and `PadRefresh` send 7-byte `04 02 16 …` packets copied from the MiniLab 3. Nothing calls them, and they reference `eLedId.eLedPart`, which does not exist [S: `KL3Process.py:898-968`; `LedId.py`]. Do not copy that pattern.
- **The FL guide**: the DAW port needs matching input and output; the MIDI port is input only; select the DAW program with the Prog button; Arturia plugins go on MIDI input port 10 [S: guide pages 2 and 6]. The guide names the MIDI-port script "KeyLab mk Arturia", but the local file is `# name=KeyLab mk3 Arturia dev` [S: `device_KeyLab mk3 MIDI.py:1`].

## 9. Downloads worth asking Daniel about (none done)
From arturia.com/support/downloads-manuals/product/keylab-88-mk3 [S: that page]:
- **Cubase Script v1.1.0, 3.77 MB**: JavaScript, the newest code family. Its device detection and any idle handling would be visible.
- **Logic Pro Script v1.1.0, 654.5 KB**: the same release date (2025-03-05). May show a different lifecycle.
- **Ableton Live Script v1.0.0, 743.55 KB**: the original files, which would fill the decompile's partial function bodies.
- **The DAW integration guides** for Bitwig, Ableton and Cubase (sizes not listed): troubleshooting steps for "not detected" or reconnect.

No installs are needed.

## 10. Inputs for the `keylab doctor` verb (all [I])
- **Liveness check**: match the reply prefix `F0 7E 7F 06 02 00 20 6B 02 00 0A`, then read the size byte and the four firmware-version bytes. Ask on the DAW port, which is where Bitwig asks and listens [S: `MidiProcessor.java:44-45, 56`].
- **Gate before writing**: like Bitwig and Live, send no screen or LED traffic until a reply arrives. Re-check after any port change, with one retry 0.5 s later.
- **One owner per port**: one long-lived writer per port, with all other producers going through it.
- **Error handling**: report `MMSYSERR_NODRIVER` and close, wait and reopen by name. Never leave a SysEx unterminated.

---

## Lane: Windows MIDI Services (verbatim)

**Windows MIDI Services lane: how the service carries WinMM SysEx, its known issues, and what that says about the 2026-10-26 KeyLab hang**

## Bottom line

1. **The KeyLab is not on a Microsoft driver.** It runs on Arturia's own driver, version 1.7.0.0. The MIDI service reaches it through its "Kernel Streaming Aggregate" path (KSA), which is how it talks to older MIDI 1.0 drivers. [S: local read-only PnP query] The driver is very likely built on Thesycon's USB audio framework. [I] Microsoft's own advice is to avoid third-party drivers unless you need them. [S]
2. **The hang was most likely below the MIDI service, in the Arturia driver or the KeyLab's firmware.** It was probably not in midisrv or the WinMM layer. [I] The evidence:
   - midisrv kept running the whole time and was not restarted. [S: local]
   - When the service's write to a device stalls, every WinMM SysEx send fails after about 1 second with error code 1. Our CLI prints that error and exits. The hang study records no such errors. [I, built from source facts; please confirm in the scratch-probe logs]
   - Input was dead too: a key press produced no events. A stuck service write does not stop input. [S #1195; I]
3. **This lane found a real bug in our capture code.** `winmidi.MidiIn` cuts every captured SysEx at its first `00` byte, then reads past the end of a short Python object. That explains the "zeros after `06 02`" in the identity reply, because Arturia's maker ID starts with `00`. I confirmed it with a pure-ctypes test that made no MIDI calls. [S: test output; I: explanation]
4. **This Windows build has several known WinMM bugs that bear on our tools**, with fixes not shipping until late 2026 or early 2027 (details below). The diagnostic tools (`midi.exe`, `mididiag`, the troubleshooter app) are not installed here.

I did not touch the KeyLab, any MIDI port, FL Studio, or ports 8793/8794/8796. I only ran read-only PnP, registry, event-log and process queries, plus one ctypes test. I made no repo edits and downloaded no files.

## 1. This machine

| Fact | Grade |
|---|---|
| Windows 11 25H2, build 26200.9168. KB5121003 installed 2026-09-21. | [S: local] |
| `midisrv.exe` and `wdmaud2.drv` are version 10.0.26100.7705; `usbaudio.sys` is 10.0.26100.8972. This build matches the one in #1157 exactly. | [S: local; #1157] |
| midisrv starts on demand ("Manual"). It has been running since 2026-10-22 03:18:55 (boot was 03:09:40): 21 MB private memory, 1,036 handles, 8 threads. | [S: local] |
| The registry entries are as Microsoft requires, and the "legacy mode" switch (`UseLegacyMidi`) is not set, so the PC runs the full new MIDI stack. | [S: local; required-registry-entries KB] |
| KeyLab chain: the USB device (`VID_1C75&PID_02CE`) runs on Arturia's `arturiausbmidi` driver (oem22.inf, dated 2025-08-19). Its kernel-streaming child, `TUSBAUDIO_ENUM\…&KS`, runs on `arturiausbmidiks` 1.7.0.0. The service's endpoint is `SWD\MIDISRV\MIDIU_KSA_16201702556534547415`. | [S: local] |
| `TUSBAUDIO_ENUM` is the hardware-ID prefix of Thesycon's TUSBAudio driver (drivermax.com driver listing). | [S] → the Arturia driver is Thesycon-based [I] |
| The KeyLab last arrived at 2026-10-26 23:31:45 (USB) and 23:31:47 (endpoint). That is Daniel's power cycle. | [S: local] |
| The Arturia driver logs Event 3, "Audio Controller initialization failed.", at every device arrival (daily back to 2026-06-16, including 10-22 03:09:58 and 06:54:08). It logged nothing between 22:30 and 23:31 on 10-26. | [S: local] → it marks arrivals, not hangs [I] |
| The Windows MIDI Services Tools are not installed: no `midi.exe` or `mididiag`. | [S: local] |

## 2. How WinMM SysEx travels through the service

Sources are microsoft/MIDI on `main` (MIT licence). Line numbers drift.

**Sending:**
- `midiOutLongMsg` is synchronous. It splits the buffer into pieces of at most 2,048 bytes and sends each one with "wait for send complete". It sets the done flag and sends the done callback before it returns. [S: `src/in-box/Client/WinMM/MidiSrvPort.cpp` `SendLongMessage`; `src/in-box/Inc/MidiDefs.h` line 70]
- The 2,048-byte limit on one message was removed by this splitting; an 8,192-byte SysEx was tested. [S #605]
- The send-complete wait is 1,000 ms, or 4,000 ms where a staged fix (`Feature_Servicing_MIDI2XProcSendWaitTimeouts`) is enabled. On timeout the pipe is marked stalled and later sends are dropped without waiting. [S: `src/in-box/Libs/MidiXProc/MidiXProc.cpp` lines 46-57, 344-410, 840-858]
- That stall error maps to `MMSYSERR_ERROR` (1). [S: `winmmdrv.cpp` error-mapping function]
- The service moves its read position only after it has finished processing a message, including the write to the device. [S: MidiXProc.cpp reader loop] So "send complete" means the device write returned. [I] Microsoft says the same thing in other words: sends "can wait until the message has been transmitted". [S #258]
- The write to an older KS driver is a blocking call with no timeout on today's builds. [S: `src/in-box/Libs/MidiKs/MidiKs.cpp` `WritePacketMidiData`] Pete Brown (Microsoft) on #1195: "midisrv waits for that write with no time limit".
- The fix gives each write 4,000 ms plus 1 ms per byte. After 3 timeouts in a row the output pin is retired. [S: `src/in-box/Inc/MidiKS.h` lines 105-108; MidiKs.cpp lines 595-707] Nothing in that object ever turns the pin back on. [S]
  - It rolls out in the end-of-November 2026 controlled rollout and can take up to 45 days to enable. [S #1084, Pete Brown 2026-09-14]
  - Once it is on, a wedged KeyLab would show up as host writes failing with an error. That would look different from a silent hang. [I]
- The client-to-service buffer is 64 KB, holding about 2,730 messages of 24 bytes. [S: Pete's numbers, quoted in #695]

**`midiOutReset`:**
- Microsoft's documentation says it sends "a note-off message for each note in each channel" and turns sustain off on each channel. [S: Learn, `midiOutReset` Remarks] That is about 2,064 messages [I].
- In the new stack, the reset handler does nothing for output. It only acts on input. [S: MidiSrvPort.cpp `CMidiPort::Reset`] So our reset on close sends nothing today. [I] It would become that 2,064-message burst if anyone switches the PC to legacy mode. [I]

**Receiving:**
- Messages stamped before `midiInStart` are dropped. [S: MidiSrvPort.cpp] Fast replies get caught by this (#1263): 0 of 20 replies arrived with no delay, 5 of 20 at 1 ms, 18 of 20 at 2 ms, 20 of 20 at 5 ms. Microsoft's workaround is a 20 ms delay after `midiInStart`. The fix ships Q4 2026 to Q1 2027. [S]
- SysEx goes into the app's queued buffers. A buffer is completed at `F7` or when it is full. [S: code]
  - If no buffer is queued when a SysEx starts, the service waits 1 ms. After that it silently discards that SysEx and all later ones until a buffer is present when the next SysEx arrives. [S: code constants 1 ms and 10 ms, lines 12-16 and 596-660]
- Microsoft's callback rule: "Applications should not call any multimedia functions from inside the callback function, as doing so can cause a deadlock." [S: Learn, MidiInProc (archived page)] So buffers have to be re-queued from another thread.

**Ordering:** one client's messages pass through one queue that the service reads one at a time, in order. [S: code] There is no ordering guarantee between different clients. [I]

## 3. Several apps sharing one USB MIDI 1.0 device

- Every WinMM app reaches the device through the service, so many apps can use it at once. [S: `docs/kb/api-back-compat.md`]
- **Nothing stops two apps' SysEx from colliding.** Issue #60 has been open since 2023-06-18. [S]
- Each send is converted as one locked unit (the converter holds a lock per call). [S: `Midi2.UMP2BSMidiTransform.cpp` line 90; `MidiDevicePipe.cpp` line 277] So SysEx of 2,048 bytes or less, which covers all of ours, cannot be interleaved mid-message. Larger messages can. [I]
- Device state such as DAW mode, and the last screen frame written, is shared by every app. Any reply the KeyLab sends, including our identity replies, goes to every app that has its input open, FL Studio included. [I]
- **Opening and closing is expensive and has no time limit.** Each open or close is a call to the service under a lock that covers the whole process, plus an exclusive lock inside the service. A stalled close can block opens across the whole machine. `Restart-Service` hangs; killing midisrv cleared it. [S #1195: Microsoft labels this unproven, from code inspection plus one user's report] One user measured about 400 ms per open. [S #1195]
- Lock contention while a device changes can delay `midiOutShortMsg` by up to 30.8 ms. This is still open. [S #1169]
- I found no issue that links many short-lived clients, or a frame sent every 2 seconds, to a device hang. [I: absence in my searches] #968 (receiving stops after the third reopen, on loopbacks) is open and Microsoft could not reproduce it with WinMM. [S]

## 4. Unplugging or power-cycling while apps hold the port

- **Output to a removed device** now fails at once. Before the February 2026 fix it waited 5 seconds. [S #831] The error code issue (#970) was also fixed. [S]
- **WinMM apps do not reconnect by themselves.** They must close and reopen. [S #696, Pete Brown 2025-08-30] That fits our screen service dying at the power cycle. [I]
- **Input handles leak after removal on this build.** `midiInReset` and `midiInStop` return "no driver", and `midiInClose` keeps returning "still playing". The handle and its service connection leak until the process exits. The fix ships Q4 2026 to Q1 2027. [S #1157]
- **A removal during a large SysEx send** leaves that process's output broken (`MMSYSERR_NODRIVER`). [S #1267] Workaround: keep each send to a few KB; on that error, close, wait 2-3 seconds, and reopen by looking the name up again.
- Device numbers shift when devices are added or removed. Call `midiOutGetNumDevs` before opening. [S #981]
- **A device that stops draining its input wedges the service.** midisrv cannot be restarted until the device is unplugged; "the process stays zombied". [S #1084, Pete Brown 2026-08-12] A power cycle counts as an unplug and clears it. [I]
- A similar Arturia case exists: #1078 (KeyLab Essential 61). WinMM input stopped after 10-18 minutes while the console monitor kept receiving, and it also happened in legacy mode. Microsoft suspected hardware or firmware. The reporter never followed up and it was closed. [S]
- Same build as ours: #1177 (KB5121003, vendor-driver devices passing no data) was closed as not reproducible. [S]
- Inbound SysEx through KSA could be corrupted. The fix rolls out from end of November 2026. [S #1040]

## 5. Why the hang points below the service, and how to tell next time

- Not a service wedge: our CLIs kept opening and closing ports, FL started normally afterwards, and midisrv's start time never changed. [S: local; I]
- If midisrv's write to the KeyLab had blocked, each CLI SysEx would have failed after about 1 second with error 1, and `main()` prints that to stderr. [I from §2] **Check:** did any 23:20-23:29 run print `MMRESULT=1`?
- The current evidence cannot separate the Arturia driver from the KeyLab firmware. Microsoft says the same about a device that only runs on its vendor driver. [S: `docs/kb/usb-midi-device-round-trip-measurements.md` note 11]

Tests that would separate them during the next hang (each needs Daniel's go):
1. **Native monitor beside a WinMM monitor.** Run `midi endpoint monitor` on the KeyLab, then press a key.
   - If the native monitor sees the key, the device and driver are alive and the fault is in WinMM.
   - If it does not, the fault is below the service. [S: console docs; Pete's #1177 method]
2. **Log every send.** Record each `midiOutLongMsg` result code and how long it took.
3. **Dump the service.** Take a midisrv memory dump from Task Manager ("Create memory dump"). Microsoft asks for this. [S #1195]
4. **Capture USB traffic.** A USBPcap capture shows whether data moves on the wire. [S #1195 follow-ups]
5. **Swap the driver.** If the KeyLab is class compliant, move it to Microsoft's driver (`usbaudio.sys` or `usbmidi2-acx`) and see whether the hang comes back. [S: class-driver KB; I] Whether Arturia's own tools need the Arturia driver is an open question.

## 6. Our code: findings from this lane (not applied; the lane is read-only)

- **The SysEx capture bug.** The buffer pointer in `MIDIHDR` (`lpData`) is declared `c_char_p`, so reading it returns bytes only up to the first `00`. `ctypes.string_at` then reads past a 5-byte object.
  - In my test, `F0 7E 7F 06 02 00 20 6B …` came back as `F0 7E 7F 06 02 00 00 … 01`. [S: scratch test `…\scratchpad\lpdata_probe.py`]
  - Fix: declare `lpData` as `c_void_p`. [I]
- **The capture can go deaf.** `MidiIn` never re-queues its 24 buffers. A long-lived watchdog would lose every reply after 24 probes and falsely report "hung". [I from §2]
  - Re-queue from a separate thread, wait at least 20 ms after `midiInStart`, and accept any `F0 7E xx 06 02 … F7` reply.
- **The 1-second wait in `send_sysex` never waits on the new stack**, because the done flag is already set when the call returns. [I]
  - In legacy mode the driver decides whether sends are synchronous. [S: Learn, `midiOutLongMsg`] There, unpreparing a header that is not done could free a buffer the driver still owns. This is the same class of bug as NAudio PR #1478 and JUCE #1727. [I]
- **Error codes are ignored when closing input** (`MidiIn.close`). Combined with #1157, that hides the leak after a power cycle. [I]

## 7. Microsoft's diagnostic tools

All are open source in github.com/microsoft/MIDI under the MIT licence. [S]

- **MIDI Console (`midi.exe`)** [S: `docs/tools/console`]
  - Lists endpoints, WinMM ports, the apps connected right now, and the installed transports.
  - `endpoint monitor`: shares the port with other apps, reconnects after an unplug, and can save a capture to a file.
  - `send-message`, `sysex send-file` (with a pause between transfers) and `sysex receive-file`.
  - `service status` and `service ping`; `watch-endpoints` and `watch-ports`; `api-mode get` and `api-mode set`.
- **`mididiag`** writes a report covering [S: `docs/tools/mididiag`]:
  - versions of Windows, the service, `wdmaud2.drv` and the class drivers, and the API mode;
  - unexpected service stops in the last 30 days;
  - each endpoint's device, driver, hubs and last connect/remove time, and WinMM port numbering;
  - connected apps, a ping test, and how long opening a connection takes.
- **`midiksinfo`** shows the kernel-streaming view of devices. It has no documentation yet. [S]
- **MIDI Troubleshooting and Repair app** [S: `docs/tools/miditroubleshooter`]
  - Pages for API mode, diagnostics, and swapping between Microsoft's two USB MIDI drivers.
  - "Capture repro log": a system trace plus a time-travel trace of midisrv, plus the reports.
- **`midi1monitor`** watches a port through WinMM, with WinMM timestamps. **`midi1rtmonitor`** is new in Preview 12. [S]
- **Caveat:** don't use these tools in legacy mode, because some of them start the service. [S: api-mode KB]

## 8. Downloads worth doing (Daniel's approval needed)

1. **Windows MIDI Services Tools 0.99.94-preview.12 (x64)**
   - Size: 223,376,824 bytes (about 213 MiB).
   - Source: github.com/microsoft/MIDI/releases/tag/inbox-preview-12 (via aka.ms/midireleases), published 2026-10-21. [S]
   - It is a preview. Its release notes say it "will not break" the parts of Windows MIDI Services that come with Windows. It also installs the Windows App SDK 2.5.1 runtime. [S]
   - Skip the separate Transports package (21,690,248 bytes); we don't need it.
2. **Optional: USBPcap 1.5.4.0**
   - Size: 195,040 bytes, from github.com/desowin/usbpcap. [S]
   - It also needs Wireshark, and it installs a kernel USB filter driver. [I] Use it only if test 1 is inconclusive.
3. **Optional: Thesycon USB Descriptor Dumper (`tdd.exe`)** from thesycon.de, which Microsoft suggests for checking a device's USB descriptors. [S #1061] I did not check its size.
4. **No install needed:** the midisrv memory dump from Task Manager.

## Open questions

- Did any CLI run during the hang return an error (`MMRESULT`)? Did the capture's `midiInOpen` succeed, and how long did it take?
- Is the KeyLab mk3 class compliant, and does anything Arturia makes need its driver?
- Which of the staged Windows fixes are already switched on for this PC? I found no read-only way to see that without extra tools.

Main sources: microsoft.github.io/MIDI (kb/api-back-compat, kb/how-to-change-api-mode, kb/required-registry-entries, kb/kernel-streaming-aggregate, kb/best-practices, tools/console, tools/mididiag, tools/miditroubleshooter); github.com/microsoft/MIDI issues #60, #258, #605, #695, #696, #831, #968, #970, #981, #1040, #1061, #1078, #1084, #1157, #1169, #1177, #1195, #1263, #1267; Learn pages for `midiOutLongMsg`, `midiOutReset`, `midiInAddBuffer` and MidiInProc. The repo has GitHub Discussions turned off; its maintainers point to Discord instead. [S]

Files:
- E:\AI-Setup\arsenal\keylab\winmidi.py (where the bugs in §6 live)
- <scratch>\lpdata_probe.py

---

## Lane: community hang reports (verbatim)

I found no community report that matches tonight's hang. In that hang, the KeyLab's own screen and sleep kept working while nothing went in or out over USB MIDI, and only a power cycle cleared it. The closest reports, plus several Windows MIDI Services bugs logged in 2026, point to a second explanation the hang study has not ruled out: the stall may have been on the computer's side, not in the keyboard. A power cycle cannot tell the two apart, because it also rebuilds the Windows driver and MIDI-service connection.

Grading: [S] means a source I cite says it (URL plus post or section). [I] means my inference. "Local" means a read-only query I ran on this machine; I did not touch the KeyLab, the MIDI ports or FL Studio.

## 1. Local facts found read-only (these change the picture)

- [S, local System event log] Arturia's driver (`arturiausbmidi`) logged one error, Event 3 "Audio Controller initialization failed", at 2026-10-26 23:31:45. That is the moment of Daniel's power cycle. The same event appears at 2026-10-21 19:17 and 20:05, and 2026-10-22 03:09 and 06:54.
  - [I] It fires when the device reconnects, so it marks reconnects, not the start of a hang.
  - [S, same query] No USB, PnP or MIDI event matched my filter between 22:30 and 23:31 on 10-26. The device did not drop off USB when the hang began.
- [S, local driver query] The KeyLab 88 mk3 runs on **Arturia's own USB MIDI driver, version 1.7.0.0 (dated 2025-08-19)**: `oem11.inf` (MEDIA) and `oem22.inf` (ARTURIAUSBMIDI_SC). It does not use Windows' built-in class driver.
- [S, local] The Windows MIDI service (`midisrv`) is running, set to start manually. The Windows MIDI Services console (`midi.exe`) is **not installed**.
- [S, environment] The OS is build 10.0.26200, which is Windows 11 25H2.

## 2. Community reports closest to the hang signature

| Report | Symptoms | Conditions | What fixed it | Grade |
|---|---|---|---|---|
| Gearspace, "Keylab stops transmitting midi (Win11)" (https://gearspace.com/board/music-computers/1454200-keylab-stops-transmitting-midi-win11.html) | **KeyLab 88 mkII** (not mk3) stops sending MIDI after a while, though Windows, Cubase and Analog Lab still see it | Win11 24H2, USB. A reply asks whether the Arturia driver or the built-in driver is in use | Disabling and re-enabling the KeyLab in Device Manager; for one user it came back after about 1.5 h, when switching armed tracks in Cubase | [S, search-result summary only; the page returned 403] |
| Arturia forum, "Keylab MK3 sometimes stop sending MIDI" (https://forum.arturia.com/t/keylab-mk3-sometimes-stop-sending-midi/5892), Xion, posts 1-7, 2024-12-15/16 | KeyLab 49 mk3: MIDI sending drops at either the transport or the notes. Disabling the script did not help; Cubase had to be restarted | Cubase 14, Win11, WinRT MIDI enabled | Switching from WinRT to the Windows MIDI drivers, after which no more drops. Arturia support advised using only the "MIDI" port. vocov (post 8, 2024-12-19) saw the same in Reaper | [S] |
| Arturia forum, "Cubase DAW integration crashes the Keylab Essential Mk3" (https://forum.arturia.com/t/cubase-daw-integration-crashes-the-keylab-essential-mk3/3273), stanft and m.c, 2024-02-22; cyler32, 2025-03-27 | Essential 49 mk3: after a fader move the buttons die, the display stops changing and MIDI Control Center reports a disconnect. Notes and fader values still pass | Firmware 1.0.17, German Cubase. The script sent "Lautstärke" to the screen, and the "ä" is a byte above 127 | Replugging the unit. The lasting fix was changing the script to replace characters above 127. Still reported in 2025 | [S] (also https://forums.steinberg.net/t/arturia-keylab-essential-61-mk3-not-opening-or-controlling-vstis-in-cubase-pro-13/880270?page=2, posts 25-28) |
| saxofonbrian/keylab-mk3-sysex, MIT (https://github.com/saxofonbrian/keylab-mk3-sysex, keylab-mk3-sysex.md, section "Send limits") | 36 LED packets in one burst from SysEx Librarian freeze the device until it is power-cycled | KeyLab 61 mk3, Live 12, macOS. Mapped Aug-Sep 2026 | Power cycle | [S] |
| Same doc, section "Sending, in practice" | Two screen packets (`00 02 04`) sent back to back race on the device and one is dropped. Sending byte by byte loses 2-4% of packets. The screen accepts only ASCII 32-126; anything else costs the character or the whole packet | same | A queue with 60 ms between packets; sending each packet as one complete message | [S] |
| Same doc, section "MIDI pauses when a readout is drawn over a list" | While a readout over a list keeps changing, the keyboard stops sending MIDI for about 60 ms of every 100 ms | same | — | [S] |

[I] The saxofonbrian burst size (36) is the same as our own "~36-packet" freeze from 2026-10-22. Our README cites that repo, and bpm-sources-and-fusion-2026-10-22.md:89 calls our ~36 "inherited". So it is still open whether 36 was measured on Daniel's unit or carried over.

## 3. Other mk3 screen, LED and DAW failures (fixed without a host-wide hang)

- [S] Arturia forum 7164 (https://forum.arturia.com/t/keylab-mk3-49-screen-not-working/7164), captquack, 2025-03-12. KeyLab 49 mk3: after one session the screen backlight stayed on with no picture, while MIDI still worked. Both the first and the latest firmware were tried; support called it a hardware defect and the unit was returned.
- [S] Sound On Sound review, December 2024 (https://www.soundonsound.com/reviews/arturia-keylab-mkiii), 61 mk3. The display stuck on the first Arturia instrument, "like the display had crashed". Seen in Live, Bitwig and FL, on several computers; the controls kept working.
- [S] Arturia forum 5470 "Reaper bugs" (https://forum.arturia.com/t/reaper-bugs/5470), powertree, 2024-10-23. 61 mk3: the screen froze on the last working plugin when switching tracks. Workaround: turn off the KeyLab's MIDI outputs. An update fixed it (2025-04-30).
- [S] Arturia forum 5073, Live 12 (https://forum.arturia.com/t/keylab-mk3-ableton-live-12-arturia-app-control-not-working/5073), Sep-Oct 2024, Win11 and Mac. The screen showed no plugin; unticking the KeyLab output ports helped, but not reliably.
- [S] Arturia forum 5294, Linux (https://forum.arturia.com/t/status-of-keylab-mk3-analog-lab-on-linux/5294), Tim.Arturia, 2025-04-25. The screen is driven only by SysEx, and the port name must match the Windows name.
  - [I] Analog Lab and Arturia plugins write to the same KeyLab ports themselves, so they are a possible second writer next to our services.
- [S] Arturia forum 7272 (https://forum.arturia.com/t/fl-studio-x-keylab-49-mk3-doesnt-show-preset-information-on-the-screen/7272), 2025-03-23. 49 mk3, firmware 1.1.1, FL Studio: the screen stopped showing the plugin while the knobs kept working. Restarting and replugging did not fix it.
- [S] Arturia forum 5621 (https://forum.arturia.com/t/using-keylab-49-mk3-pads-in-switched-control-mode-problems/5621), 2024-11-14. 49 mk3, firmware 1.0.4: pads in Switched Control mode stop lighting after a power cycle, though their CC messages are still sent. No fix posted.
- [S] Arturia forum 5933 (https://forum.arturia.com/t/keylab-mk3-49-experience-a-bad-unit-or-simply-a-bad-keyboard/5933).
  - vocov, 2024-12-19: a 49 mk3 on direct USB in Reaper switched itself off and on.
  - Igor1980, 2025-03-07: a 49 mk3 lost connection during use on macOS.
- [S] Arturia forum 6002 (https://forum.arturia.com/t/firmware-update-for-keylab-61-mk3-froze-12-hours-and-counting/6002), 2024-12-24/26. A 61 mk3 firmware update froze at about 5%; power off and on, then MIDI Control Center, recovered it.
- [S] Arturia forum 7572 "MIDI port error" (https://forum.arturia.com/t/midi-port-error/7572), Apr-May 2025.
  - Win11 with Cubase, Studio One and Live, after Arturia software updates.
  - Post 13: MIDI driver 1.5.0 differed from 1.4.1 only by adding 88 mk3 support.
  - Post 15: a workaround was switching the KeyLab on after Cubase starts.
- [S] Arturia forum 2869 (https://forum.arturia.com/t/minifuse-disconnects-keylab-essential-61-mk3/2869), 2024-01-14. Essential 61 mk3 behind a MiniFuse hub on Win11 disconnected often, and the event log showed the same `arturiausbmidi` error we have.
  - Arturia staff advised removing the hub, swapping cables and setting the USB ports to "always on".
  - A full reinstall fixed it.
- [S] Arturia forum 6019 (https://forum.arturia.com/t/doubt/6019), Arturia Support, 2024-12-26: connect directly to the computer; a hub is fine if it works and supplies enough power.
- [S] Gig Performer, KeyLab **mkII** LED scriptlet (https://community.gigperformer.com/t/scriptlet-arturia-keylab-mkii-led-control/12473), tripleB.
  - 2022-12-04: with too much SysEx, some LEDs did not respond, so guard times were added.
  - 2024-09-05: holding back MIDI output during startup stopped LED flicker and rare crashes.
- [S] Older models, same symptom family:
  - Image-Line forum (https://forum.image-line.com/viewtopic.php?t=317638), KeyLab mkII 88, 2023-11-08: FL froze after 10-30 minutes, suspected drivers.
  - Arturia legacy forum (https://legacy-forum.arturia.com/index.php?topic=84324.15), April 2015, earlier KeyLab: a controller freeze after a few minutes was fixed by disabling USB power saving and by a software update.
- [S] Bitwig 5.1.4 release notes, 2024-02-28 (https://downloads.bitwig.com/5.1.4/Release-Notes-5.1.4.html): fixed a crashing bug in the Essential mk3 script.

## 4. Windows MIDI Services bugs that look the same from the computer's side

These matter because this machine is on 25H2, with midisrv and a vendor driver.

- [S] microsoft/MIDI #432 (opened 2024-11-08, closed 2025-01-15): the service got stuck while receiving SysEx and every app using it went silent. Only an OS restart or killing MidiSrv recovered it. A USB trace showed **the device kept talking**.
- [S] #245 (2024, closed 2024-08-15): undefined system messages (F4/F5/F9/FD) sent to a USB MIDI 1.0 device on USBMidi2.sys put the service into an endless loop that needed an OS restart.
- [S] #651 (closed 2025-09-03): the service hung when an open USB device was removed.
- [S] #957 (2026-03-31, Win11 25H2 26200): after a device sends SysEx, a WinMM input that has no SysEx buffers queued stops registering further input, and later short messages are lost too.
- [S] #1263 (2026-10-09; fix scheduled for Q4 2026 to Q1 2027): WinMM drops replies timestamped before `midiInStart`.
  - Identity replies to `F0 7E 7F 06 01 F7` were lost at 0 ms delay and received at 5 ms. The workaround is about 20 ms.
  - The maintainer recommends the built-in driver over vendor drivers for class-compliant devices.
- [S] #1267 (2026-10-10): WinMM output stays broken in a process if the device reconnects during a large SysEx send; a new process works.
- [S] #1157 (2026-09-01; fix in the 25H2 November CFR): after removal, a WinMM input with queued buffers cannot reset or close.
- [S] #906 (2026-03-03, still open): WinRT MIDI 1.0 input is silent after a replug on 25H2. WinMM was fixed in February 2026.
- [S] #975 (closed 2026-09-14) and the Microsoft Tech Community thread on KB5077181 (2026-02-21): SysEx send failed with "No Buffers Available" (32-bit apps only; fix in the November 2026 CFR).
- [S] Microsoft's known-issues post (https://devblogs.microsoft.com/windows-music-dev/windows-midi-services-rollout-known-issues-and-workarounds/, updated 2026-04-30): some vendor drivers lock up the service; it recommends `midifixreg` and the Windows MIDI Discord.
- [S] JUCE #1728 (closed 2026-10-16) and NAudio PR #1478 (merged 2026-10-17): long-hidden WinMM buffer bugs surfaced under the new service because its path changes buffer timing.
  - SysEx buffers were freed before the driver finished with them.
  - `midiInReset` was called before `midiInStop`.
  - SysEx was silently dropped when buffers were not re-queued in time.
- [S] rtmidi #377 (2026-09-08): a buffer was freed while still prepared after a failed unprepare.

## 5. What this means for the hang study [I]

1. **The probe cannot yet tell "keyboard hung" from "computer path stuck".** Unplugging or power-cycling resets the driver, the MIDI service connection and the WinMM handles as well as the keyboard. The Device Inquiry check goes through the same WinMM path, so silence proves only that nothing got through that path. A frozen last frame and dead pad writes are exactly what a healthy KeyLab would show if the computer stopped delivering. #432 is the precedent: the service hung while the device kept sending.
2. **Steps to try at the next hang, before power-cycling.** Each step isolates one layer. They are for Daniel to run, since I may not touch the device.
   1. Open FL Studio or another app: do key presses arrive?
   2. Compare `midi endpoint monitor` (goes through the service) with `midi1monitor` (goes through WinMM). Both need the Tools install below.
   3. Restart `midisrv`. This resets only the computer side; #245 and #651 note it sometimes would not stop.
   4. Disable and re-enable the KeyLab in Device Manager. This re-starts the driver and is the Gearspace recovery.
   5. Replug USB.
   6. Power cycle.
   
   If step 3 or 4 brings it back, the fault is on the computer side or in the driver. If only step 6 does, it is the keyboard's firmware. Also check Event Viewer for errors at the moment it stopped.
3. **Things to fix in `arsenal/keylab/winmidi.py` before building the planned watchdog:**
   - `MidiIn` queues 24 buffers of 512 bytes once (lines 239-245) and never re-queues them. A long-lived watchdog would run out of buffers after about 24 SysEx replies. Under the #957 behaviour, all input could then go silent: a false "the KeyLab stopped answering". Open a fresh `MidiIn` for each probe, and wait at least 20 ms after `midiInStart` before sending the inquiry (#1263).
   - `send_sysex` (lines 143-147) waits 1 s for the done flag, then unprepares without checking the result and lets the buffer be freed. If the send is still in progress, that is the use-after-free pattern from rtmidi #377 and NAudio #1478. It also hides the stall signal we want. The send should report that it did not complete and loop on `MIDIERR_STILLPLAYING` with a limit.
   - `MidiIn.close` (line 269) calls `midiInReset` without `midiInStop` unless `stop()` was called first. NAudio fixed this same ordering.
4. **Candidate causes, ranked by community evidence:**
   1. A computer-side or driver stall. It is well documented on 25H2 in 2026, several fixes only ship from the November 2026 CFR onward, and the KeyLab is on Arturia's vendor driver, not the built-in one.
   2. A second writer on the port: Analog Lab or Arturia plugins, FL's script, or several of our short-lived processes. Arturia and Ableton users fixed screen hangs by turning off KeyLab output ports.
   3. USB power saving or a hub. Arturia staff advice, and the 2015 FL freeze fix.
   4. SysEx bursts or back-to-back screen packets. Documented by saxofonbrian, but in our 10-22 case that produced a black screen, which is a different signature.
   5. Bytes above 127 in screen text. A documented freeze on the Essential mk3. Our CLI text path calls `ascii_clean` (`__main__.py:408-415`); I did not check whether every producer goes through it.
5. **Firmware.**
   - [S] There is no public changelog for 1.5.1 (2026-10-16, 7.2 MB; https://www.arturia.com/products/hybrid-synths/keylab-88-mk3/resources).
   - [S] The 1.5.0 notes (forum 9128, 2026-05-12) list sustain-pedal, stuck-note and pedal-mapping fixes, but nothing about freezes or USB.
   - [S] 1.2.0 (forum 8769, 2025-12-18) was mainly sustain-pedal fixes.
   - [S, search-result summary only] 1.2.1 (January 2026) fixed velocity spikes.
   - I found no report of a firmware update fixing a hang like ours. Daniel's firmware version is not recorded in `arsenal/keylab`.

## 6. Downloads and installs worth doing (for Daniel to approve; I did none)

- **Windows MIDI Services Tools package**: the `midi.exe` console and troubleshooting tools, from https://github.com/microsoft/MIDI/releases. Tools 0.99.94-preview.12, released 2026-10-21; the installer size was not shown in what I fetched. It enables steps 2.2 and 2.3 above.
  - [S] `midi1monitor` comes with the Windows MIDI Services SDK, which is also not in-box (https://microsoft.github.io/MIDI/tools/midi1monitor/).
- **KeyLab 88 mk3 firmware 1.5.1** (7.2 MB, 2026-10-16), installed through **MIDI Control Center 1.23.0.134** (70.95 MB for Windows, 2026-06-10). Only worth doing if his unit is older, since the changelog is unknown. Use direct USB; firmware updates have frozen mid-way (forum 6002).
- **Optional experiment: the built-in driver instead of Arturia's.** Microsoft's maintainer favours the built-in driver for class-compliant devices (#1263). Arturia's support pages say its own driver (1.4.0 or newer) is required on Windows. That second point comes from search-result summaries only, because support.arturia.com returned 403.
  - [I] The port names would probably change (forum users without the Arturia driver saw "keylab 49 mk3" and "MIDIIN2 (...)": https://forum.image-line.com/viewtopic.php?t=330816). That would affect the FL script and our port matching. This is Daniel's call.

## 7. Gaps

- Reddit could not be read: the fetch tool is blocked, and no Reddit threads came up in searches.
- Gearspace, support.arturia.com, vi-control.net and reasontalk returned 403, so those rows rest on search-result summaries.
- I found no KeyLab mk3 hang threads on the Image-Line, Bitwig or Ableton forums. The KVR KeyLab mk3 thread (t=613545) has no fault reports.
- I found no 1.5.1 changelog.

Relevant files:
- E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-hang-study-2026-10-26.md
- E:\AI-Setup\arsenal\keylab\winmidi.py
- E:\AI-Setup\arsenal\keylab\README.md
- E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\bpm-sources-and-fusion-2026-10-22.md
