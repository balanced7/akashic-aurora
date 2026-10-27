# The KeyLab's driver, read-only, and what building our own would take (2026-10-27)

Workflow run wf_c00e40e4-eb5 (task wucxq5uvs). Daniel asked (verbatim): "Can we see what we can tell from the arturia driver? what would it take to build our own driver?" Three read-only lanes (the Arturia driver on this machine; building our own path; the USB-MIDI wire protocol and recovery), then one synthesis for Daniel. Nothing was installed, switched, run or changed; the KeyLab's ports were never opened. Verbatim; local paths shortened.

Vandor's read: "Arturia's driver" is Thesycon's TUSBAudio 5.72.0 (built 2024-11-12, classic WDM kernel driver) inside Arturia's package 1.7.0.0; its licence is locked to that Thesycon version, and Thesycon has since shipped 6.x releases with MIDI fixes Arturia has not. Our own driver is realistic as a user-mode program over WinUSB with virtual MIDI ports for FL; a kernel driver of our own is not worth it (signing with Secure Boot, crash risk, weeks of work), and Microsoft already ships an open-source class driver.

---

## The answer for Daniel (verbatim)

# The Arturia driver, and what building our own would take (KeyLab 88 mk3, 2026-10-27)

**Grades:** [S] means a cited source says it. [S:local] means it was measured read-only on this machine. [I] means inference.

All of this was read-only. No one opened the KeyLab's ports or USB handles, touched FL, ran any Arturia code, or changed the system or the repo. Three research lanes did the work. I re-checked the key identity fact myself by reading the version resources of both driver files in the DriverStore.

## In one minute

- **"Arturia's USB MIDI Driver" is a generic, licensed USB audio/MIDI driver called TUSBAudio, version 5.72, made by the German company Thesycon, with Arturia's name on it.** It was built in November 2024, so it is about two years old. Thesycon has since released 6.0 through 6.20, and those include MIDI fixes Arturia hasn't shipped [S:local; S].
- **It has no power-saving settings, and power saving doesn't explain the hang.** It has buffer and flow-control settings, but none is set on this machine and their defaults aren't public [S:local; I].
- **The hang looks like a stuck USB pipe, but we can't yet tell which end stuck.** The KeyLab stayed connected, the hub and controller logged no resets, and Windows logged nothing. The stall could be the KeyLab's own USB-MIDI side or the host driver. A built-in Windows USB trace taken during the next hang could separate them, with nothing installed [S:local; I].
- **"Our own driver" is realistic as a program, not as a kernel driver.** Microsoft's generic WinUSB driver would hand the KeyLab's USB pipes to one process of ours. That gives us timeouts, pipe resets and real visibility. That process is the hub we already plan, with its bottom layer swapped. A kernel driver would mean weeks to months of work, signing costs or turning Secure Boot off, and blue-screen risk. It is not worth it.
- **One limit no driver removes:** the KeyLab's firmware can freeze on its own. On a Mac, with Apple's class driver and not Arturia's, a 36-LED burst froze a KeyLab 61 mk3 until it was power-cycled [S: saxofonbrian/keylab-mk3-sysex]. Our own driver would buy faster detection and gentler recovery, not immunity. Pacing the traffic is still what keeps it alive.

---

## Part 1: What the Arturia driver tells us

### 1.1 What it is and who wrote it

| File on disk | What it really is | Built |
|---|---|---|
| `arturiausbmidi.sys` (434,320 bytes) | "TUSBAudio Class Driver" 5.72.0.0, original name `tusbaudio.sys` | 2024-11-12 [S:local, re-checked tonight] |
| `arturiausbmidiks.sys` (55,440 bytes) | "TUSBAudio Kernel Streaming Driver" 5.72.0.0, original name `tusbaudioks.sys` | 2024-11-12 [S:local, re-checked] |
| `arturiausbmidiapi_x64.dll` (+ an x86 copy) | "TUSBAudio API DLL": control and diagnostics only | 2024-11-12 [S:local] |
| `tllegacysetupaddon.exe` | Installer helper from ToriLogic GmbH | 2024-06 [S:local] |

**How we know it's Thesycon's code:**
- The main driver contains the tag `THESYCON-VERSION-THESYCON tusbaudio.sys v5.72.0 fre x64 Nov 12 2024`.
- Its debug-symbol path is `C:\wrk\prj\_Thesycon\USB\TUSBAudio\...` [S:local].
- Both setup files (INFs) are machine-generated ("GENERATED FILE. DO NOT EDIT!").
- The INF carries a Thesycon licence record: customer 1629, created 2024-11-13, locked to driver version 5.72, covering 2048 Arturia product IDs [S:local].
- The driver refuses to load outside that record ("Driver not licensed for this USB VID/PID.") [S:local strings]. So Arturia can't drop in a newer Thesycon core without a new licence [I].

**What Arturia actually changed:** its 1.7.0.0 package (2025-08-20) only adds model entries around the 2024 core. It covers 17 Arturia models; the KeyLab 88 mk3 is product ID 02CE [S:local].

**What Thesycon fixed since 5.72** [S: thesycon.de history]:
- 6.0.0 (2025-11): USB disconnect handling in the MIDI pipes.
- 6.16.0 (2026-06): a race condition on stream stop, and support for MIDI-only devices.
- 6.20.0 (2026-10-08): MIDI descriptor parsing.

None of these describes our hang exactly [I]. Asking Arturia for a 6.16-or-newer build is still the cheapest lever we have.

**Signing:** both drivers are signed by Microsoft through its "attestation" channel. That means Arturia submitted them for signing without Microsoft's full hardware-lab testing [S:local; I]. The version is past the 2024 security fix in Thesycon 5.68 [S].

### 1.2 How it is built: the chain your keys travel

```
FL Studio
  -> Windows MIDI Services (midisrv, its "KS aggregate" transport)
  -> arturiausbmidiks.sys   (Thesycon's kernel-streaming child: exposes MIDI "pins" to Windows)
  -> arturiausbmidi.sys     (Thesycon's main driver: owns the whole USB device)
  -> USB root hub port 8 (no hub in between) -> AMD USB 3.2 controller
```

[S:local for each hop; I for how they chain]

- **The main driver is the older hand-written driver style (WDM), not Microsoft's modern driver framework.** It builds its own USB requests [S:local imports].
- **It claims the whole device.** Windows' own composite-device driver never loads, so every USB interface on the KeyLab belongs to Thesycon. Arturia's INF beats Microsoft's on rank, 00FF0001 against 00FF2006 [S:local].
- **It has no tracing switch.** Its only diagnostic output is the Windows event log [S:local; I]. The only event it ever logs is "Audio Controller initialization failed.", once each time the KeyLab connects. That is harmless: the audio half finds no audio on a MIDI-only device [S:local; I].
- **The API DLL is control-only.** Its 83 functions cover statistics, the USB descriptor, vendor requests and firmware update. None sends MIDI [S:local].
- **Firmware updates on Windows run through this driver.** The INF sets `DFUProtocol=2`, and MIDI Control Center calls `TUSBAUDIO_StartDfuDownload` [S:local]. Any other driver means switching back to Arturia's before a firmware update [I].

### 1.3 Its settings

**Power saving** [S:local; I]:
- The driver has no idle, selective-suspend or sleep strings at all. That suggests it never puts the KeyLab to sleep, though only disassembly could prove it [S:local; I].
- The device reads fully on (D0).
- The power plan's "USB selective suspend" is on, but only Microsoft's own USB drivers act on it, and none of them is in the KeyLab's stack [S:local; I].
- The hang also doesn't look like suspend: a sleeping USB-powered device must drop to almost no current, yet the pads stayed lit [S: USB 2.0 suspend rule; I].
- **Caveat:** Microsoft's own MIDI driver (option b below) does put the device to sleep after 15 idle minutes [S: microsoft/MIDI `Device.cpp`]. Moving to it adds a power variable we don't have today.

**Buffers and flow control** [S:local strings and registry; I]:
- The driver reads these values if they are present: `MidiInPipeBufferCount`, `MidiOutPipeBufferCount`, `MidiParserInput/OutputBufferSize`, `MidiUsbFlowControl`, `SendResetPipeForMidiInPipe/OutPipe`, `EnableWatchdogStreamingRestart`, `SendRestartDeviceRequest`, `AllowMidiPortSharing`.
- **None is set for the KeyLab.** Arturia's INF writes only seven audio-flavoured values. The defaults and exact meanings are in Thesycon's licensee-only documentation.
- One documented behaviour matters: since version 5.12, Thesycon's MIDI input uses USB flow control. When its receive buffers fill, it stops reading from the KeyLab instead of dropping data [S: Thesycon history].

**The registry knobs with promising names** (`SendResetPipeForMidi*`, `EnableWatchdogStreamingRestart`) look designed for exactly our failure. But they are undocumented, so setting them would be a blind experiment [I].

### 1.4 The ports it creates [S:local]

- **Two ports each way:** "KeyLab 88 mk3 MIDI" (USB virtual cable 0) and "KeyLab 88 mk3 DAW" (cable 1).
- Windows MIDI Services groups them into one endpoint, with the DAW group oddly named "KeyLab 88 mk3 DAW 2".
- The names are not in the INF. They come from the KeyLab's own USB descriptors [S:local; I].
- Both cables almost certainly share one USB pipe in each direction, as standard USB-MIDI does. If so, one stuck cable can stall the other [I].
- The wire format is plain USB-MIDI 1.0: 4-byte packets, each tagged with its cable and message type. SysEx is chopped into 3-byte pieces. For example, a Device Inquiry goes out as `14 F0 7E 7F | 17 06 01 F7` [S: USB-MIDI spec, checked against the Linux driver; I].

### 1.5 What this says about the hang

The facts:
- The KeyLab's own menus and screen kept working.
- It took no host SysEx and sent nothing.
- It never dropped off USB: there was no arrival event between 10-22 06:54 and your power cycle at 10-26 23:31.
- The hub and controller reset counters read zero.
- Nothing was logged [S:local].

| Explanation | What it would look like on the wire | Fit |
|---|---|---|
| **H1. The KeyLab's USB-MIDI side stopped** while its menu side kept running | Every write waits forever: the device keeps saying "not ready" (NAK), and no Windows layer times that out | **Fits** [I] |
| **H2. The KeyLab kept accepting data but its MIDI processing stalled** | Writes "succeed" and vanish | **Fits.** Best fit if no send ever returned an error [I] |
| **H3. The host driver stopped servicing the device** (input never re-requested, or Thesycon's flow control holding input closed) | No input request pending | **Fits** [I] |
| USB sleep (suspend) | — | **No:** pads lit, device on, no resume recorded [S:local; I] |
| Disconnect or re-enumeration | — | **No:** no events [S:local] |
| A one-packet USB glitch (data-toggle error) | Loses one packet, then heals | **No** [I] |

**Why nothing on Windows ever times out.** A device that keeps saying "not ready" looks to every software layer like a transfer that simply never finishes:
- Windows MIDI Services' write to the KeyLab has no time limit in today's retail Windows. Microsoft's repository already has a fix with a timeout, but it hasn't shipped [S].
- Microsoft's own class driver also writes with no timeout [S: `Device.cpp`].
- Thesycon's buffers hide the stall from the apps until they fill [I].

**The trigger is still most likely days of constant SysEx** (about 190,000 screen frames a day), as the guide says. One loose end connects to our own code. The guide found our `MidiIn` never re-queues its buffers. Whether a client that stops reading can push back through midisrv and close Thesycon's input flow control is unknown; midisrv is multi-client, so probably not [I, weak].

### 1.6 What static inspection can't tell us

- The KeyLab's exact USB layout: endpoints, packet size, Full or High Speed, the firmware-update interface.
- Thesycon's buffer defaults.
- The meaning of status `0xEE000050`.
- Which end stuck.

The first item needs a descriptor read (approval list, item 2). The last needs the trace at the next hang (approval list, item 1).

---

## Part 2: What it would take to build our own

### 2.1 The paths at a glance

| Path | Effort | Risk | What breaks | You approve |
|---|---|---|---|---|
| **(d) Stay on Arturia's driver; harden everything above it** (bug fixes, doctor/watchdog, the hub) | Days, already planned | Lowest | Nothing | The usual rollout |
| **(b) Swap to Microsoft's built-in class driver** (no code) | About 30 min, plus a soak | Low; undone in minutes | Port names change, so FL's port setup, our name lookup and possibly Analog Lab's screen link need redoing. Firmware updates need Arturia's driver back. Adds a 15-min idle sleep. Windows Update may quietly put Arturia's driver back | A Device Manager driver switch (admin, FL closed) |
| **(c) A user-mode "driver": WinUSB + our own process + virtual ports.** The real "direct to metal, PC does the work" option | About 1–2 weeks to build, plus a week of soak [I; the lanes said 1–2 and 2–3 weeks] | Medium; reversible | Only one program can own the device, so FL, Analog Lab and our tools all go through our process, and if it dies the keyboard goes silent (it needs a supervisor). Firmware updates need a switch back. Adds one hop of latency: similar bridges report under 1 ms [S]; ours must be measured | Driver binding (admin, FL closed); the MIDI Services Tools/SDK install |
| **(a) Our own kernel driver** | Weeks (a fork of Microsoft's) to months (from scratch) | High: any bug blue-screens the music PC | Secure Boot, or money and paperwork | Secure Boot off plus test mode, or an EV certificate plus a Microsoft Partner Center account |

### 2.2 Each path in plain words

- **(b) Microsoft's class driver** is already on this PC: `USBMidi2.sys` "USBMidi2-ACX" and the older `usbaudio.sys` [S:local].
  - Microsoft's source is MIT-licensed open source [S].
  - The KeyLab mk3 works class-compliant on Linux and Mac (keys, pads, DAW port, screen) [S: Arturia forum t/5294].
  - It keeps multi-client access through Windows MIDI Services [S].
  - Its real value is as an **experiment**: if the hang recurs on Microsoft's driver, Arturia's driver is cleared and the firmware becomes the suspect [I].
- **(c) WinUSB + our process** is how to "bypass the convoluted wrapper". Thesycon's two drivers and the kernel-streaming layer drop out of the device side. FL still reaches the keyboard through Windows MIDI Services, via virtual ports we publish [I]. What our process would do:
  - **Bounded writes:** a per-transfer timeout, so "the device stopped draining" becomes a measured fact instead of silence [S: WinUSB pipe policy].
  - **Gentle recovery, in order:**
    1. Abort the pipe, then reset it. This clears a halt and resyncs the pipe [S].
    2. Reopen the handle.
    3. Cycle the port (admin) [S].
    4. Last resort: you replug the cable.
  - **Never-stopping input:** we drop and count when overloaded instead of using flow control [I].
  - **Separate queues per cable**, so the DAW cable can't block the keys [I].
  - **No sleep unless we ask for it** [S: WinUSB power docs].
  - **Counters** published to the house dashboard.

  Precedents: Ableton Push 2 drives its display this way through libusb [S]. A Bluetooth-MIDI bridge on GitHub (MIT licence) publishes a Windows MIDI Services virtual device this way [S].
- **(a) Kernel driver.** Everything we would add there (timeouts, pipe resets, a watchdog) is available in (c) without kernel risk. If we ever needed it, we would fork Microsoft's MIT-licensed `USBMIDI2` source rather than start from zero [S]. Not recommended.
- **Not an option:** rebuilding or patching Thesycon's driver. It is commercial and licence-locked [S:local].

### 2.3 The honest limit

If the hang is H1 or H2, the KeyLab's own firmware stopped. No host driver can make it start draining again. Path (c) would detect it in under a second and try a port cycle. Whether a port cycle revives a USB-powered KeyLab without a real power cut depends on the hub hardware [S: Microsoft recovery docs; I].

The cure for firmware limits is pacing, and pacing lives in the hub whichever driver sits underneath:
- at most 12 SysEx per 100 ms across all producers;
- screen frames at least 60 ms apart;
- each SysEx sent whole;
- a Device Inquiry check after each burst, which turns open-loop pacing into closed-loop flow control [S: saxofonbrian; S: guide; I].

### 2.4 Recommendation and order

1. **First, the work already in progress, whichever driver we end on:**
   - the governor per port instead of per process;
   - the `MidiIn` buffer and truncation fix;
   - `send_sysex` reporting its timeouts;
   - doctor and the watchdog.

   These are real defects either way.
2. **Then the hub: one process owns the KeyLab ports, and everyone sends through it.** Build it over today's WinMM ports. Path (c) later only swaps its bottom layer from "WinMM port" to "WinUSB pipes", so nothing is wasted [I].
3. **At the next hang:** walk the ladder with the USB trace running (stage 1 below). That tells us which end stuck.
4. **Then the class-driver A/B (b).** It's cheap, but a soak only means something if we know how often the hang happens on Arturia's driver. We have one hang so far. The 36-LED burst is a known way to freeze the unit and might serve as a repeatable trigger, though it isn't proven to be the same failure, and it costs a replug each time. That's your call [I].
5. **Path (c) only if** the evidence points at the host side, or you want the bounded writes and automatic recovery for their own sake.
6. **In parallel, at no cost:** ask Arturia support for a driver on Thesycon 6.16 or newer, and for Thesycon's statistics tool ("Spy"). That's a message from you; I can draft it.

### 2.5 Staged, reversible plan for the user-mode path

| Stage | When | What | Receipt | Undo |
|---|---|---|---|---|
| 0 | Now, offline, no approvals | The bug fixes, doctor, the hub over WinMM. The USB-MIDI packet codec with unit tests. A ctypes binding to Windows' `winusb.dll` (nothing installed; no device touched) | Tests pass; the codec round-trips the real frames (inquiry → `14 F0 7E 7F 17 06 01 F7`) | Code only; revert the commits |
| 1 | Next hang, your yes (admin) | Start the built-in USB trace (`logman` with Windows' xHCI, UCX and USB-hub providers), send one inquiry, press a key, then walk the ladder. **Note whether step 6 (Disable/Enable) revives it without the yellow-to-red boot gradient** | Dated ladder record + `.etl` file: OUT never completes = H1; OUT completes = H2; no IN pending = H3 | `logman stop … -ets`; delete the `.etl` |
| 2 | FL closed, your yes | Read the KeyLab's USB descriptors: the same trace's "rundown" from Windows' cached data, or `lsusb -v` on a Linux machine | Descriptor text filed under research | Nothing to undo |
| 3 | FL closed, your yes | Class-driver A/B: parent → "USB Composite Device", MIDI function → USBMidi2-ACX (or usbaudio). Check keys, pads, SysEx, screen and FL; soak | New port names recorded; doctor log; soak record | Device Manager → pick Arturia's "KeyLab 88 mk3" (its package stays installed) |
| 4 | FL closed, your yes | Bind Windows' own signed WinUSB by hand in Device Manager (**not Zadig**). The hub's bottom layer switches to WinUSB pipes; it publishes "KeyLab 88 mk3 MIDI"/"DAW" as virtual ports | Same checks as stage 3, plus a **recovery drill**: pull the cable mid-write and confirm detect → abort → reset → reopen, with a dated receipt | Device Manager → Arturia driver; delete the added `DeviceInterfaceGUIDs` value |
| 5 | After 4 | Supervisor, the full recovery ladder, counters on the dashboard, a 7-day soak | Soak log with pipe counters | As stage 4 |

Before any firmware update, at any stage: switch back to Arturia's driver.

### 2.6 Needs your approval (nothing done yet)

| # | What | Source, size | What it gives | Undo, risk |
|---|---|---|---|---|
| 1 | USB event trace (`logman`) | Built into Windows; no download; trace size not measured | Which end stuck (at a hang); descriptors and bus speed (any time) | Admin; temporary session; stop it and delete the `.etl` |
| 2 | Descriptor read, the alternatives | Linux `lsusb`: nothing on this PC. USBView: source on GitHub (microsoft/Windows-driver-samples), size not checked. Thesycon `tdd.exe`: size not checked. Arturia's API DLL: already on disk, 320,264 bytes | The KeyLab's exact USB layout (needed for stage 4) | USBView and the DLL talk to the device; run them only with FL closed. The DLL means running vendor code |
| 3 | Read Thesycon's pipe statistics at a hang (`TUSBAUDIO_QueryDeviceStatistics`) | On disk (the same DLL) | Driver-side counters during a hang | Runs vendor code; its data layout isn't public |
| 4 | Windows MIDI Services Tools, Preview 12 | github.com/microsoft/MIDI releases, 223,376,824 bytes [S]; also installs the Windows App SDK 2.5.1 runtime | `midi.exe` monitor (ladder step 3), `mididiag`, the runtime that virtual ports need for stage 4 | Uninstall from Apps; it's a preview |
| 5 | Class-driver switch (stage 3) | In-box | The Arturia-vs-firmware test | Switch back in Device Manager; Windows Update may revert it on its own |
| 6 | WinUSB binding (stage 4) | In-box `winusb.inf` | Direct pipe ownership | Switch back. **Avoid Zadig/libwdi**: it installs a self-made root certificate |
| 7 | Thesycon registry knobs (`SendResetPipeForMidi*`, `MidiUsbFlowControl`) | — | Maybe built-in self-recovery | Meanings and registry location are inferred. **I'd skip these** in favour of 1–3 |
| 8 | pyusb 1.3.1 (58,465 bytes) / libusb-package | PyPI | Convenience only | Not needed: ctypes reaches `winusb.dll` directly |
| 9 | USBPcap 1.5.4.0 | github.com/desowin/usbpcap, 195,040 bytes | Transfer capture | Installs a kernel filter driver; item 1 makes it mostly redundant |
| 10 | Ask Arturia for a 6.x-based driver + the Spy tool | Your message (I'll draft it) | Upstream fixes; driver statistics | None |
| 11 | Hardware USB analyzer | Purchase, not priced | The only tool that sees the device saying "not ready" (NAK) directly | Cost |
| 12 | Path (a) toolchain | Visual Studio 2026 + WDK (several GB), EV certificate, Partner Center | Our own kernel driver | Not recommended |

### 2.7 Where the lanes disagreed

- **Hang fit.** One lane ranked "stuck pipe" best and power saving weak. Another rated three stuck-pipe variants equally. These don't conflict: "stuck pipe" is the shape, and which end stuck is open until stage 1.
- **Effort for (c).** 1–2 weeks versus 2–3 weeks. The gap is the soak, so I've written 1–2 weeks of build plus a week of soak.

Files are in `<scratch>\` (`drv_build\` and `usbwire\` under it):
- the INFs decoded to UTF-8;
- string dumps of the binaries;
- the inspection scripts.

The guide this builds on is `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-dev-guidance-and-hang-guide-2026-10-27.md` (its ladder is section 2.2).

---

## Lane: the Arturia driver on this machine (verbatim)

# Arturia's KeyLab driver: what's on this machine, and what our own driver would take (lane "arturia-driver", read-only, 2026-10-27)

Grades: [S] cited source, [S:local] measured on this machine, [I] inference. I did not open the KeyLab's MIDI ports or USB handles, did not touch FL, ran no Arturia code, and changed nothing on the system or in the repo.

## Bottom line

1. **"Arturia's driver" is Thesycon's TUSBAudio 5.72.0 with Arturia's name on it.** Thesycon is a German company that licenses a USB audio and MIDI driver to many hardware makers. The two .sys files have Arturia names, but their version resources say "TUSBAudio Class Driver", original file names `tusbaudio.sys` and `tusbaudioks.sys`, version 5.72.0.0. The debug-symbol path inside them is `C:\wrk\prj\_Thesycon\USB\TUSBAudio\...`, and the main driver carries the tag `THESYCON-VERSION-THESYCON tusbaudio.sys v5.72.0 fre x64 Nov 12 2024 07:58:22` [S:local]. This settles the guide's "probably Thesycon" [I] as a measured fact.
2. **The core is about two years old.** The engine was built 2024-11-12, and Arturia's package 1.7.0.0 (2025-08-20) only adds model entries around it [S:local]. Thesycon has since released 6.0.0, 6.14, 6.16 and 6.20 (2026-10-08) with MIDI fixes Arturia hasn't shipped [S: thesycon.de history file].
3. **For the hang, a stuck MIDI pipe or a stuck USB queue on the device fits best, power saving fits weakly, and buffer limits matter only as a possible trigger** [I; reasons in the hang section].
4. **"Our own driver" is realistic as a user-mode program, not as a kernel driver.** WinUSB (Microsoft's generic USB driver) would own the KeyLab, and our own process would read and write its USB pipes with timeouts and recovery. FL would see the KeyLab through virtual MIDI ports. Our own kernel driver would mean code signing with Secure Boot on, crash risk, and weeks of work. Microsoft already ships an open-source (MIT) kernel class driver we could fork if we ever need one.

## 1. The KeyLab's device nodes [S:local: Get-PnpDevice / Get-PnpDeviceProperty]

| Node | Instance ID | Driver (service) | INF, version, date | Driver stack |
|---|---|---|---|---|
| The USB device as a whole | `USB\VID_1C75&PID_02CE\7656400341020110` (hardware ID also `&REV_1500`, which matches firmware 1.5.0) | `arturiausbmidi`, setup class `arturiausbmidi_sc` `{463BF520-…}` | oem22.inf (`arturiausbmidi.inf`), section `_Install_12.NTamd64`, 1.7.0.0, 2025-08-20, provider Arturia | `arturiausbmidi`, then ACPI, then USBHUB3 |
| Kernel-streaming (KS) child: the layer that exposes MIDI pins to Windows | `TUSBAUDIO_ENUM\VID_1C75&PID_02CE&KS\7656400341020110` | `arturiausbmidiks`, class MEDIA | oem11.inf (`arturiausbmidiks.inf`), 1.7.0.0 | ksthunk, then `arturiausbmidiks`, then `arturiausbmidi` |
| Windows MIDI Services endpoint | `SWD\MIDISRV\MIDIU_KSA_16201702556534547415` | none (`c_midi.inf` NO_DRV), created by the midisrv process (PID 45480) | Microsoft 10.0.26100.8328 | SoftwareDevice |
| Legacy (WinMM-style) ports | `SWD\MMDEVAPI\…_0_0` "KeyLab 88 mk3 MIDI", `_0_1` "DAW", `_1_0` "MIDI", `_1_1` "DAW" | c_swdevice.inf | — | SoftwareDevice |

- **Arturia's driver takes the whole device.** The compatible IDs end in `USB\COMPOSITE` and the device class is 00 [S:local]. Because Arturia's INF matches the exact `USB\VID_1C75&PID_02CE` ID, Windows never loads its own composite-device driver. So no per-interface `&MI_xx` nodes exist, and the registry and every setupapi log since Feb 2026 show none for PID 02CE [S:local]. Two other Arturia PIDs, 021B and 02CB, did run on Windows' own audio class driver here at some point (`MI_00` nodes with audio interfaces) [S:local: setupapi logs].
- **Physical path:** port 8 of the root hub, no hub in between. The controller is `PCI\VEN_1022&DEV_43FD`, "AMD USB 3.20 eXtensible Host Controller", driven by Microsoft's USBXHCI 10.0.26100.8972 [S:local]. The same root hub also carries a generic hub (1A40:0101) and device 048D:5711 [S:local].
- **History:** first seen on this PC 2025-11-17; current driver installed 2026-06-11; last arrival 2026-10-26 23:31:45, which is Daniel's power cycle [S:local]. The `usbflags` registry key shows earlier device revisions 0500, 1101, 1201 and 1500 [S:local]. Reading those as firmware versions is my inference [I].

## 2. The driver package (INF text) [S:local: DriverStore copies, decoded to UTF-8 in the scratchpad]

- **Generated by Thesycon's tooling.** Both INFs open with "GENERATED FILE. DO NOT EDIT!" and "Copyright (c) 2009-2024", with no company name [S:local].
- **Models matched (17):** MicroFreak, KeyStep Pro, PolyBrute and PolyBrute 12, MiniLab 3, KeyLab Essential 49/61/88 mk3, KeyLab 49/61/88 mk3 (88 = PID 02CE, `_Install_12`), MicroLab mk3, KeyStep mk2, KeyStep 37 mk2, MiniLab 37 mk3 [S:local].
- **Service entries:** kernel driver, demand start, normal error control; `ServiceBinary=%13%\arturiausbmidi.sys`, run from the DriverStore. Each driver registers as an event-log source through `IoLogMsg.dll` plus its own .sys [S:local].
- **KS INF:** pulls in ks.inf and wdmaudio.inf. It registers a KS "Topology" interface named "USB Audio Mixer" and sets `AssociatedFilters=wdmaud,swmidi,redbook` [S:local].
- **Settings the INF writes for the KeyLab 88 (`_AddReg_12`), all audio-oriented:** `DFUProtocol=2`, `InterfaceGUID={B68E4561-4835-47FE-B4E6-041921D15721}`, `KsSampleRateControl=2`, `RestoreClockSourceAtStart=1`, `RestoreSampleRateAtStart=1`, `Settings\DeviceStreamingMode=2`, `Settings\StreamFormatSelectionMode=2` [S:local].
  - The general driver-parameters section is empty: no MIDI buffer, latency, flow-control, port-count, power, selective-suspend or idle values [S:local].
  - Port names and port count are not in the INF. They come from the device's own USB descriptors, through name formats compiled into the driver such as `%s MIDI %s` [S:local strings; I].
- **License record** (created 2024-11-13) [S:local, INF comments]:
  - Thesycon customer number 1629; options "Version Platform VidPid"; locked to driver version 5.72; USB only; Windows x86 and x64.
  - It lists 2048 licensed VID/PID pairs: VID 1C75 with PIDs 0100–02FF, 0400–06FF, 2200–22FF, 4200–42FF and AF00–AFFF.
  - The AF range appears to be Arturia's MiniFuse audio interfaces [I; S: drivermax listing for VID_1C75&PID_AF80].
  - The binary refuses to load outside this record ("Driver not licensed for this USB VID/PID.", "License not valid for current driver version.") [S:local strings]. So Arturia can't just drop in a newer Thesycon binary without a new license record [I].
- **Signing:** catalog-signed by "Microsoft Windows Hardware Compatibility Publisher"; pnputil shows the attributes "Universal, Attested" [S:local]. "Attested" means submitted through Microsoft's attestation channel rather than full Windows hardware-lab (HLK) testing [I, general knowledge of Microsoft's program].

## 3. The binaries [S:local: pefile, Get-AuthenticodeSignature, string extraction; no disassembly]

| File | What it is | Build (PE timestamp) | Mode and framework | What it imports |
|---|---|---|---|---|
| `arturiausbmidi.sys`, 434,320 B, SHA256 080DCD22…0783 | TUSBAudio Class Driver 5.72.0.0, x64 | 2024-11-12 06:58 UTC | Kernel; **classic WDM** (the older hand-written driver model, no KMDF framework imports); USB bus driver for its own KS child | Core kernel calls for interrupt-time callbacks (DPCs), timers, work items, IRP allocate/reuse/cancel, remove locks, basic power handling (`PoRequestPowerIrp`/`PoSetPowerState`), thread-priority control, `IoWriteErrorLogEntry`, `IoInvalidateDeviceRelations`; `KeQueryPerformanceCounter`; only `USBD_CreateConfigurationRequestEx` from the USB library (transfer requests go down by hand) |
| `arturiausbmidiks.sys`, 55,440 B | TUSBAudio Kernel Streaming Driver 5.72.0.0 | 2024-11-12 06:59 UTC | Kernel; **AVStream** minidriver (Microsoft's kernel-streaming framework) | ks.sys pin and stream-pointer functions; synchronous requests to its parent driver |
| `arturiausbmidiapi.dll` (x86) and `arturiausbmidiapi_x64.dll` | TUSBAudio API DLL 5.72.0.0, registered as a COM in-process server | 2024-11-12 | User mode | Reaches the driver through `DeviceIoControl` on the private interface; 83 exports (below) |
| `tllegacysetupaddon.exe` | "TL-Installer Legacy Setup Add-on" 1.23.0.0, CompanyName "ToriLogic GmbH & Co. KG" | 2024-06-13 | Installer helper | — |

- **No MIDI services plug-in and no user-mode MIDI data path.** MIDI bytes only flow through the KS driver [S:local].
- **The API DLL's 83 exports are control and diagnostics only:**
  - `TUSBAUDIO_QueryDeviceStatistics`, `QueryDriverStatistics` and `ResetDriverStatistics`;
  - `GetUsbConfigDescriptor` and `GetDeviceUsbMode`;
  - `ClassVendorRequestIn/Out` (control requests on the device's control endpoint);
  - DFU firmware functions (`StartDfuDownload`, `StartDfuRevertToFactoryImage` and others);
  - and audio functions [S:local].
  - None sends MIDI data [S:local].
- **Signatures:** all four .sys/.cat files are Valid, catalog-signed by Microsoft's hardware publisher (certificate 2024-10-10 to 2025-10-08, time-stamped) [S:local].
- **No tracing switch.** The kernel driver imports no ETW (Windows' event-tracing system) functions, so there is no trace we can switch on passively. Its only log route is the event log [S:local; I].
- **MIDI tuning knobs exist in the binary but none is set on this machine** [S:local strings and registry]:
  - `MidiInPipeBufferCount`, `MidiOutPipeBufferCount`
  - `MidiParserInputBufferSize`, `MidiParserOutputBufferSize`
  - `MidiUsbFlowControl`
  - `SendResetPipeForMidiInPipe`, `SendResetPipeForMidiOutPipe`
  - `AllowMidiPortSharing`, `AcIfcForMidiRequired`, `IgnoreMidi`
  - `EnableWatchdogStreamingRestart`, `SendRestartDeviceRequest` / `RestartDeviceRequest`
  - `SetInterfaceRequestTimeout`, `AcRequestTimeout_Get/Set`
  - Their defaults and semantics are unknown without Thesycon's documentation or disassembly [I].
- **No power-management knobs.** No string mentions selective suspend, idle, D3 or wake [S:local]. That suggests TUSBAudio doesn't put the USB device to sleep on its own [I; not provable without disassembly].
- **Other details:**
  - It is built for Windows' MIDI-port naming (`midi_%s_%02u_%02u`, `MidiIn_%02u`), uses standard USB-MIDI jack parsing (`TUSB_CLS_AUDIO_MS_MIDI_IN_JACK`), and has class names `MidiFunctionController::GetMidiEndpoint` and `MidiJack::Dump` [S:local].
  - A `KsEnumeratorName` parameter exists but Arturia doesn't set it, which is why the vendor's `TUSBAUDIO_ENUM` name leaks into the hardware ID [S:local; I].

## 4. Registry settings [S:local]

- **Service key `Services\arturiausbmidi`:** Type 1, Start 3, ErrorControl 1, ImagePath in the DriverStore, owner oem22.inf. `ParametersDriver\License` holds the record above. `ParametersDriver\Settings` is empty. `arturiausbmidiks` has only its Enum key.
- **Device hardware key (`Enum\USB\VID_1C75&PID_02CE\…\Device Parameters`):**
  - the INF's seven values, plus `EnumerationRetryCount=0`, `SymbolicName`, `FriendlyDeviceNameString`;
  - Windows' `Ceip` descriptor-validation info;
  - **none of** `EnhancedPowerManagementEnabled`, `SelectiveSuspendEnabled`, `AllowIdleIrpInD3`, `DeviceSelectiveSuspended` or `IdleUsbSelectiveSuspendPolicy`.
  - Those values are read by Microsoft's own USB drivers (composite, WinUSB, HID), and none of them is on this device's stack. So they wouldn't apply even if set [I].
- **Driver key (`Class\{463bf520…}\0000`):** DriverDesc, ProviderName, DriverDate 8-20-2025, DriverVersion 1.7.0.0, InfPath and InfSection. The KS driver key (`Media\0013`) has `Driver=arturiausbmidiks.sys` and `KS=1`.
- **Power state:**
  - The device's power data says it is currently in D0, fully on (capabilities D0, D3, wake-from-D0) [S:local decode].
  - Root hub: `HardResetCount=0`, `LastHubResetPortStatus=0`. Controller: `HCRecoveryCount=0`, `HCRestoreStateFailureCount=0` [S:local values]. My reading is that the hub and controller never recorded a reset or recovery [I].
  - Power plan "USB selective suspend" is Enabled on both AC and DC (scheme alias SCHEME_MIN) [S:local powercfg].
- **Microsoft's other device flags (`usbflags\1C7502CE*`):** `osvc = 0 0`. Windows asked for Microsoft's "OS descriptor" (the device-side way to request WinUSB automatically) and got none [S:local; I]. So WinUSB will never bind to the KeyLab on its own.
- **Platform:**
  - Secure Boot ON;
  - no TESTSIGNING in the boot options;
  - OS 26200.9168 (25H2), the KB5121003 build named in Microsoft MIDI issue #1177 [S:local; S].

## 5. How Windows MIDI Services sees it [S:local: CfgMgr interface properties, registry]

- **Transport plug-in:** `Midi2KSAggregateTransport` (CLSID `{0f273b18-e372-4d95-87ac-c31c3d22e937}`, enabled; transport code "KSA"). Also registered: plain KS, loopback, and **virtual MIDI** (`Midi2VirtualMidiTransport`, `{8feaad91…}`) [S:local].
- **What the service aggregates:** one endpoint over 4 KS pins:
  - `\\?\TUSBAUDIO_ENUM#VID_1C75&PID_02CE&KS#…#{6994ad04-…}\midi_in_00_00`, `midi_in_01_01`, `midi_out_00_00`, `midi_out_01_01`;
  - pin names: "KeyLab 88 mk3 MIDI" (cable 0) and "KeyLab 88 mk3 DAW" (cable 1);
  - manufacturer "Arturia"; a group-terminal-block name table that includes "KeyLab 88 mk3 DAW 2" [S:local].
- **Property meanings:** the format-byte 01 and multi-client=True readings are my mapping of property numbers [I].
- **Data path:** app → midisrv (10.0.26100.7705) → KS aggregate → `arturiausbmidiks` → `arturiausbmidi` → USB bulk pipes [S:local for each hop; I for the chaining].
- **No Windows MIDI Services SDK or tools are installed:** no `C:\Program Files\Windows MIDI Services`, no midi.exe, no mididiag [S:local].
- **Shared input pipe (inference):** both cables almost certainly share one bulk IN pipe and one bulk OUT pipe, as USB-MIDI 1.0 usually does [I]. If so, one stuck cable can stall the other.

## 6. Logs and diagnostics the package ships [S:local]

- **No log files, no diagnostic tool, no tracing.** No "Spy" tool (Thesycon's statistics viewer, which shows MIDI pipe statistics since 5.12 [S: changelog]) and no control panel. The install folder holds only the setup files, the two API DLLs, `custom.ini` (the interface GUID) and SetupFx XML.
- **The only event:** System-log Event 3, Error, "Audio Controller initialization failed.", 124 times since 2026-06-16.
  - One per arrival: 10-21 19:17 and 20:05, 10-22 03:09 and 06:54, 10-26 23:31:45. Nothing in between.
  - Its binary payload is error code `0xE0070003` with final status `0xEE000050`, an internal Thesycon status code.
  - It probably means the audio-control part of TUSBAudio finds no audio function on a MIDI-only device (`AcIfcForMidiRequired` exists) [I].
- **What the gap tells us:** the KeyLab did not drop off the bus or re-enumerate between 10-22 06:54 and the 23:31 power cycle. The hang was silent at the USB level [S:local; I].

## 7. What this says about the hang

- **Stuck pipe: the best fit [I].**
  - The device both sent nothing and took nothing, yet never dropped off the bus. The hub reset and controller recovery counters show nothing (both read 0), and the driver logged nothing [S:local].
  - TUSBAudio has made MIDI reception use USB flow control since 5.12 [S: changelog]: when its buffers fill, it stops reading from the device.
  - Mechanism [I, untested]: if one consumer stops draining, the shared IN pipe stops being read. If the KeyLab's firmware then blocks on its full send queue, it would stop accepting input too. That gives total silence both ways while the screen and keys stay "awake".
  - Equally possible: the firmware stopped draining OUT, and a write with no timeout sits pending. midisrv's KS write has no time limit [S: guide, citing MidiKs.cpp / #1195]. Microsoft's own class driver also sends bulk writes with no timeout [S: microsoft/MIDI `Device.cpp` ~line 3033, `WDF_NO_SEND_OPTIONS`]. So no stack on Windows times out a write the device never accepts.
  - The knobs that look meant for this (`SendResetPipeForMidi*`, `EnableWatchdogStreamingRestart`) are unset [S:local].
- **Power saving: a weak fit [I].**
  - The driver has no idle or selective-suspend parameters [S:local strings], and it is the only function driver, so the power plan's selective-suspend switch has no Microsoft driver to act through [I].
  - The device is in D0 and no resume or reset was recorded [S:local].
  - Caveat: Microsoft's in-box `USBMidi2` driver *does* arm a 15-minute idle suspend [S: `Device.cpp` lines 452–459]. Moving to it adds a power variable the current stack doesn't have.
- **Buffer limits: plausible only as the trigger [I].** The buffer and pipe-count knobs exist but are unset, with defaults unknown [S:local; I]. Frames of 66 bytes don't point to an overflow; an unread or full input buffer feeding the flow-control stall above does.
- **Driver age [S: changelog; I].** Arturia's 5.72 predates these upstream fixes:
  - 6.0.0 (2025-11-27): "USB disconnect handling in MIDI and AC notify pipes".
  - 6.16.0 (2026-06-08): a "race condition on stream stop" fix, and "support devices with only a MIDI streaming interface".
  - 6.20.0 (2026-10-08): "USB MIDI descriptor parsing for SuperSpeed devices".
  - 5.72's own note is just "MIDI handling improvements".
  - None of these describes our hang exactly, but asking Arturia for a build on 6.16 or newer is the cheapest lever.
- **What would separate driver from firmware [I]:**
  - Read the driver's pipe statistics during a hang (`TUSBAUDIO_QueryDeviceStatistics`). That needs Daniel's approval and the statistics structure layout, which isn't public as far as I know.
  - The guide's Disable/Enable step.
  - Running on the 12 V supply and replugging only USB.
  - A driver swap.

## 8. What it would take to build our own driver

Prerequisite for every option: **the KeyLab's USB descriptors**. They aren't stored anywhere on disk [S:local]. TUSBAudio parsed standard USB-MIDI jacks into the four KS pins, and Arturia says the unit is class-compliant on Mac. So the MIDI interface is very likely standard USB-MIDI 1.0 class [I, strong].

The options, from least to most work:

- **A. Use Microsoft's in-box class driver (no code, reversible, about 30 min).**
  - Installed here: `USBMidi2.sys` "USBMidi2-ACX" 10.0.26100.9168, KMDF + ACX, matching `USB\CLASS_01&SUBCLASS_03`; and `usbaudio.sys` (wdma_usb.inf) [S:local].
  - Microsoft documents switching between them [S: microsoft.github.io/MIDI kb/how-to-switch-between-class-drivers].
  - Removing Arturia's binding lets Windows' composite driver split the KeyLab into per-interface nodes (`MI_xx`) [I].
  - It directly tests "is the hang Arturia's driver?".
  - Costs [I]:
    - port names may change, so FL's script and our `arsenal/keylab` name lookup need updating;
    - firmware updates and possibly Analog Lab integration may need Arturia's driver back (the INF has `DFUProtocol=2` and the API exports DFU functions [S:local]);
    - it adds USBMidi2's 15-minute idle suspend.
- **B. A user-mode driver: the "direct to metal, PC does the work" version (I recommend this one) [I].**
  - **Binding:** put WinUSB on the KeyLab. Either pick Windows' own signed winusb.inf manually in Device Manager (no self-signed certificate), or use Zadig/libwdi, which installs a self-signed certificate into the machine trust store. That second route is a security change and Daniel's call.
  - **Our service owns the pipes:**
    - continuous bulk-IN reads that never stop reading, with drop-and-count instead of flow control;
    - bulk-OUT writes with a per-transfer timeout (WinUSB's `PIPE_TRANSFER_TIMEOUT`), then abort pipe, reset pipe, reopen, and finally a hub port cycle;
    - the USB-MIDI 1.0 packet codec (code index numbers, cable 0 MIDI / cable 1 DAW, SysEx split into 3-byte pieces);
    - per-cable queues so one cable can't block the other;
    - a Device Inquiry heartbeat on the DAW cable;
    - counters published to the house dashboard.
  - **FL access:** publish virtual ports through the Windows MIDI Services virtual device transport (registered here [S:local]; the SDK runtime isn't installed [S:local]).
  - **What it buys:** the evidence the guide says we lack (its line 855). We'd see whether a write is NAKed on the wire (the device not draining) or completes with no reply (the firmware's parser), and we'd get automatic recovery.
  - **Effort and risk [I]:** about 1–2 weeks to make it robust. If our service dies, FL loses the keyboard, so it needs a supervisor. Latency is about 1–2 ms. Arturia's driver comes back temporarily for firmware updates.
- **C. A kernel driver of our own [I].**
  - Don't start from scratch: Microsoft's class driver source is MIT-licensed at github.com/microsoft/MIDI `src/in-box/Drivers/USBMIDI2` (KMDF continuous reader with a read-failed callback; idle settings; MIDI 1.0 jack-to-cable mapping) [S]. Fork it and add write timeouts plus recovery.
  - Signing: Secure Boot is ON [S:local], so test-signing needs Secure Boot off plus a boot-option change, both security changes and Daniel's call. Production signing needs attestation through Microsoft Partner Center with an EV certificate (paid, yearly).
  - Also needs the WDK and kernel debugging on a second machine or VM; a bug means a blue screen.
  - Effort: weeks to months. Worth it only if B can't serve FL natively.
- **Not an option: re-using or rebuilding TUSBAudio.** It is commercial and license-locked [S:local]. A clean-room build from the public USB-MIDI 1.0 spec is option C.

## 9. Needs Daniel's approval (nothing done; sizes not checked unless stated)

1. **Descriptor dump with FL closed.** Either a small read-only script using the hub's cached connection data (opens the root hub's handle, not the KeyLab's), or Microsoft USBView (Windows SDK / github.com/microsoft/Windows-driver-samples `usb/usbview`), which sends standard descriptor requests to the device. Thesycon's `tdd.exe` from thesycon.de is the alternative (already on the guide's list).
2. **Calling `arturiausbmidiapi_x64.dll` from ctypes** to read MIDI pipe statistics and the cached configuration descriptor during the next hang. This runs vendor code and opens the device's private interface.
3. **Driver experiments (system changes, Daniel's call):**
   - Set `SendResetPipeForMidiInPipe/OutPipe=1` or `MidiUsbFlowControl`. Semantics and the registry location are inferred.
   - Option A, the class-driver swap.
4. **Windows MIDI Services tools** (MIDI Troubleshooting app, midi.exe, mididiag) from github.com/microsoft/MIDI releases.
5. **For option B:** pyusb from PyPI plus the libusb-1.0 DLL.
6. **Ask Arturia support** for a driver built on TUSBAudio 6.16 or newer, and for Thesycon's Spy tool.

## 10. What I could not determine

- The KeyLab's interface, endpoint and DFU layout, and its USB speed (needs item 1).
- TUSBAudio's defaults for the MIDI knobs, and whether it ever sends the device into suspend (needs disassembly or Thesycon's docs).
- The meaning of status `0xEE000050`.
- The roles of the interfaces `{B68E4562-…}` and `{fd0505c2-d259-42a8-b6a0-92e3849133ca}` on the USB node (strings suggest DFU and "private"/"optional" interfaces) [I].
- Which product PIDs 021B and 02CB are.

Files are in `<scratch>\`:
- `arturiausbmidi.inf.txt`, `arturiausbmidiks.inf.txt` (the INFs decoded to UTF-8)
- `main_strings.txt`, `ks_strings.txt`, `api_strings.txt` (string dumps of the binaries)
- `pe_inspect.py`, `strs.py`, `ifprops.ps1`, `ifprops_full.ps1`, `infgrep.py` (the inspection scripts)

Sources:
- [TUSBAudio history (thesycon.de)](https://www.thesycon.de/usbaudio/TUSBAudio_history.txt)
- [Thesycon v5.12.0 notes (denafrips)](https://www.denafrips.com/single-post/thesycon-driver-v5-12-0)
- [Windows MIDI Services: switching class drivers](https://microsoft.github.io/MIDI/kb/how-to-switch-between-class-drivers/)
- [microsoft/MIDI repo (MIT), USBMIDI2 driver source](https://github.com/microsoft/MIDI)
- [microsoft/MIDI issue #1177](https://github.com/microsoft/MIDI/issues/1177)
- [drivermax: Arturia MiniFuse 1, VID_1C75&PID_AF80](https://www.drivermax.com/Minifuse-1-Arturia-USB-VID-1C75-PID-AF80-1_1_1_0-2022-04-14-4544546-driver.htm)
- Local guide: `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-dev-guidance-and-hang-guide-2026-10-27.md` and `keylab-hang-study-2026-10-26.md`

---

## Lane: building our own path (verbatim)

# Build-our-own lane: what Arturia's KeyLab driver is, and what replacing it would take (KeyLab 88 mk3, 2026-10-27)

## Bottom line

Arturia's "USB MIDI Driver" is a rebadged copy of Thesycon's commercial TUSBAudio driver, version 5.72 from November 2024. It owns the whole KeyLab USB device and reaches the Windows MIDI service through a kernel-streaming child driver. Thesycon has since released 6.20.

Building our own path ranks like this, best first:

1. **(d) Stay on Arturia's driver and harden above it.** Do this now.
2. **(b) Swap to Microsoft's own class driver, with no code.** This is the cheapest experiment that answers "is it Arturia's driver?". It can be undone in minutes, and Microsoft's driver is MIT-licensed open source and already on this PC.
3. **(c) A user-mode WinUSB "driver" plus virtual ports.** This is the real "direct to metal" option and gives the best diagnostics. It takes about 2 to 3 weeks of our work [I] and needs installs and driver binding that Daniel must approve.
4. **(a) A kernel driver of our own.** Not recommended. Secure Boot is on, so we would need test mode or an EV certificate plus Microsoft signing, and a bug crashes the music PC. It would also add nothing that (b) and (c) don't already give.

Grading: [S] = cited source, [S:local] = measured on this machine (read-only), [I] = inference. I ran no vendor binary, touched no device handle, and changed nothing.

## 1. What the Arturia driver tells us (static inspection only)

**Identity**
- `arturiausbmidi.sys` 1.7.0.0 has OriginalFilename `tusbaudio.sys`, product "TUSBAudio Class Driver", file version 5.72.0.0 [S:local].
- Its build path inside the binary is `C:\wrk\prj\_Thesycon\USB\TUSBAudio\_main\bin\Release\x64\tusbaudio.pdb`, and the PE timestamp is 2024-11-12 [S:local].
- The other files follow the same pattern [S:local]:
  - `arturiausbmidiks.sys` is `tusbaudioks.sys`.
  - `arturiausbmidiapi*.dll` is `tusbaudioapi.dll`.
  - `tllegacysetupaddon.exe` is a "TL-Installer" from ToriLogic GmbH.
- The INF carries a Thesycon licence record: "created 2024-11-13", customer 1629, version 5.72, licensed for Arturia's vendor ID (0x1C75) only [S:local].
- Thesycon's current version is 6.20, and 5.72 is past the CVE-2024-25376 fix in 5.68 [S: thesycon.de/eng/usb_audiodriver.shtml]. So Arturia ships a core that is a full major version behind [I].

**Signing**
- Both `.sys` files and both catalogs are signed by "Microsoft Windows Hardware Compatibility Publisher", and pnputil lists them as "Attested" [S:local]. That means attestation signing, not HLK-tested certification.
- The API DLLs and the installer are signed with Arturia SAS's EV certificate from DigiCert [S:local].

**Architecture**
- The main driver is classic WDM, not KMDF. It imports `IoCreateDevice`, `IoAttachDeviceToDeviceStack` and `USBD_CreateConfigurationRequestEx`, and has no WDF import [S:local]. The last of those means it selects the USB configuration itself.
- It binds the whole device `USB\VID_1C75&PID_02CE`, outranking Microsoft's composite driver (`usb.inf` `USB\COMPOSITE`, which normally loads usbccgp): rank 00FF0001 against 00FF2006 [S:local, pnputil]. So no usbccgp ever loads, and every interface belongs to Thesycon.
- It creates the child `TUSBAUDIO_ENUM\...&KS`. That child runs `arturiausbmidiks.sys`, an AVStream minidriver (it imports `KsInitializeDriver`, `KsCreateFilterFactory` and `KsPin*`) [S:local].
- The service endpoint `SWD\MIDISRV\MIDIU_KSA_...` hangs off that child and exposes two ports each way, "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW" [S:local].
- The full chain is: FL → midisrv (its KS Aggregate transport) → Thesycon KS filter → Thesycon WDM driver → USB root hub [S:local].

**Event 3 is benign.** The string "Audio Controller initialization failed." is inside `arturiausbmidi.sys`, next to `IoWriteErrorLogEntry` [S:local]. On a MIDI-only device with no audio streaming, that fits a harmless arrival marker [I]. This confirms the hang guide's reading.

**Firmware update goes through this driver.**
- The INF sets `DFUProtocol=2` for the KeyLab, and the binary has strings for "Register device interface (DFU)" [S:local].
- MIDI Control Center contains a `DFUUpdater` class, a TUSBAudio API wrapper and `TUSBAUDIO_StartDfuDownload` [S:local].
- So firmware updates on Windows almost certainly need Arturia's driver bound [I].
- Analog Lab V.dll and .vst3, and the Arturia Software Center Agent, link the same `TUsbAudioApiDll` wrapper, including the message "Could not find the driver .dll" [S:local]. What they use it for is unknown [I].

**Undocumented tuning knobs.** The driver binary names these registry values: `MidiInPipeBufferCount`, `MidiOutPipeBufferCount`, `MidiUsbFlowControl`, `MidiParserInput/OutputBufferSize`, `SendResetPipeForMidiInPipe`, `SendResetPipeForMidiOutPipe`, `AllowMidiPortSharing`, `SendRestartDeviceRequest`, `EnableWatchdogStreamingRestart` and `AcRequestTimeout_Get/Set` [S:local].
- None is set for the KeyLab today. Its Device Parameters hold only DFUProtocol, InterfaceGUID, KsSampleRateControl and Restore* [S:local].
- What they mean is not public. Thesycon's SDK is for licensees only [S: thesycon.de].

**A statistics API we could call.** The API DLL exports `TUSBAUDIO_QueryDeviceStatistics`, `QueryDriverStatistics`, `ReadDeviceNotification` and `GetUsbConfigDescriptor` [S:local]. Calling them means running a vendor binary, so I didn't. It is an approval item below.

**Small USB facts**
- The hardware ID is `REV_1500`, which is firmware 1.5.0. The `usbflags` history shows earlier revisions 0500, 1101 and 1201 on this PC [S:local].
- `osvc={0,0}`: the KeyLab offers no Microsoft OS descriptor, so WinUSB will never bind to it automatically [S:local; I].
- The instance ID is the device's serial number, so any driver choice follows the device across USB ports [S:local].

**What static inspection cannot tell us**
- The configuration descriptor, meaning the exact interfaces and endpoints. My inference is Audio Control + MIDIStreaming with two cables, plus a DFU interface [I].
- Whether the driver or the firmware hung.

## 2. The four options at a glance

| | Effort [I] | Risk | What breaks | Daniel approves |
|---|---|---|---|---|
| **(d) harden above Arturia** | days (the hub design) | lowest | nothing | the usual hub rollout |
| **(b) Microsoft class driver** | about 30 min, no code | low; undone in minutes | port names, FL bindings, possibly Analog Lab's screen, firmware updates until switched back | driver switch in Device Manager (admin, FL closed) |
| **(c) user-mode WinUSB + virtual ports** | 2-3 weeks including a soak | medium; reversible | everything must go through our process; firmware updates need a switch back; extra installs | driver binding, MIDI Services SDK/Tools install, a supervisor for our process |
| **(a) kernel driver** | weeks (fork) to months (scratch) | high: bugcheck, signing | Secure Boot or money and paperwork | Secure Boot off and test mode, or an EV certificate plus a Partner Center account |

## 3. (a) A kernel-mode USB MIDI driver from scratch

**What it would be**
- Either an AVStream MIDI 1.0 driver, like Thesycon's KS child, reached through midisrv's KSA path.
- Or a UMP kernel-streaming driver like Microsoft's USBMidi2, which is KMDF 1.31 according to its in-box INF [S:local `usbmidi2.inf`].
- Microsoft's version is already MIT-licensed, at `src/in-box/Drivers/USBMIDI2/Driver` (Driver.cpp, Device.cpp, StreamEngine.cpp, ump.h) [S: github.com/microsoft/MIDI, LICENSE]. So "from scratch" really means "fork USBMidi2".

**Toolchain:** Visual Studio 2026 plus WDK 28000, or the EWDK ISO [S: learn.microsoft.com/windows-hardware/drivers/download-the-wdk]. This PC has no kernel headers and no `cl.exe` [S:local].

**Signing**
- Secure Boot is on (`UEFISecureBootEnabled=1`), test signing is off, and HVCI is not running [S:local].
- Test signing needs `bcdedit -set TESTSIGNING ON`. Microsoft's own note says to disable Secure Boot in the BIOS if that is refused, and that Test Mode shows a watermark [S: Learn the-testsigning-boot-configuration-option]. BitLocker reports Off on C: [S:local, shell property].
- Production means attestation through Partner Center with an EV certificate [S: Learn code-signing-reqs, code-signing-attestation]. Microsoft now calls attestation signing "for testing purposes only", and such drivers can't go to Windows Update for retail audiences [S: Learn driver-signing-offerings, 2026-03-23]. Arturia uses this exact route [S:local].
- EV certificates go to organisations [I].

**Risk:** any bug in the kernel stops the whole PC in the middle of a session [I].

**Verdict:** everything we would add here (write timeouts, pipe resets, a watchdog) is available in user mode through WinUSB. Not worth it.

## 4. (b) Microsoft's open-source class driver

**Already on this PC**
- `USBMidi2.sys` (106,496 bytes) matches `USB\CLASS_01&SUBCLASS_03&PROT_00`, `USB\CLASS_01&SUBCLASS_03` and `USB\CLASS_01` [S:local].
- `usbaudio.sys` (`wdma_usb.inf`) matches `USB\CLASS_01` [S:local].
- Microsoft says the new driver "supports both MIDI 2.0 devices as well as MIDI 1.0 devices", but "most MIDI 1.0 devices remain on existing drivers by default" [S: microsoft.github.io/MIDI/overview].
- Microsoft's round-trip numbers: about 1.2 ms on its newer KS path (USBMidi2-ACX), 20-39 µs faster than usbaudio, with similar jitter [S: kb/usb-midi-device-round-trip-measurements].

**Will it work with no code?** Very likely.
- The KeyLab mk3 runs class-compliant on Linux: keys, pads, the DAW port, and the screen through SysEx once port names match [S: forum.arturia.com/t/5294, posts 17, 22-28]. Arturia's product page calls it class-compliant [S, search summary]. Arturia's Windows support pages still say its driver is required [S, via the hang guide].
- Mechanics: Arturia's INF claims the whole device, so first the parent goes to "USB Composite Device" (usbccgp). Windows then groups the consecutive audio-class interfaces into one function [S: Learn support-for-interface-collections]. That function then gets usbaudio.sys or "USBMidi2-ACX", picked by hand in Device Manager (Update driver → Browse → Let me pick) [S: kb/how-to-switch-between-class-drivers].
- To undo it, pick Arturia's "KeyLab 88 mk3" from the same list (`oem22.inf` stays in the driver store) [S:local; I].

**What changes**
- **Port names.** Users on usbaudio.sys saw "keylab 49 mk3" and "MIDIIN2 (keylab 49 mk3)", and their FL integration broke [S: forum.image-line.com/viewtopic.php?t=330816]. Windows MIDI Services can use the device's iJack names or custom names [S: kb/midi1-name-mapping]. The Linux name "KeyLab 61 mk3 KeyLab 61 mk3 MID" suggests the iJack strings are "KeyLab NN mk3 MIDI" and "DAW" [I].
- **Analog Lab.** It needs the exact Windows names for the screen and buttons [S: forum 5294 post 17 and thread summary].
- **FL.** Its saved port settings need redoing [I].
- **Firmware updates.** MCC needs Arturia's driver back [I, from strings].
- **Multi-client** access is fine: the service shares every endpoint between apps [S: overview].
- Windows Update can silently revert the driver choice [S: tools/miditroubleshooter].

**Its diagnostic value:** if the hang comes back on Microsoft's driver, Arturia's driver is cleared and the firmware or service becomes the suspect [I].

**Forking it** is legal under MIT but brings back all of (a)'s signing cost.

**Other routes**
- A midisrv transport plugin (user-mode COM) must be signed or needs Developer Mode, which is off here [S: miditroubleshooter, overview; S:local]. It also runs inside the system service, so a bug there silences all MIDI [I].
- The service fix is already upstream. Repo HEAD has `WriteAbandonablePacketMidiData` with a timeout, `CancelIoEx` and `ConsecutiveWriteTimeoutLimit` [S: `src/in-box/Libs/MidiKs/MidiKs.cpp` HEAD]. Retail Windows still blocks with no limit [S: hang guide].

## 5. (c) A user-mode "driver": WinUSB plus virtual ports

**Binding**
- With no INF and no catalog: Device Manager → Universal Serial Bus devices → "WinUsb Device", then add `DeviceInterfaceGUIDs` under Device Parameters by hand [S: Learn winusb-installation]. The in-box `winusb.inf`, `winusb.sys` and `winusb.dll` are present [S:local].
- Zadig/libwdi instead installs a self-made certificate into the Trusted Root and Trusted Publisher stores [S: libwdi FAQ]. Avoid it.
- We can bind the whole device, or put the parent on usbccgp and bind only the MIDI function [S: Learn; I].
- libusb needs the interface GUID for composite devices [S: libusb wiki Windows].

**Gains**
- **Visibility.** We would see each transfer's status, telling "the device stopped taking data" from "the host stopped reading" without USBPcap [I]. That is the hang guide's M1 question.
- **Bounded writes.** `PIPE_TRANSFER_TIMEOUT` instead of the service's blocking write [S: Learn winusb-functions-for-pipe-policy-modification].
- **Software recovery.** In order:
  1. `WinUsb_AbortPipe`, then `WinUsb_ResetPipe`, which "resets the data toggle and clears the stall condition" [S: Learn].
  2. Reopen the handle.
  3. Disable and re-enable the device, or `IOCTL_USB_HUB_CYCLE_PORT`, which power-cycles the port and needs Administrator [S: Learn].
  4. Unplug the cable as a last resort.

  WinUSB "cannot send an actual reset" by itself [S: libusb wiki]. A firmware hang may survive all of these [I].
- **No selective suspend.** WinUSB suspends only if `DeviceIdleEnabled` is set [S: Learn winusb-power-management]. That removes the T5 power-saving suspect.
- **One owner.** A single process holds the device, so the burst governor becomes truly per device [I].

**Costs**
- WinUSB is exclusive, "no multiple concurrent applications" [S: libusb wiki]. FL, Analog Lab and our tools all go through our process. If it dies, the keyboard goes silent, so it needs a supervisor [I].
- FL still reaches our ports through midisrv [I].
- Virtual ports need the separate SDK runtime. Only apps built on the new SDK can host a Virtual Device; WinMM apps can use it, but port numbers can shift [S: kb/virtual-device-app].
  - The alternative is a loopback pair, made in the MIDI Settings app [S: kb/virtual-basic-midi1-loopback].
  - loopMIDI and teVirtualMIDI were broken under Windows MIDI Services in Feb-Mar 2026 [S: forums.steinberg.net/t/1025292]. Their current status is unverified.
- No MIDI Services SDK runtime or tools are installed here; the in-box Loopback and Virtual transports are [S:local registry, System32].
- Firmware updates still need a switch back.
- Latency rises by one user-mode hop. A similar bridge, Perfect-Bluetooth-MIDI-For-Windows (MIT), reports "well under 1 ms" [S: github.com/mayerwin/Perfect-Bluetooth-MIDI-For-Windows].

**Precedents**
- **Perfect-Bluetooth-MIDI-For-Windows:** reads the device itself and publishes a Windows MIDI Services Virtual Device, falling back to loopbacks.
- **Ableton Push 2:** class MIDI plus a bulk display interface driven through libusb, with Zadig on Windows [S: github.com/Ableton/push-interface].
- **NI Maschine Mikro MK3 user-space drivers:** libusb to a virtual MIDI port, on Linux [S: github.com/r00tman/maschine-mikro-mk3-driver].
- **deadsy/libusb midi.go:** a minimal USB-MIDI reader [S].
- The wire format: 4-byte event packets with a cable number and a code index number [S: usb.org midi10.pdf].

**Staged, reversible plan**

| Stage | When | What |
|---|---|---|
| 0 | now, offline | Write and unit-test the packet codec (SysEx framing, cables 0 and 1) and a `ctypes` binding to `winusb.dll`. No installs. |
| 1 | Daniel's call | Read the configuration descriptor: run Thesycon's `GetUsbConfigDescriptor`, or USBPcap. |
| 2 | approval | Do (b) as an A/B soak. |
| 3 | approval, FL closed | Bind WinUSB and bridge to named ports ("KeyLab 88 mk3 MIDI" / "DAW"). Verify keys, pads, SysEx and the screen. |
| 4 | after stage 3 | Supervisor, watchdog, recovery ladder, 7-day soak. |
| any | — | Undo: Device Manager → "KeyLab 88 mk3" (Arturia). |

## 6. (d) Stay on Arturia's driver: what this lane adds

1. **Read Thesycon's statistics** (`TUSBAUDIO_QueryDeviceStatistics` / `QueryDriverStatistics`) as a health signal. Needs approval because it runs a vendor DLL.
2. **Treat `SendResetPipeForMidi*` and `MidiUsbFlowControl` as experiments**, one at a time, with Daniel's sign-off. Their semantics are unknown.
3. **Ask Arturia** whether a driver on the 6.x core exists.
4. **Use `IOCTL_USB_HUB_CYCLE_PORT`** (admin) as a soft power cycle. It works whichever driver is bound [S: Learn].

## Needs Daniel's approval (nothing downloaded or installed)

- **Run Arturia's API DLL**, read-only calls only. Local; vendor binary.
- **Windows MIDI Services Tools**, Preview 12 (2026-10-21), x64 installer 223 MB; Transports 21.7 MB [S: GitHub releases API]. Winget id `Microsoft.WindowsMIDIServicesSDK` [S: search summary]. These are previews; I did not confirm a stable release.
- **pyusb 1.3.1**, 58,465-byte wheel, BSD [S: PyPI]. Optional, since `ctypes` works.
- **libusb-package 1.0.30.0**, Apache-2.0 [S: PyPI]. I did not get its size.
- **A .NET SDK**, only for a C# Virtual Device helper. Only the runtimes are installed [S:local]. I did not check the size.
- **USBPcap 1.5.4.0**, 195,040 bytes, as in the hang guide.
- **For (a) only:** VS 2026 + WDK (several GB [I]), an EV certificate and a Partner Center account. Cost not checked.
- **Device Manager driver switches** for (b) and (c): admin, with FL closed.

Working files (INFs as UTF-8, string dumps, `pe_meta.py`, `strs.py`) are in `<scratch>\drv_build\`.

---

## Lane: the USB-MIDI wire protocol and recovery (verbatim)

**USB wire level for the KeyLab 88 mk3: protocol, flow control, recovery, and what the hang looks like on the wire (lane usb-midi-wire, 2026-10-27)**

**Bottom line.** Below Arturia's driver, the KeyLab is a standard composite USB device. Its USB revision is 0x1500, which matches firmware 1.5.0. It has a serial number and no Microsoft OS descriptors.

- **Arturia's driver is Thesycon's TUSBAudio.** It is the generic "TUSBAudio Class Driver" v5.72.0 (12 Nov 2024), renamed, and it owns the whole device. Its strings show it reads the standard USB-MIDI 1.0 jack descriptors. It exposes four kernel-streaming ports, which Windows MIDI Services groups as 0 "MIDI" and 1 "DAW".
- **The wire format is almost certainly plain USB-MIDI 1.0** with two virtual cables each way: cable 0 is MIDI and cable 1 is DAW.
- **Endpoint sizes, bus speed and the exact jack layout cannot be read from the registry or the INF.** One built-in route with nothing to install exists: an admin-run USB trace with Windows' own logman tool. Other routes are listed for Daniel's approval in section 9.
- **USB flow control is invisible from above.** The device says "not ready" with a NAK handshake. To every software layer that looks like a transfer that never finishes, and by default Windows waits forever on such a transfer.
- **The current Arturia and Windows MIDI stack gives our code nothing at the pipe level.** A program that owned the device through Microsoft's generic WinUSB driver would get timeouts, abort, reset-pipe and flush. With admin rights it could also cycle the port.
- **The hang fits two explanations equally, and rules out two others.** It fits either the KeyLab's USB-MIDI task stopping or the host driver stopping. It rules out USB suspend and data-toggle loss. A 30-second USB trace at the next hang would tell the two remaining cases apart, with nothing installed.

Grades: **[S]** a cited source says it. **[S:local]** a read-only query on this machine shows it. **[I]** my inference.

---

### 1. What this machine shows about the KeyLab's USB side

All of this is read-only: PnP, registry, the INF files, PE headers, imports and strings, and pnputil enumeration.

**The device**
- `USB\VID_1C75&PID_02CE\7656…0110`, with hardware ID `USB\VID_1C75&PID_02CE&REV_1500` [S:local].
  - The REV value is bcdDevice from the device descriptor [S: Learn, USB device registry entries].
  - 0x1500 matches firmware 1.5.0 [I].
- The instance ID carries a serial number, so the device has an iSerialNumber string [S:local]. That makes a driver choice stick to the device, not to the port [S: Windows MIDI Services KB, "How to switch between class drivers"].
- Its compatible IDs are `USB\DevClass_00&SubClass_00&Prot_00 … USB\COMPOSITE` [S:local]. That is the exact pattern Microsoft gives for a "USB Composite Device" [S: Learn, USB device registry entries example]. So bDeviceClass is 0 and there is more than one interface [I].
- The `usbflags` keys record the revisions this unit has shown up with: 0x0500, 0x1101, 0x1201 and 0x1500 [S:local]. That is the firmware history 1.1.1 → 1.2.1 → 1.5.0; 0x0500 is unknown, possibly the updater or bootloader identity [I].
- `osvc = 00 00` on every revision [S:local]. That means "the device didn't provide a valid response to the Microsoft OS string descriptor request" [S: Learn]. So WinUSB can never bind to it automatically [I].

**The driver stack**
- The device stack is `\Driver\arturiausbmidi | \Driver\ACPI | \Driver\USBHUB3`. There is no usbccgp: Arturia's driver is the function driver for the whole device [S:local].
- The KeyLab sits directly on USB 3 root hub port 8 [S:local]. There is no hub in between, and the speed is unknown.
- Arturia's binaries run from the DriverStore:
  - `arturiausbmidi.sys`: OriginalFilename `tusbaudio.sys`, "TUSBAudio Class Driver" 5.72.0.0. It contains the build marker `THESYCON-VERSION-THESYCON tusbaudio.sys v5.72.0 fre x64 Nov 12 2024` and the debug-symbol path `C:\wrk\prj\_Thesycon\USB\TUSBAudio\...` [S:local].
  - The kernel-streaming child is `tusbaudioks.sys` [S:local].
  - Both are signed by "Microsoft Windows Hardware Compatibility Publisher" [S:local].
  - Thesycon's own history dates 5.72.0 to 12 November 2024: "Chg: MIDI handling improvements" [S: thesycon.de TUSBAudio_history.txt].
- The main driver is a WDM driver, not one built on Microsoft's driver framework [S:local imports]. It has no WDF imports. Its only USBD import is `USBD_CreateConfigurationRequestEx`, so it builds its own USB requests. The kernel-streaming child imports ks.sys (AVStream) [S:local].
- The INF's licence block names the TUSBAudio licence version as v5.72 [S:local, oem22.inf].
- The KeyLab's INF section sets only generic TUSBAudio values: DFUProtocol=2, an InterfaceGUID and audio sample-rate options. **It sets no MIDI parameters**, so every MIDI setting runs at the driver's built-in defaults [S:local, `_AddReg_12`, empty `_AddReg_DriverParameters`].

**MIDI settings the driver can read (names only)**
- The driver's strings name MIDI tunables [S:local strings]:
  - `MidiUsbFlowControl`, `MidiInPipeBufferCount`, `MidiOutPipeBufferCount`
  - `MidiParserInputBufferSize`, `MidiParserOutputBufferSize`
  - `SendResetPipeForMidiInPipe`, `SendResetPipeForMidiOutPipe`
  - `AllowMidiPortSharing`, `IgnoreMidi`, `AcIfcForMidiRequired`
  - `SendRestartDeviceRequest`, and the KS-name formats `midi_%s_%02u_%02u`
- It also has a jack-descriptor dumper: `MidiJack::Dump`, `bJackType`, `iJack`, `TUSB_CLS_AUDIO_MS_MIDI_IN_JACK`, `…JACK_TYPE_EMBEDDED` [S:local].
- Thesycon's history adds context [S]:
  - 5.12.0 (2021): "MIDI RX now uses USB flow control", "several registry parameters for MIDI added" and "MIDI pipe statistics".
  - 6.16.0 (Jun 2026): "support devices with only a MIDI streaming interface".
  - 6.20.0 (Oct 2026): a fix for MIDI descriptor parsing.
  - So Arturia ships a framework about two years old [I].
- The event that fires at every arrival, "Audio Controller initialization failed.", is one of this driver's own strings [S:local]. It is probably the audio half failing harmlessly on a MIDI-only device [I].

**Arturia's user-mode API**
- `C:\Program Files\Arturia\USBMidiDriver\x64\arturiausbmidiapi_x64.dll` is Thesycon's "TUSBAudio API DLL" 5.72 [S:local].
- Its exports include [S:local]:
  - `TUSBAUDIO_GetUsbConfigDescriptor` and `TUSBAUDIO_GetDeviceUsbMode`
  - `TUSBAUDIO_QueryDeviceStatistics`
  - `TUSBAUDIO_ClassVendorRequestIn/Out`
  - the DFU (firmware update) functions
- Nothing was called.

**The Windows side**
- The kernel-streaming child has four filter interfaces: `midi_in_00_00` and `midi_out_00_00` ("KeyLab 88 mk3 MIDI"), and `midi_in_01_01` and `midi_out_01_01` ("KeyLab 88 mk3 DAW") [S:local, pnputil /enum-interfaces].
- Windows MIDI Services' endpoint properties map them as follows [S:local, CM interface properties]:
  - its port map sends both `*_00_00` pins to group 0 and both `*_01_01` pins to group 1;
  - its group terminal blocks name group 0 "KeyLab 88 mk3 MIDI" and group 1 "KeyLab 88 mk3 DAW 2";
  - the transport is "KSA", the manufacturer "Arturia".
- The WinMM ports `…_0_x` use interface class {504BE32C…} and `…_1_x` use {6DC23320…} [S:local]. Those are the input and output port classes respectively [I].

### 2. The wire: USB-MIDI 1.0 event packets

**The packet**
- Every message travels as 32-bit packets [S: USB-IF, Device Class Definition for MIDI Devices 1.0, §4]:
  - byte 0 is the Cable Number in the high nibble and the Code Index Number (CIN) in the low nibble;
  - bytes 1-3 carry the MIDI bytes;
  - unused bytes are zero.
- The cable number (0x0-0xF) is "the number assignment of the Embedded MIDI Jack associated with the endpoint" [S: spec §4, via search excerpt].
- An endpoint lists its jacks in its class-specific MS endpoint descriptor, through `bNumEmbMIDIJack` and `baAssocJackID[]` [S: spec §6.2.2; TinyUSB `midi.h` struct]. Cable N is the Nth jack in that list [S: spec].
- The MIDIStreaming interface is class 01h, subclass 03h. It sits behind an AudioControl interface [S: spec]. Thesycon 5.20 made the AudioControl interface optional [S: history].

**The CIN table and data lengths** [S: spec Table 4-1; corroborated by Linux `snd_usbmidi_cin_length[] = {0,0,2,3,3,1,2,3,3,3,3,3,2,2,3,1}` and TinyUSB's enum]

| CIN | Meaning | MIDI bytes carried |
|---|---|---|
| 0x0, 0x1 | Reserved | – |
| 0x2 | Two-byte system common message | 2 |
| 0x3 | Three-byte system common message | 3 |
| **0x4** | **SysEx starts or continues** | 3 |
| **0x5** | **SysEx ends with one byte**, or a one-byte system common message | 1 |
| **0x6** | **SysEx ends with two bytes** | 2 |
| **0x7** | **SysEx ends with three bytes** | 3 |
| 0x8-0xE | Note off, note on, poly pressure, control change, program change, channel pressure, pitch bend | 3 or 2 |
| 0xF | Single byte | 1 |

**How SysEx is split.** Linux's encoder buffers bytes in threes. It emits `cable|0x4` packets, then closes with `0x5` (F7 alone), `0x6` (x F7) or `0x7` (x y F7), depending on where the F7 falls [S: Linux `sound/usb/midi.c`, `snd_usbmidi_transmit_byte`].

**Our real messages on cable 1 (DAW)** [I, applying the spec]
- Device Inquiry `F0 7E 7F 06 01 F7` becomes `14 F0 7E 7F | 17 06 01 F7`: 8 bytes on the wire.
- LED pad 82 blue becomes `14 F0 00 20 | 14 6B 7F 42 | 14 00 02 03 | 14 52 00 00 | 17 7F 00 F7`: 20 bytes.
- A 66-byte screen frame is 22 packets: 88 bytes.
- The 17-byte identity reply comes back as 5 × CIN 4 plus 1 × CIN 6: 24 bytes.
- A DAW pad press on the input side would be `19 99 00 7F`.

**Packing and strictness**
- One bulk transfer carries several packets, up to the endpoint's maximum packet size [S: search excerpt of the spec].
- Linux fills each output transfer round-robin across cables, up to `wMaxPacketSize` [S: midi.c, `snd_usbmidi_standard_output`, `max_transfer = usb_maxpacket()`]. So cables can be interleaved packet by packet inside one transfer, and the device must keep separate SysEx state per cable [I].
- Windows' in-box driver throws away a transfer whose length is not a multiple of 4 ("buf_len must be a multiple of four", Clemens Ladisch, 2022-08-11) [S: midi.org community thread]. Our own parser should consume whole 4-byte groups and carry any remainder, not drop the transfer [I].

### 3. The two cables: what is confirmed and what is inferred

**Confirmed**
- Two ports each way, named MIDI and DAW, each its own kernel-streaming filter, mapped to groups 0 and 1 [S:local].
- The driver parses standard embedded-jack descriptors [S:local strings].
- On Linux the 61 mk3 shows two ports whose names derive from iJack strings, "KeyLab 61 mk3 KeyLab 61 mk3 MID" and "…DAW" [S: forum.arturia.com/t/5294 post 17]. Linux builds those names as `"%s %s"` from the card name plus the iJack string, in a 32-byte buffer [S: midi.c]. The cut at 31 characters means the jack strings themselves are "KeyLab 61 mk3 MIDI" and "KeyLab 61 mk3 DAW" [I].
- The DAW port's pad press arrived as `99 00 7F` on the DAW input [S: hang guide].

**Inferred**
- The most likely layout is one bulk OUT and one bulk IN endpoint, each carrying two embedded jacks: cable 0 = MIDI, cable 1 = DAW [I]. The kernel-streaming reference strings `…_01_01` fit "port 1, cable 1" [I, moderate].
- I cannot rule out two endpoint pairs with one cable each without the descriptor [I].
- The 5-pin DIN In and Out are routed inside the unit by its MIDI Thru setting, not exposed as a third USB cable. Only two ports appear [S:local; S: manual pp.58-59 via the guide; I].

**Not readable without touching the device:** endpoint addresses, `wMaxPacketSize`, bInterval, jack IDs, whether the device runs at Full Speed or High Speed, and what the other interfaces are (DFU is likely, given DFUProtocol=2 and the DFU strings [I]). See section 9.

### 4. Speed and bandwidth (why USB is never the bottleneck)

- Full Speed bulk packets are at most 64 bytes; High Speed bulk packets go up to 512 bytes. Bulk transfers have CRC and retries but "no guarantee of bandwidth or minimum latency" [S: beyondlogic.org USB in a NutShell, chapter 4].
- Even one 64-byte packet per 1 ms frame is 16 events, or 48 SysEx bytes per ms, about 48 KB/s. DIN MIDI runs at 31,250 baud, about 3,125 bytes/s, so that is roughly 15 times DIN [I, arithmetic; S: MIDI 1.0 spec for 31.25 kbaud].
- Worked numbers [I]:
  - a 36-LED burst is 720 bytes, about 12 Full Speed packets, about 1-2 ms of bus time;
  - our governor's 12 messages per 100 ms at 15-66 bytes each is about 1.8-7.9 KB/s, roughly 0.6 to 2.5 times DIN;
  - about 190,000 screen frames a day is roughly 17 MB a day out on cable 1.

### 5. Flow control, and how a stuck pipe looks to the host

**The handshakes**
- On a bulk OUT, the device answers NAK if its buffer is still full and STALL if the endpoint is halted [S: beyondlogic chapter 4].
- On a bulk IN, the device answers NAK when it has no data, or STALL [S: beyondlogic].
- **NAK is not an error.** The host controller just keeps retrying, so a device that stops draining shows up only as a transfer that never completes [I].
- Software capture (USBPcap, usbmon, ETW) sees transfer requests, not handshakes. "The individual packets as described in USB 2.0 Specification Chapter 8 are not possible to capture with software sniffers" [S: wiki.wireshark.org CaptureSetup/USB]. Seeing NAKs takes a hardware analyzer [S: same page].

**How WinUSB treats these cases**
- `PIPE_TRANSFER_TIMEOUT` defaults to 0 for bulk, meaning "transfers won't time out … the transfer waits indefinitely until it's manually canceled or the transfer completes" [S: Learn, WinUSB pipe policy].
- With `AUTO_CLEAR_STALL` off, "all transfers that arrive to the endpoint after the stalled transfer fail until the caller manually resets the endpoint's pipe" [S: same].

**Data toggle loss heals itself**
- A data-toggle mismatch costs one packet, which is acknowledged and then discarded; both ends then resynchronise [S: USB 2.0 §8.6, cited from memory].
- A real case of silent loss: M-Audio Keystation Mini 32 MK3 on a Raspberry Pi. The cause was the host controller's NAK-holdoff polling delays combined with a small device buffer [S: github.com/raspberrypi/linux #4986].

**The current Thesycon stack**
- Since 5.12, "MIDI RX now uses USB flow control" [S: history]. So when its receive buffers fill, the driver stops reading the IN endpoint and pushes back on the device rather than dropping data [I].
- Its output buffers (`MidiParserOutputBufferSize`, `MidiOutPipeBufferCount`) hide a NAKing device from the layers above until they fill [I].
- Only then would Windows MIDI Services' 1 s send wait fail a WinMM send with error 1 [S: hang guide, MidiXProc]. Before that, sends return 0 and nothing lands [I].
- Windows logs nothing for a NAK-forever device [S:local: no event, per the guide].

**A robust host, for reference (Linux)** [S: midi.c]
- 7 IN and 7 OUT transfers in flight.
- On an IN error of `-EPROTO`, `-ETIME` or `-EILSEQ`, it waits `HZ/10` (100 ms) and resubmits.
- Drain waits 50 ms.
- It never times out a pending OUT transfer [I, from the code shown].

### 6. Detecting and clearing a stuck pipe from user mode

**With today's stack (Arturia driver → kernel streaming → midisrv → WinMM)**
- User mode has no pipe-level handle. It can only open, close, send and receive.
- Detecting a stall needs the end-to-end probe, the Device Inquiry [S: hang study].
- Clearing it is coarse: restart midisrv (admin), disable and re-enable the device (admin), or replug.
- The Thesycon API exports show no pipe-reset function [S:local exports; I].

**With a program that owns the device through WinUSB**
- **Detect:** set `PIPE_TRANSFER_TIMEOUT` on OUT and IN pipes. "When the timer exceeds the set time-out interval, the request is canceled"; time spent queued inside WinUSB doesn't count [S: Learn, pipe policy].
- **Cancel:** `WinUsb_AbortPipe` "aborts all of the pending transfers for a pipe. This is a synchronous operation" [S: Learn].
- **Clear a halt:** `WinUsb_ResetPipe` "resets the data toggle and clears the stall condition on a pipe" [S: Learn]. Underneath, the stack sends CLEAR_FEATURE(ENDPOINT_HALT) to the device and resets the host-side toggle to 0 [S: Learn, "How to recover from USB pipe errors"]. Or turn on `AUTO_CLEAR_STALL` for IN pipes [S].
- **Discard cached input:** `WinUsb_FlushPipe` "discards any data that is cached in a pipe" [S: Learn]. libusb notes that FlushPipe "seems to fail on OUT pipes" [S: libusb `windows_winusb.c`].
- **Throughput:** `RAW_IO` for several reads in flight (buffer a multiple of the max packet size) [S: Learn]. `RESET_PIPE_ON_RESUME` if suspend is ever allowed [S].

**Microsoft's escalation order** is cancel → reset pipe → reset port → cycle port, and "perform more complex operations … only if it's necessary". A port reset re-enumerates and keeps the configuration. A cycle port is "similar to the device that is unplugged and plugged back … except the device isn't disconnected electrically", and PnP rebuilds the device node. On a composite device both affect every function [S: Learn, "How to recover from USB pipe errors"].

**Privileges**
- WinUSB can't reset or cycle the port: "WinUSB does not support host-initiated reset port and cycle port operations". libusb's reset therefore aborts, flushes and resets each pipe [S: libusb, quoting Microsoft's WinUSB paper].
- From user mode, the port can be cycled with `IOCTL_USB_HUB_CYCLE_PORT` sent to the hub. It is "supported on Windows 8 and later … if the caller is running as Administrator" [S: Learn]. That page says it "power-cycles the port", while the recovery page says not electrically. Whether power actually drops depends on the hub hardware [I].
- Device Manager Disable/Enable "causes the bus driver to reset the device" [S: Learn, same page]. It needs admin [I].
- On Daniel's USB-powered unit, a cable replug is the only true power cut [S: hang study].

### 7. How fast SysEx can safely flow

**What others have measured**
- On a 61 mk3 under macOS, with Apple's class driver and not Arturia's: 36 LED packets in one burst froze the unit until a power cycle [S: saxofonbrian/keylab-mk3-sysex, "Send limits"].
- Two screen packets sent back to back race inside the device and one is dropped. Sending byte by byte loses 2-4%. A queue with 60 ms between packets fixes it [S: same, "Sending, in practice"].
- While a list readout is being redrawn, the keyboard stops sending MIDI for about 60 ms of every 100 ms [S: same].
- Arturia's FL script sends about 48 messages at start without trouble [S: hang guide].

**What that says**
- The limit is the firmware's processing, not USB. The burst freeze reproduced on macOS, so it is not caused by Arturia's Windows driver [I].
- If the firmware NAKed whenever its queue was full, USB flow control would have prevented the freeze. More likely it accepts bulk data into a queue that later overflows [I].

**Recommendation [I]**
- Send each SysEx as one complete message [S: saxofonbrian].
- Keep screen frames at least 60 ms apart and the burst cap at no more than 12 per 100 ms, counted across every producer.
- Add a closing check after each burst: send one Device Inquiry and wait for its reply before the next burst. That turns the open-loop governor into closed-loop flow control for 8 bytes out and 24 in.
  - Caveat: it proves the device processed the burst only if the inquiry and the DAW SysEx share one input queue inside the device, which is unknown.
- In a WinUSB transport, also keep at most one OUT transfer of 64 bytes or less pending per pipe, with a 250-1000 ms timeout. A pending write is the device saying it isn't draining.

### 8. The hang at the wire level

**What we saw:** the KeyLab's own interface stayed alive (screen frame held, sleep and wake on a key, pads at resting white). It accepted no host SysEx, sent nothing, Windows logged no event, and only a power cycle cured it [S: hang study, guide].

| USB-level state | OUT side | IN side | What apps see | Fits? |
|---|---|---|---|---|
| H1. The device's USB-MIDI task stopped; its interface task is alive | NAK forever; the transfer stays pending | NAK forever; looks idle | Sends return 0 until the driver's buffers fill, then midisrv error 1; no input; stays enumerated with no PnP event | Yes [I] |
| H2. The device's MIDI processing stalled, but its USB interrupt handler keeps accepting OUT data into an overflowing queue | Completes normally | Silent | Every send returns 0 | Yes; fits best if no `MMRESULT` errors are confirmed [I] |
| H3. The host driver stopped servicing the device (IN not resubmitted after an error, or its worker thread blocked) | Not issued, or stuck in the driver | No IN transfer pending | Sends return 0 or error 1; no input | Yes [I] |
| H4. An endpoint halted and was never cleared | Every transfer fails with STALL | Same | Driver errors | Weak: both directions at once, and nothing logged [I] |
| H5. USB suspend | – | – | – | **No.** A suspended bus-powered device must drop to 2.5 mA, but the pads stayed lit [S: USB 2.0 suspend current, §7.2.3 from memory; I]. Suspend also starts only when the function driver asks for it [S: Learn, USB Selective Suspend] |
| H6. Data-toggle desync | Loses one packet | Loses one packet | Could cut off a SysEx on one cable | **No** as a cause: it heals after one packet and would not stop the keys on cable 0 [I] |
| H7. Re-enumeration or disconnect | – | – | Ports vanish; arrival events | **No:** no events [S:local] |

**What would separate H1, H2 and H3 at the next hang**

1. **Watch for a reboot on Disable/Enable** (ladder step 6). It resets the device on the bus and reloads Arturia's driver [S: Learn].
   - If the KeyLab recovers without its yellow-to-red boot gradient, its main firmware never restarted, so the fault was in the USB layer (the device's USB side or the host driver) [I].
   - If it reboots on the bus reset, this step doesn't separate anything [I].
2. **A built-in USB trace (admin, nothing installed).** Run `logman` with the USBXHCI, UCX and USBHUB3 providers and the HeadersBusTrace keyword, which "shows all USB transfer events" [S: Learn, "How to capture a USB event trace"]. Send one inquiry and press a key during it.
   - H1: the OUT transfer is issued and never completes, with an IN transfer pending.
   - H2: the OUT transfer completes.
   - H3: no IN transfer is pending on the KeyLab [I].
   - The same trace's Rundown events record "the USB descriptors … of connected devices" [S], which also answers section 3.
3. **DIN MIDI Out.** If a DIN device is connected to the KeyLab's MIDI Out and is still played by the keys, the firmware's MIDI generation is alive and only the USB path is dead [I].
4. **Only a hardware USB analyzer** shows NAK versus no polling directly [S: Wireshark wiki].

**Why the watchdog's onset time matters [I].** A counter-wrap bug can't be tested until the onset is known. For example, a 32-bit counter of 125 µs microframes wraps at 6.2 days (3.1 days if signed); a 32-bit millisecond counter wraps at 49.7 days. The onset window currently runs from an unknown last-good time to 10-26 21:18.

### 9. What owning the KeyLab directly would take at the wire level

**Binding (driver install, admin, Daniel's decision; not allowed in this lane)**
- Arturia's driver owns the whole device [S:local], and the device has no Microsoft OS descriptors [S:local], so WinUSB needs an INF and a trusted catalog.
- Zadig and libwdi generate a self-signed certificate and install it into the Trusted Root and Trusted Publisher stores, then destroy the private key [S: libwdi FAQ].
- The path Microsoft recommends is usbccgp for a composite device, with WinUSB on one function [S: Learn, supported USB classes].

**Consequences**
- **Exclusive access.** "WinUSB does not support multiple concurrent applications" [S: libusb wiki, Windows page]. FL, Analog Lab and MIDI Control Center then reach the KeyLab only if our process re-publishes ports.
- **Re-publishing ports.** Windows MIDI Services virtual devices are enabled here (`Midi2VirtualMidiTransport Enabled=1`) [S:local]. The KB says that for virtual devices, WinMM ports "are optionally available", with port-number caveats [S: Windows MIDI Services KB, virtual-device-app].
- **Firmware updates.** Replacing Arturia's driver likely drops MIDI Control Center's Windows update path, which runs through the TUSBAudio DFU API [S:local exports and DFUProtocol; I].

**A cheaper middle step.** Microsoft's in-box drivers (usbaudio.sys, or usbmidi2-acx.sys, which "handles both MIDI 1.0 and MIDI 2.0 devices") can be switched in from Device Manager or the MIDI troubleshooter [S: Windows MIDI Services KB]. The KeyLab is class-compliant on Mac and Linux [S]. This keeps multi-client access through midisrv. Arturia says its driver is needed for Analog Lab and DAW integration [S: manual p.10]; the likely reason is port names [I; S: forum t/5294 post 14, names must match].

**Transport design for an owner process [I; APIs cited above]**
- One process owns both pipes, and every producer sends through it. That also closes the gap left by the per-process governor.
- OUT: one transfer in flight, no more than `wMaxPacketSize`, a timeout, then abort → reset → probe. After three consecutive failures, declare the device wedged and stop writing.
- IN: 2-4 reads in flight with `RAW_IO` and `AUTO_CLEAR_STALL`.
- Parse whole 4-byte packets using the CIN length table, reassembling SysEx per cable.
- To close a dangling SysEx, send `x5 F7 00 00`.
- Liveness: the inquiry check after each burst, plus the age of the oldest pending OUT and of the last IN packet.
- Escalate: cycle port (admin), then a human replug.

### 10. For Daniel's approval (none done)

| What | Source and size | What it gives | Cost or risk |
|---|---|---|---|
| USB trace with logman, Rundown plus HeadersBusTrace | Built into Windows; no download. Output goes to `C:\Windows\Tracing\*.etl` | Full descriptors and bus speed now, read from Windows' own cached data (no bus traffic is my inference). At the next hang, transfer-level evidence | Admin. Use `-ets` so no saved collector remains [I] |
| Call Arturia's own API DLL: `TUSBAUDIO_GetUsbConfigDescriptor`, `GetDeviceUsbMode`, `QueryDeviceStatistics` | Already on disk (`arturiausbmidiapi_x64.dll`, 320,264 bytes) | Descriptors, speed, and maybe MIDI pipe statistics (Thesycon 5.12 added "MIDI pipe statistics") [S; I] | Runs vendor code and opens the driver's private interface. The function signatures are not public [I]. Only while Daniel isn't playing |
| USBView, built from microsoft/Windows-driver-samples `usb/usbview` | GitHub source; size not checked | Descriptor and speed view | It sends GET_DESCRIPTOR requests to the device [I]. Only while Daniel isn't playing |
| USBPcap 1.5.4.0 | github.com/desowin/usbpcap, 195,040 bytes [S: guide] | Transfer-level capture | Installs a kernel filter driver. The ETW trace makes it mostly redundant [I] |
| Thesycon `tdd.exe` descriptor dumper | thesycon.de; size not checked [S: guide] | Descriptors | Vendor binary |
| Plug the KeyLab into a Linux machine: `lsusb -v -d 1c75:02ce` | No download on this PC | The definitive descriptor | Daniel's hands, and the KeyLab out of FL |
| A hardware USB analyzer | Purchase | The only tool that shows NAK versus no polling [S: Wireshark wiki] | Cost |

### 11. Open questions
- Did any send during the hang return an `MMRESULT` error? That separates H1 from H2. It is still open from the guide.
- What are the bus speed and the endpoint layout (one endpoint pair or two)? The trace or the API would answer both.
- Does a USB bus reset reboot the KeyLab's main firmware? The step-6 observation answers this.
- What defaults does Thesycon use for `MidiUsbFlowControl` and the buffer counts? They are not public, and reading them out of the binary would mean disassembly, which this lane forbids.

**What I did:** read-only PnP, registry, INF, pnputil interface enumeration and device-interface property reads; PE headers, imports, exports and strings with pefile; web reading. I opened no device handle or MIDI port, touched nothing in FL, installed and downloaded nothing, and made no repo edits. No web fetch saved a file. My scratch files are in `<scratch>\usbwire\`: UTF-8 copies of the INFs, the decoders, and the property dumps.

**A note on the specs:** I cited the USB-MIDI 1.0 and USB 2.0 section numbers from memory. I did not open those PDFs, because fetching a PDF saves it to disk. The USB-MIDI points were cross-checked against the Linux driver, TinyUSB and a search excerpt of the spec.

**Sources:**
- USB-IF MIDI 1.0 class spec: https://www.usb.org/sites/default/files/midi10.pdf
- Linux USB-MIDI driver: https://github.com/torvalds/linux/blob/master/sound/usb/midi.c
- TinyUSB MIDI header: https://github.com/hathach/tinyusb/blob/master/src/class/midi/midi.h
- Thesycon TUSBAudio history: https://www.thesycon.de/usbaudio/TUSBAudio_history.txt
- WinUSB pipe policies: https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/winusb-functions-for-pipe-policy-modification
- WinUsb_ResetPipe: https://learn.microsoft.com/en-us/windows/win32/api/winusb/nf-winusb-winusb_resetpipe
- WinUsb_AbortPipe: https://learn.microsoft.com/en-us/windows/win32/api/winusb/nf-winusb-winusb_abortpipe
- WinUsb_FlushPipe: https://learn.microsoft.com/en-us/windows/win32/api/winusb/nf-winusb-winusb_flushpipe
- Recovering from USB pipe errors: https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/how-to-recover-from-usb-pipe-errors
- IOCTL_USB_HUB_CYCLE_PORT: https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usbioctl/ni-usbioctl-ioctl_usb_hub_cycle_port
- USB device registry entries: https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/usb-device-specific-registry-settings
- USB device classes included in Windows: https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/supported-usb-classes
- USB selective suspend: https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/usb-selective-suspend
- Capturing a USB event trace: https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/how-to-capture-a-usb-event-trace
- Introduction to WinUSB: https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/introduction-to-winusb-for-developers
- Windows MIDI Services KB: https://microsoft.github.io/MIDI/kb/how-to-switch-between-class-drivers/ and https://microsoft.github.io/MIDI/kb/virtual-device-app/
- libusb WinUSB backend: https://github.com/libusb/libusb/blob/master/libusb/os/windows_winusb.c
- libusb Windows wiki: https://github.com/libusb/libusb/wiki/Windows
- libwdi FAQ: https://github.com/pbatard/libwdi/wiki/FAQ
- Wireshark USB capture: https://wiki.wireshark.org/CaptureSetup/USB
- USB in a NutShell: https://www.beyondlogic.org/usbnutshell/usb3.shtml and https://www.beyondlogic.org/usbnutshell/usb4.shtml
- Raspberry Pi bulk-data loss: https://github.com/raspberrypi/linux/issues/4986
- Windows SysEx alignment thread: https://midi.org/community/midi-specifications/cannot-receive-sysex-messages-via-usb-on-windows-but-it-works-on-mac-os
- Arturia forum, KeyLab mk3 on Linux: https://forum.arturia.com/t/status-of-keylab-mk3-analog-lab-on-linux/5294
- Community SysEx map: https://github.com/saxofonbrian/keylab-mk3-sysex
- Local research: `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-hang-study-2026-10-26.md` and `…\keylab-dev-guidance-and-hang-guide-2026-10-27.md`
