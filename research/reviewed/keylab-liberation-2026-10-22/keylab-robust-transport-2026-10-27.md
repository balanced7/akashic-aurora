# Robust KeyLab transport: the MIDI bug fixes (landed) and the hub transport design (2026-10-27)

Workflow run wf_efc891a3-dd0 (task wwcuj3l2w). Daniel's words (verbatim): "lets start with the bugs, do we have any way of getting around the midi hangs, any more robust communication or if we can find out how the protocol works and what methods of interaction could we set up to deliver messages, perhaps we can bypass some convoluted wrapper and have a more direct to metal approach where more of the heavy lifting is being done by the pc. (just throwing some ideas out)". Track 1 fixed the transport defects the hang guide found (fix -> adversarial verify, two rounds); Track 2 researched the native Windows MIDI Services API, the USB layer and delivery acknowledgements, then designed the hub transport as a revision of draft D0 (docs/library/design/20261022_a16-d0-control-center-hub_3325c3.md). Nothing touched the KeyLab during the run. Verbatim; local paths shortened.

Outcome: round 1 was refused by its verifier (a header the driver still owned could be freed when a caller dropped its MidiOut without closing it, as vj.run did); round 2 (branch worktree-wf_efc891a3-dd0-7, 3dc783b6) passed. Vandor then ran the verifier's hardware check on the real KeyLab with FL open (Device Inquiry only): 30 of 30 identity replies captured whole, 17 bytes, `f0 7e 7f 06 02 00 20 6b 02 00 0a 08 7f 7f 7f 7f f7`; 30 buffers re-queued with no errors; nothing parked; every send done, the slowest Windows call 0.82 ms; every close code 0; the port-wide governor's file counted 30 admits on "KeyLab 88 mk3 DAW". The eight files landed on master by name as fe9f64af. The three test_keylab_fl_script.py failures in the main checkout come from another seat's 71 uncommitted lines in the FL script (the startup hue ramp); the same tests pass against the committed FL script.

---

## The hub transport design (verbatim)

# A16 D0, revision 2: the KeyLab hub as a robust transport

**Status.** This is a draft revision of D0 (`art_20261022_a16-d0-control-center-hub_3325c3`), waiting for Daniel's "that's right". D0's file is a generated projection marked "DO NOT EDIT", so this revision has to land through the doc verbs, not as a hand edit.

**Sources.** It is written on 2026-10-27 from:
- the hang study;
- the guide;
- today's three research lanes: native API, USB layer, and protocol depth;
- my own read-only checks of the repo, plus Microsoft's GitHub read through `gh api` to stdout.

**What this lane did not do.** It never touched the KeyLab, its ports, FL, or ports 8793/8794/8796. It downloaded nothing, installed nothing, and committed nothing.

**Grades.**
- **[S]** a cited source says it.
- **[S:local]** a file, log, registry entry or measurement on this machine says it.
- **[I]** my inference.

---

## The answer first

Daniel asked four things: whether we can get around the MIDI hangs, whether there is more robust communication, how the protocol works, and whether we can skip the wrapper and go direct to the hardware, with the PC doing more of the work.

### 1. We can't make the hang impossible from the PC. We can make it rarer, shorter and loud.

**The likely place it stuck.** The leading suspect is the USB link: Arturia's driver, or the KeyLab's own USB interface [S: guide §3.1, M1].

**The likely trigger.** The leading suspect is days of constant traffic: FL was open from 10-24 to 10-26 while the screen service re-sent frames [S: guide "Start here" 1, §3.2 T1].

**What the hub does about each part:**
- **Rarer.** It sends the device far less.
- **Shorter.** It notices within minutes, not hours. On 10-26 the hang began before about 21:18 and was found at 23:15 [S: guide "Start here" 1].
- **Loud.** It says which recovery step worked, then repaints everything by itself.

### 2. There is no faster protocol hidden under the wrapper.

- At the bottom, the KeyLab speaks plain USB-MIDI 1.0: 4-byte packets on one pair of USB data channels, almost certainly shared by both ports [S: USB-IF MIDI 1.0 class spec §4, via the usb-layer lane; I for the shared pair].
- Our SysEx is already the device's own language.
- The layers in between (Windows MIDI Services and Arturia's driver) relay those packets. They don't translate them into something slower or richer [S: usb-layer lane §2; protocol-depth lane §9].

### 3. Literal "direct to metal" is the wrong trade.

"Direct to metal" in the literal sense means our own USB driver, through WinUSB.

- **What it costs.** It would take the keyboard away from FL, Analog Lab and MIDI Control Center. WinUSB serves one app at a time [S: Learn, WinUSB considerations]. Firmware updates would need Arturia's driver put back first [S:local: the INF sets `DFUProtocol = 2`; MCC imports `TUSBAUDIO_StartDfu*`, per the usb-layer lane].
- **What it would not do.** It cannot stop a hang inside the keyboard. That hang would look the same, just sooner [I].
- **The one thing it would give.** Wire-level visibility. USBPcap gives that passively, with no driver swap [S: guide §5.6].

### 4. "The PC does the heavy lifting" is the right instinct, and the hub is how we do it.

The PC takes over these jobs:
- composing the picture;
- comparing it with what was last sent;
- merging rapid updates so only the newest goes out;
- pacing;
- timing sends to the beat;
- checking every byte;
- watching the device's health;
- recovering;
- remembering what the device should show.

The keyboard receives only short "set this light to this colour" packets, and only for elements that changed. Its processor is the scarce resource, not the USB bus: a 66-byte screen frame is 88 bytes on the wire [I: usb-layer lane arithmetic].

### 5. One lower-layer move is worth making, as an experiment.

- **What.** Swap Arturia's driver for Microsoft's open-source MIDI class driver (MIT-licensed, already on this PC, never used) [S:local: `C:\Windows\INF\usbmidi2.inf`, per the usb-layer lane].
- **How.** Run it as an A/B soak test, after the watchdog exists to time a hang.
- **Why.** It removes the top suspect, Arturia's driver. Under its Arturia name it is Thesycon's TUSBAudio 5.72 [S:local: file version info, usb-layer lane].

### 6. Recommendation: Path A

1. **Now.** Harden our current Windows API (WinMM) and put it inside the hub, behind a seam that lets the transport be swapped later. Nothing to install.
2. **Later.** The native Windows MIDI Services API, proven first on Windows' built-in test loopbacks, once Daniel approves the downloads.
3. **After a baseline soak.** The class driver, as a single controlled experiment.
4. **Never.** WinUSB.

Section 6 gives the build slices with receipts.

---

## 1. What changed since D0 was drafted on 2026-10-22

| Finding | Source | What it changes in D0 |
|---|---|---|
| The KeyLab can hang silently. It takes no host SysEx and sends nothing, while its menus, sleep and wake still work. Only a power cycle cleared it | [S:local] hang study, "What it tells us" 1; guide §1 table L0 | D0 had no liveness check. The hub needs one |
| A healthy KeyLab answers the Device Inquiry every time, within about 10 ms. A hung one answered none | [S:local] hang study 5; protocol-depth lane §1 (`liveness_fresh.txt`) | The inquiry is the heartbeat |
| Drawing pads and screen alongside FL works, as long as we never send a DAW connect | [S:local] hang study, "After recovery", 10-27 00:36 | **Probe P1 is answered: the DAW output is shared.** D8's "exclusive" branch is not needed today |
| The burst governor works per process, not per port. The screen service, the VJ engine, every CLI call and FL each get their own 12 per 100 ms | [S:local] `winmidi.py:95-101`; guide "Start here" 3 | One owner, one budget becomes the hub's first job, as D0 already said |
| `MidiIn` has four defects: `lpData` stops at the first `00`; buffers are never re-queued; the send timeout is silent; close happens in the wrong order | [S:local] `winmidi.py:43, 143-147, 239-247, 267-273`; guide §4.1 | The watchdog would lie without these fixes. They are slice K0 |
| A long-lived holder dies when the device power-cycles. The screen service did. WinMM apps never reconnect on their own | [S:local] hang study 4; [S] microsoft/MIDI #696 | The hub must re-open by itself |
| Port 8794 is now the VJ engine's | [S:local] `vj.py:154`; README `vj` row | The hub needs another port. I propose 8798; no live code uses it [S:local: grep of `arsenal/` and `scripts/`]. Daniel picks |
| D0's clean exit sends `daw_connect(False)`. With FL open, that clears FL's lights | [S:local] D0 line 111; Rill's lesson 10-26 21:40 | Disconnect only if the hub made the connection |
| D0's 2-second blackout watchdog opens the port itself. That makes a second writer, painting into a link that may be the thing that hung | [S:local] D0 line 113; protocol-depth lane §6 gap 4 | Replace it with a supervisor plus a shared lock (§4.13) |
| Our caches mark a pad "shown" when the send returns 0. During a hang they believe the pads are painted | [S:local] `ledframe.py:37-41`; protocol-depth lane §4 | Track "sent in this epoch", never "shown". Repaint on every epoch (§4.6) |
| Our FL script's header says it "never colours a pad", but its `OnInit` paints a hue ramp. The working tree also holds an uncommitted change to that file | [S:local] `fl/device_AuroraKeyLab.py` header lines 21-22 against `OnInit` 297-310; guide "Start here" 4; `git status` | A D8 dependency: under the hub, the script must not paint pads |
| The in-box `Windows.Devices.Midi2` API now ships in **2027**, not late November 2026 | [S] microsoft/MIDI release notes, inbox-preview-12 (2026-10-21): "Release timing in the docs now says 'in 2027'"; `docs/kb/porting-midi-libraries.md` line 20 | The native API is a later backend, not the foundation |

---

## 2. How the protocol works, layer by layer

```
 our producers: VJ engine, screen readout, CLI, Rill, pages
        |  (today: each opens the port itself; after this design: each talks to the hub)
        v
 [hub: compose, compare, merge, pace, schedule, check, watch, recover]   <- the PC's heavy lifting
        |  WinMM (winmm.dll -> wdmaud2.drv)              <- our ctypes code calls this
        v
 Windows MIDI Service (midisrv), "kernel streaming aggregate" path    <- shared with FL
        v
 Arturia kernel-streaming driver  ->  Arturia USB driver (Thesycon TUSBAudio 5.72)
        v
 USB root hub, port 8, no hub in between  ->  KeyLab firmware 1.5.0
```

Sources for the stack: [S:local: usb-layer lane §1, from PnP, `pnputil` and file versions]. Firmware 1.5.0 also matches `REV_1500` in the hardware ID [S:local].

**What travels.** Arturia SysEx: `F0 00 20 6B 7F 42 <command> <patch> <type> ... F7`. The type byte means:
- 00 properties;
- 03 LED;
- 04 screen;
- 05 connection.

[S: Arturia's `ParamId.py:25-33`, facts only; protocol-depth lane §1]

**What comes back.**
- **The Device Inquiry reply.** It is 17 bytes, `F0 7E 7F 06 02 00 20 6B 02 00 0A <model> v v v v F7`, with model `08` for the 88 [S:local; S: Bitwig `MidiProcessor.java:130`].
- **Your own playing:** keys, pads and controls.
- **Nothing else that we know of.** There is no acknowledgement, no error reply and no state dump for LED, screen or connect writes [S, by absence across Arturia's FL script, Bitwig and saxofonbrian; protocol-depth lane §1-2].

**A detail worth knowing.** FL stores a different identity reply per port: `…08 7F 7F 7F 7F` on DAW and `…08 3C 01 01 01` on MIDI [S:local: FL registry, usb-layer lane]. So the reply may tell us which port answered [I; experiments E4/E8].

**The keyboard has no MIDI 2.0 features.** It is a MIDI 1.0 device behind a vendor driver, so there are no property reads and no capability inquiry [I: it rides the path Windows uses for MIDI 1.0 drivers, per the native-api lane].

**So "robust communication" has to be state-based delivery, run from the PC [S: protocol-depth lane §7]:**
- the PC holds the truth about what should be on the device;
- it sends absolute "set" packets, which are always safe to repeat;
- it uses the inquiry as a heartbeat and as an end-of-batch marker;
- it repaints the whole picture whenever the device may have lost it.

---

## 3. The transport options, ranked

| Rank | Option | Helps against the hang itself? | Helps us see and survive it? | Effort | Risk | What Daniel approves |
|---|---|---|---|---|---|---|
| **1** | **A. WinMM hardened, inside the hub** (fix the 4 `winmidi.py` defects; one owner; watchdog; re-open; repaint) | Indirectly: one writer and a traffic diet target T1 and T2, the leading triggers [S: guide §3.2; I] | Yes: watchdog, onset window, automatic re-open and repaint [I] | Small to medium; code only | Low | Nothing to install. His presence for hardware drills |
| **2** | **B. The native Windows MIDI Services API** (`Windows.Devices.Midi2`), through the preview binaries and a PyWinRT 4 binding in its own environment | No. Same service, same Arturia driver path underneath. The KeyLab's endpoint sits directly on Arturia's kernel-streaming device [S:local: native-api lane §3-4] | More than WinMM, all on the PC side: automatic reconnect, device watcher, send-result flags, a ping of the service itself, a list of which apps hold the KeyLab, service timestamps, sends scheduled by the service [S: native-api lane §3] | Medium. The binding's coverage of the calls we need is unknown until it is generated [S: PyWinRT 4.0 notes] | Medium. Microsoft makes "no guarantee" the preview binaries match the service now in Windows (the midisrv here dates from August); the go-live licence has conditions; the in-box version is 2027 [S: Preview 11 and 12 notes] | Downloads: the API nupkg (102,998,997 bytes), PyWinRT 4.0.2 (681,939 bytes), a new virtual environment with `winrt-runtime` 4.x wheels [S: native-api lane §7] |
| **3** | **C. Microsoft's class driver in place of Arturia's** (an experiment, not a transport) | **Possibly.** It removes the top suspect. A hang-free soak points at Arturia's driver; the same hang points at the firmware or the service [I] | The driver is open source, so a hang on it can be read in code [S:local: MIT header in `usbmidi2.inf`] | Small in code. Daniel's hands in Device Manager, FL closed | Medium. Port names may change, which means FL's two script assignments and Analog Lab's screen link. MCC and firmware updates need Arturia's driver back. Any Arturia installer puts Arturia's driver back [S: usb-layer lane §4] | The driver switch, the revert plan, and one soak |
| 3b | **D. Legacy API mode** (removes midisrv from the path; an experiment for the "service" hypothesis, M2) | Possibly, if the service is the culprit [I] | No new signals | Small. A registry value plus a restart | Medium. Machine-wide. Two apps sharing one output depends on Arturia's driver [S: usb-layer lane §3 a4]. In this mode `midiOutReset` sends about 2,064 messages, so **the hub must never call it** [S: Learn `midiOutReset`; usb-layer lane] | Registry change plus restart; reversible |
| **4** | **E. WinUSB direct, through Zadig** | No. A firmware hang looks identical [I] | Wire visibility, which USBPcap gives without the swap [S: guide §5.6] | Large. We would write our own USB-MIDI host and re-publish two virtual port pairs, which needs the 2027 API or a third-party virtual-MIDI driver [S: usb-layer lane §5] | High. FL, Analog Lab, MCC and the piano page lose the keyboard. One app at a time. Zadig installs a self-signed root certificate [S: Zadig wiki; Learn] | Driver swap plus a system trust change. **Not recommended** |

**Recommendation.**
- **Build A now.** The hub talks to a small *transport* seam (§4.5), so B can replace WinMM later without touching anything above it.
- **Run B's proof on Windows' test loopbacks** once Daniel approves the downloads (P1-P3 in the native-api lane never touch the KeyLab). Adopt it when it passes, or when Windows ships it in 2027.
- **Run C, or D, as one controlled experiment** after slice K5 has given a baseline soak. Never stack two changes, and never stack either with the USB selective-suspend change [S: usb-layer lane §7.3].

---

## 4. The design

### 4.1 The shape

```
 producers ----HTTP/SSE on 127.0.0.1---->  HUB (one process, one lock)
   VJ engine (pads)                         |- surfaces: 12 pads, 34 buttons, screen, popup, 8 labels
   screen readout (chord/BPM)               |- compositor (D0's theme / mode / overlay / alert layers)
   CLI verbs (led, pad, screen ...)         |- dirty tracking + latest-wins slots
   other seats (Rill), MCP door, pages      |- ONE send pump -> ONE governor -> transport seam
                                            |- input plane: both KeyLab inputs -> control events on SSE
                                            |- watchdog: inquiry heartbeat, USB/port watcher, FL watcher
                                            '- ladder, receipts, odometer, health
```

### 4.2 One owner

- **One process.** `py -m arsenal.keylab serve` starts the hub, which holds a Windows named lock (a mutex) called `Local\AuroraKeyLab.DAWOut` for its whole life [I].
  - A second hub finds the lock taken and refuses, naming the holder from the hub's status file (D0 R0.1 kept).
  - Any house tool that must write directly (a CLI verb with no hub running, or a bench probe) takes the same lock first. **So two house processes can never write at once, hub or not** [I]. That closes the per-process governor gap even in direct mode.
- **What it owns.** The hub opens:
  - the DAW output (all SysEx);
  - both inputs (DAW and MIDI).

  It opens the MIDI output only on demand, for the note verb.
- **What it doesn't own.** FL's script and the piano page's Web MIDI are not ours. Windows MIDI Services lets several apps share a port [S: microsoft/MIDI `kb/api-back-compat`], and that sharing is measured here: VJ inputs alongside FL [S:local: README `vj` row], and guest drawing alongside FL [S:local: hang study]. So "single owner" means single owner **among our processes**. FL co-exists under §4.11.
- **The keys stay where they are** (D0 R0.10 kept). The hub's input listener sits beside the piano page; it does not replace it. That is probe P25, still open.

### 4.3 How producers talk to the hub

**The wire.** HTTP + SSE on `127.0.0.1:<port>`: the house idiom, standard library only. Browser pages, Python, curl and the MCP door can all reach it, which a Windows named pipe could not do for pages [I]. CORS is loopback only, and the server binds to 127.0.0.1 (D0 R0.8 kept).

**The routes:**
- `POST /api/intent`: claim and release a lease (D1), and set a layer's surfaces. The body names absolute surface states, never packets:
  - `{"layer": "overlay", "token": 17, "pads": [12 colours or null], "buttons": {"play": "#ff0000"}, "screen": {"layout": "f2l", "line1": "…", "line2": "…"}, "labels": [...], "at": <PC clock time, optional>}`
  - A null clears that element from the layer. `at` asks for the change to go out at a given time, for beat-locked frames.
  - Already-built screen frames are accepted as `{"frame_hex": …}` only if `screen.check()` passes, which refuses non-screen packets, data bytes above 0x7F, and screens 38, 43 and 44 [S:local: `screen.py:391-402`].
- `GET /api/events` (SSE), carrying:
  - control events (D0's input plane, unchanged);
  - `health` changes;
  - `epoch` (repaint) events;
  - lease changes.
- `GET /api/state` and `GET /api/health`: the state machine (§4.7), the last reply, the last input, the session owner, whether FL is running, the epoch number, the counters, and the last 20 send results.
- `POST /api/probe`: run an inquiry now, at most once every 30 s per client. It returns whether there was a reply, its latency, and the reply bytes.
- `POST /api/raw`: for bench work only. It needs a "bench" lease. It runs the same byte checks, plus a refusal of the `21 03 40` configuration-write family, which throws the unit into User mode [S: saxofonbrian, via the protocol-depth lane]. It goes through the same governor and is logged.

**How each producer moves over:**
- **VJ engine.** Its `PadPainter` sink becomes a hub client in place of `W.MidiOut(prefer="daw")` (`vj.py:2602`). Its own `POST /api/pads` on 8794 keeps working by forwarding to the hub [I].
- **Screen readout.** `keylab screen --live` becomes a client that posts screen states.
- **CLI verbs.** Each verb checks `GET /api/health` with a 200 ms timeout. If the hub answers, the verb goes through it. If not, it opens directly under the lock (today's behaviour). `--direct` forces direct.
- **Rill and other seats.** HTTP, or the MCP door (D0.5, which holds no handle).
- **Inputs.** Inputs can be shared and are read-only, so the VJ engine may keep its own input listeners at first. **It moves to the hub's event stream only if the extra latency is under 2 ms at p95** (a receipt in K3). The robustness payoff is that only the hub then needs re-open logic after a power cycle [I; S: #696].

### 4.4 Surfaces, slots and latest-wins

**Every element the device shows is a slot:**
- 12 DAW-bank pads (ids 82-93) [S:local: README:31];
- 34 button LEDs (ids 0-33) [S:local: README; guide L6];
- 1 persistent screen;
- 1 popup, which expires after about 1 s [S:local: README:35];
- 8 footer labels. Their LEDs can only be set through the footer packets `00 02 04 <id>` [S: saxofonbrian "Screen buttons", via the protocol-depth lane].

**What each slot holds:**
- `wanted`: what should show, after composing D0's four layers (theme, mode, overlay, alert);
- `sent_epoch` and `sent_value`: what was sent in the current epoch;
- `dirty`: wanted differs from what was sent in this epoch;
- counters.

**How updates behave:**
- **Latest wins.** A new `wanted` simply overwrites the old one, and the overwrite is counted as "coalesced".
- **Only differences go out.** A slot goes out only when it is dirty. That is PadRenderer's diff [S:local: `ledframe.py:32-46`] generalised to every surface.

### 4.5 One budget and one send pump

**One thread is the only caller of `transport.send()`.** Each turn of its loop it:
1. takes the next dirty slot in priority order:
   1. control: the inquiry and handshake;
   2. popup;
   3. persistent screen;
   4. pads;
   5. buttons;
   6. labels.

   With aging, no dirty slot waits more than 500 ms [I];
2. waits for the governor to admit it;
3. sends;
4. records the result.

**The budget:**
- **Ceiling.** At most 12 packets in any 100 ms, for the whole hub [S:local: `governor.py:23-24`; README:32].
- **While FL is running,** the hub drops its own ceiling to 8, leaving 4 for FL's script. This follows the guide's rule of sharing one 12 [S: guide §3 "Ground rules"]; the 8/4 split is [I]. Our FL script paces itself [S:local].
- **Screen spacing.** At least 100 ms between screen packets for now. That is today's tested `min_interval` [S:local: `screen.py:409`]. Saxofonbrian found 60 ms safe, because two back-to-back screen packets race on the device [S: protocol-depth lane §4]. Probe P14 decides.
- **Pad spacing.** At least 3 ms between pad packets, as the VJ engine uses [S:local: `vj.py:1531`].
- **Speed.** Intent in, packet out: p95 under 5 ms when there is budget (D0 R0.9 kept).

**Scheduled sends: the PC doing the timing.**
- An intent with `at` waits in the pump until that moment. The PC's timer is good to about 1.5 ms [S:local: README "Timing"]. The VJ engine announces the beat about 250 ms ahead [S:local: README `vj` row]. So beat-locked lights can be queued early and leave on time.
- If the budget delays a scheduled send by more than 30 ms, the newest value still goes, and the delay is counted as "late" [I].
- This is what the native API's service scheduler offers, done in the hub instead [S: native-api lane §3; I].

**The transport seam** (load-bearing for slice K0):

```python
class Transport:                      # WinMM first; a fake for the pins; the native API later
    def open(self) -> None            # DAW out + DAW in + MIDI in, by name ("N- " prefix tolerated)
    def send(self, data: bytes) -> SendResult   # code: OK | TIMEOUT(1) | GONE(6) | OTHER, duration_ms, t
    def on_receive(self, cb) -> None  # cb(t, port, bytes) from a normal thread, never the WinMM callback
    def ports_present(self) -> bool
    def close(self, timeout_s=5.0) -> bool      # on a separate thread; False = it never returned
```

**Hot-path rule.** Handles are never opened or closed on the hot path. Opening and closing can stall the whole machine's MIDI behind a stuck driver [S: microsoft/MIDI #1195, #1286]. Every close runs on a separate thread with a 5 s timeout. A close or send that doesn't return marks the transport **WEDGED**: the hub stops sending, says so, and carries on serving its status page.

**A worker process, only if needed.** Moving the transport into a child process the hub can kill is the next step **only if a wedge is ever observed** [I; S: native-api lane §6 B on isolation].

### 4.6 What the device should show: epochs and repainting

An **epoch** is a moment when the device may have forgotten what we told it. Each epoch event:
1. raises the epoch number, which makes every slot with a wanted value dirty;
2. waits for an inquiry reply (gate);
3. repaints in a fixed order: handshake, if the hub owns the session; screen; pads; buttons; labels;
4. sends one more inquiry as an **end marker** (§4.8).

A full repaint is at most about 56 packets, which is about 0.5 s at 12 per 100 ms [I: arithmetic].

**Epoch events, each from a fact about how long the device keeps what we send:**

| Event | Why it means "the device may have forgotten" |
|---|---|
| The hub starts | Unknown state |
| The ports, or the USB device, vanish and return | A power cycle shows the boot gradient, a black screen, and a lost handshake [S:local: hang study] |
| A send returns 6 (`MMSYSERR_NODRIVER`) | The device left and returned [S: microsoft/MIDI #1267] |
| A reply arrives after a run of silence | Recovery from a hang |
| FL starts or stops | FL's script connects or disconnects, and a disconnect clears every LED [S:local: Rill's lesson 10-26 21:40] |
| DAW-port traffic resumes after a spell of MIDI-port-only traffic | A program switch away from DAW and back turns the pads resting white [S:local: Rill's note 10-26 21:55]. Whether the device announces mode changes itself is unknown (E1) |
| A known overwrite: a DAW-bank pad press, or a Back release | Only that slot is resent, about 250 ms later [S:local: `vj.py:1554` reassert; S: Bitwig `RgbButton.java:51-53`, `ContextScreen.java:96-98`] |

### 4.7 The liveness watchdog

**The probe.**
- Send the Device Inquiry `F0 7E 7F 06 01 F7` on the DAW output. Listen on both inputs.
- Accept `F0 7E xx 06 02 00 20 6B 02 00 0A 08 …`.
- Wait 1.5 s. If silent, retry once after 0.5 s, the way Live does. If still silent, ask once on the MIDI port [S: guide §4.2].
- The probe goes through the pump as top-priority control, so it counts against the budget.
- The reply also reaches FL. Our FL script discards SysEx; Arturia's script has no SysEx handler; and one probe with FL open showed no disruption [S: guide §4.2; S:local: hang study].

**When it probes:**
- at start, **before the first paint**, as Bitwig and Live do [S: Bitwig `MidiProcessor.java:129-143`; guide §4.4];
- every 5 minutes;
- after any send error, at most once every 30 s;
- after the port list or the USB device changes;
- after any epoch;
- every 60 s while not answering;
- **at once when any input arrives from the device while the state isn't ALIVE**, at most once every 2 s. A key press proves the device-to-PC direction, so it is the right moment to test the other one [I].

That is about 288 probes a day of 6 bytes each [S: guide §4.3].

**States:**

| State | Meaning | What the hub does |
|---|---|---|
| ALIVE | A reply within the window | Paints normally |
| QUIET | One probe missed | Re-probes after 0.5 s and keeps painting |
| NOT ANSWERING | Two misses, with the USB device and the ports still present | **Stops all surface traffic except probes.** Keeps accepting intents (latest wins). Records the onset window: the last reply and the first silence. Raises an alert on SSE, the console and the bus. Starts the ladder (§4.10) |
| GONE | The USB device or the ports are missing | Waits for them to return (§4.9) |
| WEDGED | A transport call didn't return within 5 s | The host side is stuck: stop and alert. Ladder from rung R4 |

**An open question that must be settled before the alarm is trusted (E9, new).**
- We have never probed a **healthy unit that was asleep**.
- Host SysEx doesn't wake it [S:local: hang study 3], and nobody has measured whether a sleeping unit answers.
- Until E9 answers this, a silence alert reads: "KeyLab not answering since HH:MM:SS. If its screen is dark it may be asleep: press a key. The hub re-probes the moment it sees one."

**What the alert looks like** [I, illustrative]:

```
KeyLab NOT ANSWERING  last reply 21:12:04, first silence 21:17:04 (USB present, ports present, sends returned 0)
  painting held (37 changes waiting); next: press a key -> if still silent, close FL -> ladder R3
```

### 4.8 Delivery confirmation: what we can know, and what we can't

| Signal | What it proves | What it cannot prove |
|---|---|---|
| Send returns 0 | The PC side took it: our process into midisrv, and per one lane on into Arturia's driver [S: protocol-depth lane §3; native-api lane §4]. Treat it as "the PC accepted it" [I] | That the device received, parsed or showed it |
| Send returns 1 | The service waited more than 1 s, so the device or driver is not draining. Stop painting and probe [S: microsoft/MIDI `MidiXProc.cpp`, via the guide L2] | Which layer stalled |
| Send returns 6 | The device left. An epoch, plus a re-open [S: #1267] | — |
| **An inquiry reply after a batch (the "end marker")** | Within one client the service keeps order, and the reply travels the same port and parser as our SysEx. So a reply should mean the device's MIDI reader took in everything sent before it [S: native-api lane on ordering; I]. **Experiment E3 must confirm this** | That every packet was *applied*. Screen packets can be dropped on the device itself [S: saxofonbrian, via the protocol-depth lane] |
| The 5-minute heartbeat | It is also an end marker for everything sent before it [I] | The same |
| Daniel's eyes, or a camera on the pads | The only end-to-end proof of rendering [I] | — |
| A frame visible on the screen | **Nothing about now.** The frozen "Dbadd9" frame outlived the hang [S:local: hang study] | — |

**How each slot reports its delivery.** Each slot reports `sent_at` and `marked_at`: the time of the last end-marker reply covering it. "Delivered" in the hub's words means "the device's reader took it in". It never means "it is on screen" [I].

### 4.9 Device gone and back: automatic re-open

**Two watchers, one inside the MIDI stack and one outside it:**
- **The USB device node.** `USB\VID_1C75&PID_02CE\7656400341020110` [S:local: usb-layer lane], checked through the documented device-manager API (cfgmgr32: `CM_Locate_DevNode`, or `CM_Register_Notification` for events). This is read-only and does not go through midisrv [I].
- **The WinMM port list,** polled once a second on its own thread, because enumeration can itself stall behind a stuck service [I; S: #1195].

**What the combination tells us [I]:**
- USB present, ports missing: a service problem.
- USB gone: cable or power.
- Both present but silent: NOT ANSWERING.

**Re-open sequence:**
1. On a change, or on a send that returns 6, close our handles on the separate thread.
2. Wait 2 s [S: #1267 workaround].
3. Reopen by name, tolerating an "N- " prefix [S: Bitwig, via the guide L3]. **Then confirm identity with the inquiry**: Arturia, family `02 00 0A`, model `08`. A name match alone could point at the wrong device after a driver or naming change [I; S: usb-layer lane §7].
4. Start a new epoch and repaint.

**Target:** ALIVE and repainted within 5 s of the ports returning, with no restart of anything (K4 receipt).

### 4.10 The recovery ladder: code where safe, instructions where not

The ladder comes from guide §2.2, re-ordered by who acts. At each rung the hub probes, records the time, and stops at the first rung that works. That rung is the evidence for which layer was stuck.

| Rung | Who | What | Why it's safe or not |
|---|---|---|---|
| R0 | **Hub, automatic** | Re-probe at the 60 s cadence and on any key | 6 bytes |
| R1 | **Hub, automatic, once, after 60 s of NOT ANSWERING** | Close and reopen only our own handles, on the separate thread | Touches only our session. A close that hangs marks WEDGED instead of blocking [I; S: #1286] |
| R2 | Daniel | Press a key; try a menu (Prog, Settings) | The hub reports whether the key arrived. Arrived means the device-to-PC direction works, which separates a one-sided hang [I]. Wake alone is free [S: guide §2.2 step 0-1] |
| R3 | Daniel | Close FL. The hub notices FL is gone and probes at once from fresh handles | It can't close FL itself. FL is Daniel's |
| R4 | Daniel, as admin | Optional memory dump of midisrv first [S: guide step 4], then restart midisrv. The hub watches the service state (read-only) and reopens when it is back | **It disconnects every MIDI app,** and some old-API clients don't survive it [S: #1016, #1037]. The hub never does this by itself |
| R5 | Daniel, as admin, a yes each time | `pnputil /restart-device "USB\VID_1C75&PID_02CE\7656400341020110"`, or Device Manager Disable/Enable. The hub prints the exact command | Reloads Arturia's driver stack without cutting power [S:local: `pnputil /?`; usb-layer lane §6]. Administrator rights; a system action |
| R6 | Daniel, as admin, later slice | Cycle the hub port (`IOCTL_USB_HUB_CYCLE_PORT`, root hub port 8): a replug without touching the cable | Documented [S: Learn, via the usb-layer lane]. On a USB-powered KeyLab it may equal a power cycle [I]. Needs a small helper, so ask before building it |
| R7 | Daniel | Replug, or the power switch. On USB power these are the same [S:local: hang study, Daniel's answer] | It always works and teaches nothing about which layer was stuck |

**After any rung that recovers it:** the hub reopens if needed, probes, starts an epoch, re-arms the session only by the rules in §4.11, repaints, and writes a hang receipt with the onset window and the rung that worked.

**Also open:** whether a stuck-open SysEx needs a lone `F7` to flush it. That is documented for the service [S: #1267 comment, via the guide L4]. Add it as a code rung between R1 and R2 only after a bench test [I].

### 4.11 Living with FL

**The hub tracks who owns the DAW session: `fl`, `hub` or `none`.** It checks for FL64 every 2 s with a process snapshot, not by spawning `tasklist` [I; the current check is `vj.py:1508-1517`].

**The rules:**
- **While FL runs, the hub never sends connect or disconnect.** It draws in guest mode, which works [S:local: hang study 10-27]. This is enforced in the pump, not left to each caller. Today the plain `led`, `pad` and `all` verbs send a connect unless `--no-connect` is given [S:local: `__main__.py:72-76`]; through the hub they can't.
- **FL starts** (owner becomes fl): an epoch. Hold for a settling time while FL's script runs its own start, then repaint. Five seconds to start; the K4 FL drill tunes it [I].
- **FL stops**: FL's script has sent a disconnect, so the lights are cleared. Owner becomes none, and an epoch starts.
  - **If Daniel says the hub takes the session when FL is closed** (question 2), the hub sends connect plus the pad-port property `00 02 00 14 02 01 00` [S: `KL3Return.py:147`, facts only; S:local: our FL script sends it too]. Owner becomes hub, and it repaints.
- **Hub exit:**
  - owner hub: pads dark, then disconnect, which hands the screen back;
  - owner fl: pads dark, never a disconnect. D8's "FL drives" mode takes over when it misses the hub [S:local: D8 R8.5].
  - This replaces D0 R0.6.
- **Warn on a fighting script.** If FL's DAW input is set to Arturia's script, it repaints the pads on every song step and fights the hub [S: `KL3Return.py:218-265`, via the protocol-depth lane]. The hub reads the assignment read-only from the registry, the same way `fl-status` does, and warns. FL 26 uses ours; FL 25 still uses Arturia's [S:local: guide "Start here" 8].
- **Our FL script must stop painting pads at start** (D8). Its hue ramp contradicts both its own header and D8's "pads are ours" [S:local].
- **The hub cannot govern FL's own writes.** Only D8's "Aurora Link" would make the hub the true single writer while FL is open, and that needs a virtual port. Not needed now that sharing works.

### 4.12 The traffic diet: the PC's lever on hypothesis T1

| Today | Source | With the hub |
|---|---|---|
| Screen re-sent every 2 s whatever happens: 43,200 identical frames a day | [I: arithmetic; S:local: `--reassert 2`, hang study] | **No blind re-send by default.** Repaint only on epoch events. Re-sends exist because FL's own script repaints the screen; ours does not [S:local: `screen.py` docstring 34-41; FL script header] |
| `--pulse`: one frame per beat; about 190,000 frames a day while music plays | [S: guide §3.2 T1, I] | Opt-in, and counted in the odometer (question 5) |
| Every process paints its own way, with no shared memory | [S:local] | Only the change goes out, across every producer |
| Sends continue into a hung link | [S:local: hang study, the screen service kept sending] | Held while NOT ANSWERING |
| Painting continues while the unit sleeps | [S:local: hang study 3] | **Optional idle hold.** If Daniel's Sleep setting is on, after that many minutes with no input from the device, hold cosmetic changes and send the latest on the first key, pad or control [I; question 4] |

**The odometer** keeps packets per day per surface, coalesced, late and held counts, and probe results, in a daily JSONL file next to the hub's state. Lining it up against hang onsets and mem_watch rows is what turns T1 from a guess into a finding [I].

### 4.13 Crash, supervisor and the dead-man

- **A supervisor restarts the hub on a crash.** A restarted hub repaints the correct frame in about 2-3 s, which is better than blacking out [I].
- **The dead-man blackout is a last resort only.** If the hub fails to restart three times within 60 s, the supervisor waits until the hub's process is confirmed gone and the named lock is free or abandoned. Windows reports an abandoned lock when its owner dies [S: Learn, `WaitForSingleObject`, `WAIT_ABANDONED`]. Only then does it take the lock, send 12 "pad dark" packets through its own governor, and let go.
  - This keeps exactly one writer, and replaces D0 R0.7's "within 2 s" with "after a failed restart".
- **Heartbeat file** every second (D0 kept), for the supervisor and for `doctor`.
- **Auto-start** at logon as a scheduled task: persistent configuration, so Daniel decides (question 3).
- **The hub never calls `midiOutReset` on close.** Its sends are synchronous, so no buffers are ever pending. Under Legacy API mode a reset is about 2,064 messages [S: usb-layer lane §3 a4]. The existing `MidiOut.close()` keeps its reset for other callers until Daniel says otherwise (house rule: ask before removing behaviour).

### 4.14 What the hub records

- **A ring of the last 512 sends:** time, packet kind, result code, duration. It is written to disk on any failure [S: guide §4.3 "Log"].
- **Hang receipts:** `state/arsenal/keylab/receipts/hang-<stamp>.json`, holding:
  - the onset window;
  - the last input per port;
  - the ladder rung that worked and its time;
  - the USB arrival time (from the `arturiausbmidi` event 3 logged at each device arrival [S:local: guide §4.2]);
  - a pointer to the odometer.
- **A bus note to Daniel and Rill** on NOT ANSWERING, GONE, WEDGED and recovery.

---

## 5. Requirements (revised D0)

- **R0.1 MUST** Among house processes, only the hub opens the KeyLab DAW output while it runs. Any direct writer holds the same named lock. A second hub refuses and names the holder.
- **R0.2 MUST** Every hub packet passes one governor: 12 per 100 ms, and 8 while FL runs, until P24 or the soak says otherwise.
- **R0.3 MUST** Surfaces are slots. Latest wins per slot. A slot is sent only when its wanted value differs from what was sent in this epoch.
- **R0.4 MUST** The layer compositor is pure and pinned without hardware (D0 R0.3 kept).
- **R0.5 MUST** Only the foreground lease paints the mode layer (D0 R0.4 kept).
- **R0.6 MUST** Never send connect or disconnect while FL runs. Disconnect on exit only if the hub sent the connect in this session.
- **R0.7 MUST** Probe before the first paint; every 5 minutes; after send errors; after port or USB changes; after epochs; on the first input while not ALIVE. Two misses mean NOT ANSWERING. The wording carries the sleep caveat until E9 is settled.
- **R0.8 MUST** While NOT ANSWERING, GONE or WEDGED, send nothing but probes, keep accepting intents, and repaint on recovery.
- **R0.9 MUST** Every epoch event re-sends every slot that has a wanted value: gated on a reply, in the fixed order, within the budget, closed by an inquiry end marker.
- **R0.10 MUST** After the ports return, reopen without a restart, confirm identity by inquiry, and be ALIVE and repainted within 5 s.
- **R0.11 MUST** No blind periodic re-send by default.
- **R0.12 MUST** No handle open or close on the hot path. Closes run on a separate thread with a timeout. A call that never returns marks WEDGED.
- **R0.13 MUST** The hub never runs administrator commands, never restarts midisrv, and never changes drivers. Those rungs are printed for Daniel.
- **R0.14 MUST** Every byte is checked before sending: framing, no data byte above 0x7F, never screens 38/43/44, never the `21 03 40` family. Raw sends happen only under a bench lease.
- **R0.15 MUST** Record the send ring, hang receipts and the daily odometer.
- **R0.16 MUST** The hub talks to a transport interface: WinMM first, a fake for the pins, the native API later.
- **R0.17 MUST** Bind and CORS are loopback only (D0 R0.8). The piano page's key input is untouched (D0 R0.10). The MCP door holds no handle (D0 R0.11).
- **R0.18 SHOULD** Host-leg latency, intent to packet, stays under 5 ms at p95 with three clients (D0 R0.9).

---

## 6. Build slices and receipts

| Slice | What | Receipt | Needs from Daniel |
|---|---|---|---|
| **K0** | The four `winmidi.py` fixes: `lpData` as `c_void_p`; input buffers re-queued from a normal thread, never the callback; the first inquiry at least 20 ms after `midiInStart` [S: #1263]; a loud send timeout with the result code; `midiInStop` before `midiInReset`, with codes checked [S: NAudio PR #1478, via the guide]. Plus the transport seam and the fake transport | Offline tests green in a clean worktree: a reply containing `00` bytes survives; 100 replies with 24 buffers all arrive; a timeout is reported; the close order is right | Nothing |
| **K1** | The `doctor` verb from guide §4.2, plus the firmware read from Plug and Play (`REV_1500`), FL's stored identity replies (read-only from the registry), and the USB node watcher | `state/arsenal/keylab/receipts/doctor-<stamp>.json`. Daniel reads Settings > Global once, so the version bytes can be mapped (E8). E9: one doctor run with the unit asleep | His go to send one inquiry. FL may stay open (seen harmless [S:local]) |
| **K2** | The hub core, offline: slots, compositor, dirty tracking, pump, governor, epochs, state machine, session owner, named lock, ladder engine. Fake transport, fake clock, fake FL watcher | Tests show: never more than 12 in any 100 ms with 5 producers at full rate; latest wins; full repaint after each epoch kind; zero surface sends while NOT ANSWERING; zero connects while the fake FL runs; disconnect only when the hub owns the session; a second hub refuses | Nothing |
| **K3** | Hub server and clients: the HTTP/SSE routes; CLI routing; the screen readout and the VJ engine's pads as clients; then the MCP door (D0.5) | Hardware, Daniel present: VJ pads plus the live screen plus CLI pad writes together for 30 min. The governor log's busiest 100 ms window is at most 12 across all of them; Daniel's eyes; input latency through the hub at p95 (decides whether the VJ engine's inputs move) | Presence |
| **K4** | Watchdog plus re-open, live. Three drills: (a) **replug**: GONE within 2 s, ALIVE and repainted within 5 s of the port returning, nothing restarted; (b) **FL open/close ×3**: the send log shows no connect while FL ran, and pads are correct after each; (c) **kill the hub**: the supervisor restarts it and it repaints within 3 s | Video or eyes plus the send log, dated | Presence; FL closed for (a) |
| **K5** | Traffic diet, odometer, and **the T1 soak**: the hub running as normal life, probing every 5 min, for up to 7 days | Time-to-hang with its onset window, or 7 clean days. Daily traffic totals against today's baseline of about 190,000 frames a day | Leave it running; glance once a day |
| **K6** | Ladder as code: `doctor --ladder` and the hub's alert walk rungs R0-R7, recording the rung and time. R5 is offered as an exact command | A dry-run walk receipt. The real one comes at the next hang | Admin rungs: a yes each time |
| **K7** (gated) | Native backend proof: the native-api lane's P1-P3 on Windows' test loopbacks (load, service ping, round trip, soak); then P4-P6 on the KeyLab with Daniel | One JSON receipt per gate. Fail at P1 means a helper process instead (needs the .NET SDK, 215 MB) | Approval of the downloads in §7 |
| **K8** (gated) | **One** experiment after K5's baseline: the class-driver A/B (C) or Legacy API mode (D), soaked the same way as K5 | Same receipts as K5; a revert receipt | The driver switch or registry change; FL closed; a revert before any firmware update |

---

## 7. What needs Daniel's approval

**Nothing to install for K0-K6.** The approvals that remain:
- **Presence** for the K1, K3 and K4 drills.
- **A scheduled task** for auto-start and the supervisor. This is persistent configuration.
- **Administrator rungs** R4-R6: a yes each time.

**Downloads for K7.** None done; the sizes are from the native-api lane's HEAD and API checks:

| What | Source | Size |
|---|---|---|
| `Windows.Devices.Midi2.0.99.92-preview.11.nupkg` | github.com/microsoft/MIDI, release inbox-preview-11 | 102,998,997 bytes |
| PyWinRT 4.0.2 | nuget.org | 681,939 bytes |
| `winrt-runtime` 4.0.3 and `winrt-table-compiler` 4.0.0, in a **new** virtual environment | PyPI | 254,046 and 12,198 bytes. The global environment keeps its 3.2.1 packages |
| Optional: Windows MIDI Services Tools 0.99.94-preview.12 | release inbox-preview-12 | 223,376,824 bytes |

**The preview licence conditions** [S: Preview 11 notes]:
- remove the preview copy once Windows ships its own;
- keep up with previews;
- never use it below Windows 11 25H2;
- Microsoft gives "no guarantee" of compatibility with the service now in Windows.

**Experiments, one at a time:**
- the class-driver switch, or `UseLegacyMidi=1` plus a restart (K8);
- USB selective suspend off (T5): separately, never stacked [S: guide §3.2].

**Not recommended for approval:**
- WinUSB / Zadig (its root certificate and driver swap);
- building on Arturia's private TUSBAudio API. Its headers are licensed only to Arturia [S: thesycon.de, via the usb-layer lane], so it would mean reverse-engineering a closed binary.

---

## 8. Experiments that settle the unknowns

None of these has been run. Each needs Daniel's go, a probe before and after, and the K0 fixes first.

- **E1. Mode census.** Listen on both inputs while Daniel switches programs, sleeps the unit, wakes it, and opens Settings. Does the mk3 report its mode, as its siblings do [S: Bitwig `essentialMk3/SysExHandler.java:140-153`]? If yes, that becomes a free epoch trigger.
- **E2. Echo census.** Send one LED, one screen, one connect and one properties write, 2 s apart. Is there any acknowledgement?
- **E3. End marker.** 20 inquiries alone, against 20 each sent after 12 LED writes. Does the reply queue behind our SysEx? This decides whether §4.8's end marker is real.
- **E4. Port symmetry.** Ask on DAW only. Which inputs carry the reply? Are the version bytes different per port?
- **E8. Version bytes.** Compare them with Settings > Global (1.5.0). MCC formats the version as `$3.$2.$1` [S:local: `KeyLab3 88.json`].
- **E9 (new). Asleep inquiry.** Does a healthy unit with a dark screen answer? This decides whether silence means "hung" or "asleep or hung".
- **E5. Configuration read** `20 09 40 lo hi` [S: saxofonbrian]. The riskiest: its write neighbour throws the unit into User mode. Explicit go only.
- **E6/E7.** Does the persistent screen come back by itself after a popup? Do pads and screen survive sleep and wake? Daniel's eyes.
- **P24, the "ramp until freeze" probe in D0,** should wait until after the K5 soak. It deliberately freezes the unit, and that freeze must not be confused with the silent hang [I].

---

## 9. Questions for Daniel

1. **Port for the hub:** 8798? 8794 is now the VJ engine's.
2. **When FL is closed,** should the hub take the DAW session by itself (connect, then paint), or wait until something asks?
3. **Start the hub at logon,** with a supervisor that restarts it (a scheduled task)?
4. **Is the KeyLab's Sleep setting on, and after how many minutes?** That decides the idle traffic hold.
5. **The beat-pulse marker on the screen:** keep it on by default? It is the biggest single source of screen traffic.
6. **FL 26 keeps our script on the DAW input,** and our script stops painting pads at start (D8). Agreed?

---

## 10. Corrections and lane conflicts, resolved

- **When the in-box API ships.** The native-api lane said "last week of November 2026". That came from the inbox-dev-preview-9 notes of 2026-09-21. The usb-layer lane said 2027. **2027 is current** [S: inbox-preview-12 notes, 2026-10-21; `porting-midi-libraries.md:20`, checked today]. The service fixes the guide expected in late November (#1084, #1146, #1263) may slip with it [I; per-issue dates not re-checked].
- **"Never supported for redistribution"** (usb-layer lane) is about the **old** package, `Microsoft.Windows.Devices.Midi2`. The current `Windows.Devices.Midi2` preview carries a go-live licence with conditions [S: porting doc line 22; Preview 11 notes]. Both lanes are right about different packages.
- **What a send result of 0 means.** One lane says "the service finished its write to Arturia's driver"; the other says the result tracks only into the service. This design takes the weaker reading, "the PC accepted it", and leaves proof of arrival to the inquiry [S: both lanes; I].
- **Number of TUSBAudio functions:** 81 distinct names (usb-layer lane) against 83 exports (protocol-depth lane). Immaterial, because we don't build on that API.
- **D0 corrections:**
  - P1 is answered (shared);
  - 8794 is taken;
  - R0.6 and R0.7 are replaced (§4.11, §4.13);
  - the README's "shared by every producer on the port" stays wrong until the hub lands [S: guide "Start here" 3].
- **Lane conduct, already reported by the lanes themselves:**
  - one lane ran a `cd` outside the repository (read-only);
  - one lane parsed Arturia's DLL export table on the host, which the house reverse-engineering rule counts as VM-only work.

  Neither changed anything. Neither is repeated here.

---

**Files read:**
- `E:\AI-Setup\docs\library\design\20261022_a16-d0-control-center-hub_3325c3.md` (whole)
- `E:\AI-Setup\docs\library\design\20261022_a16-d8-fl-script-handoff_3384d8.md`
- `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-hang-study-2026-10-26.md`
- `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-dev-guidance-and-hang-guide-2026-10-27.md` (guide sections 1-5)
- `E:\AI-Setup\arsenal\keylab\winmidi.py`, `governor.py`, `ledframe.py`, `screen.py` (ScreenWriter and docstring), `vj.py` (inputs, PadPainter, LED output), `__main__.py` (`_arm`, connect handling), `README.md` ("Confirmed facts", verbs), `fl\device_AuroraKeyLab.py` (header, handlers)

**Checked today, read-only:**
- microsoft/MIDI release notes inbox-dev-preview-9, inbox-preview-11 and inbox-preview-12, and `docs/kb/porting-midi-libraries.md`, through `gh api` to stdout;
- a repo grep for which ports are free.

Nothing was written to the repo and nothing was committed. D0's file is a generated projection, so this revision should land through the doc verbs.

---

## Research lane: the native Windows MIDI Services API (verbatim)

# Native API lane: Windows MIDI Services (`Windows.Devices.Midi2`) as a replacement for WinMM in arsenal/keylab

Grades: **[S]** a cited source says it. **[S:local]** a read-only query or offline computation on this machine. **[I]** my inference.

I did not touch the KeyLab, its MIDI ports, FL Studio, or ports 8793, 8794 and 8796. I downloaded no binaries and installed nothing. Everything I ran on the system was a read-only query: PnP, registry, file versions, service state and pip list. I fetched sizes with HTTP HEAD only.

While reading, I saved five fetched text pages to the session scratchpad: two sets of release notes, the docs index, a repo file listing and a .NET metadata line. I deleted them afterwards. One file of mine is left there: an offline encoder script, `ump_sysex7.py`. It does no MIDI I/O.

## Bottom line

1. **The brief's name for this API is out of date.** The API is now `Windows.Devices.Midi2`. There is no separate "SDK runtime" to install, and no initializer.
   - "Everything moved out of `Microsoft.Windows.Devices.Midi2.*` and into `Windows.Devices.Midi2.*`… There is no more COM initializer, no SDK update functionality, and no versioning" [S: release notes, inbox-dev-preview-8, 2026-09-14].
   - The API surface was locked at Preview 11 (2026-10-12; NuGet package `0.99.92-preview.11`). Preview 12 (2026-10-21) has no new API [S: release notes].
2. **The API isn't on this PC yet.**
   - There is no `Windows.Devices.Midi2.dll` in System32, and no Midi2 classes are registered with WinRT [S:local].
   - Microsoft plans to ship it in Windows 11 25H2+ "starting during the last week of November 2026" [S: release notes, inbox-dev-preview-9].
   - These controlled rollouts take up to 30-45 days to switch on for a given PC [S: Pete Brown on microsoft/MIDI #1084].
   - Until then, a program can carry its own copy of the API from the preview NuGet package (about 98 MiB).
3. **It does not get around the layer we most suspect caused the hang.** A native connection travels the same way as WinMM:
   - the same Windows MIDI service (midisrv);
   - the same channel between our process and the service (MidiXProc);
   - the same "kernel streaming aggregate" (KSA) path into Arturia's driver.

   The KeyLab's native endpoint sits directly on Arturia's kernel-streaming device, `TUSBAUDIO_ENUM\VID_1C75&PID_02CE&KS\…` [S:local: the endpoint's parent device]. So if the 10-26 stall was in Arturia's driver or the KeyLab's USB link (M1 in the guide), switching APIs alone would not have stopped it [I].
4. **What it does give us is a better-behaved and more honest host side:**
   - It removes the WinMM layer, which is where our own `winmidi.py` defects live and where several Microsoft bugs specific to WinMM live (#1263, #957, #1157, #1267, and #1146; the fix notes for #1146/#1263 say WinMM apps "got nothing, or lost some short messages, while apps that use the Windows MIDI Services API got everything").
   - It adds automatic reconnect, device add/remove watching, flag-style send results, a ping of the service itself, a list of who has the KeyLab open, timestamps on incoming messages, and sends scheduled by the service.

   These are the tools for detecting a hang, locating it and recovering from it, and for moving timing work onto the PC [S, details below].
5. **Python can reach it without a compiler.** PyWinRT 4 builds a Python binding from Microsoft's description of the API (the `.winmd` metadata file). It needs the .NET 10 runtime, which is already installed here [S; S:local].
   - Loading the API without registering it works through the standard WinRT fallback, which looks for `Windows.Devices.Midi2.dll` in directories we add [S: code; I: that it works for python.exe has to be proven].
   - It must live in its own virtual environment, because the global environment has PyWinRT 3.2.1 and the two generations cannot be mixed [S; S:local].
   - A small C# or C++ helper process is the fallback. It needs a toolchain that is not installed (the .NET SDK is 205 MiB).
6. **A proof plan exists that never touches the KeyLab.** It runs on Windows' built-in test loopbacks A and B and the service ping endpoint, which are present here [S:local]. Steps on the KeyLab are separate, and each one waits for Daniel's go.

## 1. The API and how the KeyLab appears in it

**Status and requirements**

- It needs Windows 11 25H2 or later; 24H2 never gets it [S: kb/minimum-requirements]. This PC runs 25H2, build 26200.9168 [S:local].
- Microsoft Learn has no `Windows.Devices.Midi2` reference page (HTTP 404). The reference lives at microsoft.github.io/MIDI/sdk-reference [S]. PyPI has no `winrt-Windows.Devices.Midi2` package [S: PyPI 404].
- Preview 11's licence lets developers ship the DLL, `.winmd` and `.pri` with an app, under conditions [S: Preview 11 release notes]:
  - remove the copy once Windows has its own;
  - not ship to Windows versions below 25H2;
  - Microsoft makes "no guarantee that the in-box API binaries or service transports will be compatible with this Preview release."
- When Windows has its own copy, apps get that copy, even if they ship one [S: Preview 11].
- The Tools package puts a copy of the DLL next to its apps. Microsoft says: "Don't build against that copy… its ABI is not locked" [S: Preview 12].

**There are no ports in this API; there are endpoints and groups**

- The "kernel streaming aggregate" (KSA) transport makes one MIDI 2.0 (UMP) endpoint per MIDI 1.0 device. Each of the device's MIDI 1.0 ports becomes a numbered group, starting at 0 [S: kb/kernel-streaming-aggregate; kb/mapping-midi1-port-concepts].
- Translation happens in the service. For a USB MIDI 1.0 device on a vendor driver, the service converts to and from UMP for this API, and to and from MIDI 1.0 bytes for WinMM [S: kb/data-translation].
- **The KeyLab on this PC** [S:local]:
  - Endpoint `SWD\MIDISRV\MIDIU_KSA_16201702556534547415`, "KeyLab 88 mk3", created by midisrv (pid 45480).
  - It last arrived on 2026-10-26 at 23:31:47, which was the power cycle. It was first installed on 2026-06-11.
  - So the endpoint id survived the power cycle.
- **Its MIDI 1.0 port devices** [S:local]:
  - `…_0_0` and `…_1_0` are "KeyLab 88 mk3 MIDI";
  - `…_0_1` and `…_1_1` are "KeyLab 88 mk3 DAW".
  - **So the MIDI port is group index 0 (Group 1) and the DAW port is group index 1 (Group 2)** [I; confirm by enumeration, step P4].
- The USB hardware id ends `REV_1500`, which matches firmware 1.5.0 [S:local; I].
- **Connections** [S: MidiEndpointConnection; porting-midi-libraries]:
  - One connection carries both directions and all groups.
  - Each connection has its own send and receive buffers and its own thread.
  - Open one connection per endpoint per process, and filter by group yourself or with Microsoft's group listener.
- **Test endpoints already on this PC:** Service Test Loopback A and B, and Service Test Ping, all with status OK [S:local].

## 2. SysEx as UMP

- **How SysEx is packed** [S: kb/ump-data-format-primer, "System Exclusive"]:
  - Message type 3: 64-bit packets of up to six data bytes each, with no `F0` or `F7`.
  - A status nibble marks each packet as complete, start, continue or end.
  - Packets from a USB MIDI 1.0 device often carry fewer than six bytes.
  - On the same group, only real-time messages may cut in; anything else ends the SysEx.
- My offline encoder reproduces both of the primer's worked examples exactly [S:local: `ump_sysex7.py` assertions pass]. It gives our messages, on the DAW group (index 1, [I]):

| Message | MIDI 1.0 bytes | UMP words |
|---|---|---|
| Device Inquiry | `F0 7E 7F 06 01 F7` | `31047E7F 06010000` (1 packet) |
| DAW connect | `F0 00 20 6B 7F 42 00 02 05 01 F7` | `31160020 6B7F4200 31330205 01000000` |
| Pad 1 DAW green (LED 0x52) | `F0 00 20 6B 7F 42 00 02 03 52 00 7F 00 00 F7` | `31160020 6B7F4200 31260203 52007F00 31310000 00000000` |
| 66-byte screen frame | 66 bytes | 11 packets, 22 words |

- **Rules for us:**
  - Send each SysEx as one multi-message call (`SendMultipleMessagesWordList` or `…WordArray`), and never split one UMP across two calls [S: MidiEndpointConnection].
  - Never spread one SysEx over several calls. Another app's message on the same group would end it, and the service still has no handling for SysEx from two apps colliding (#60, open since 2023) [S; I].
  - The per-call limit comes from `GetSupportedMaxMidiWordsPerTransmission` and must not be hard-coded [S]. Our largest message is 22 words; the KeyLab endpoint's limit is unknown [S:local; I].
- **Receiving:** incoming SysEx arrives as packets, so we reassemble it per group. Microsoft's `MidiSystemExclusiveReceiver` does this, or we can do it in Python [S: moving-from-winmm-to-wms]. Replies, like the identity reply, go to every app that has the endpoint open [I].

## 3. What it gives us over WinMM

| Capability | WinMM today | Windows.Devices.Midi2 | What it means for the hang and the hub |
|---|---|---|---|
| SysEx receive | We prepare and re-queue buffers by hand. Our `MidiIn` truncates at `00` and never re-queues. #957 drops input when no buffer is queued; #1263 drops replies that arrive before `midiInStart` [S: guide 4.1, #957, #1263] | Each packet arrives in a `MessageReceived` event with its words and a timestamp. There are no buffers to manage [S: MidiMessageReceivedEventArgs] | Removes a whole class of false "hung" verdicts [I] |
| Timestamps | WinMM timestamps, relative to when the input started [S: api-back-compat] | Stamped by the service on arrival: absolute 100 ns ticks on `MidiClock`, the same clock as `QueryPerformanceCounter` [S: MidiClock] | Hang onset can be lined up with mem_watch and FL events [I] |
| Scheduled sends | None | Any timestamp up to 5 minutes ahead; the service's scheduler sends it. 0 means now. The scheduler "slows down when it holds thousands of messages" [S: MidiClock; MidiEndpointConnection] | The hub can queue a beat's frames ahead of time without precise sleeps in Python. This is "heavy lifting by the PC". It does not throttle anything, so the governor still counts every message [I] |
| Send result | `MMRESULT` codes; 1 means the service waited too long [S: guide] | Flags: `Succeeded`, `Failed`, `BufferFull`, `EndpointConnectionClosedOrInvalid`, `TimestampOutOfRange`, `TransmissionWordCountExceeded`, and more [S: MidiSendMessageResultsEnum] | Clearer signals, with the limits in section 4 |
| Waiting for the service | `midiOutLongMsg` waits for "send complete" | Optional: `WaitForEndpointReceiptOnSend`, the same internal flag [S: MidiEndpointConnectionSettings; `MidiEndpointConnection_SendInfrastructure.cpp`] | The same 1 s stall detection as WinMM, on request [S: `MidiXProc.cpp`] |
| Device reconnect | WinMM apps must close and reopen; our screen service died at the power cycle [S: #696; hang study] | `AutoReconnect` is on by default, with `EndpointDeviceDisconnected` and `EndpointDeviceReconnected` events [S] | The hub survives a power cycle, then probes and repaints [I] |
| Device add/remove/change | Poll the port count [S: moving doc] | `MidiEndpointDeviceWatcher` with Added, Removed and Updated events [S] | The doctor's "ports" check becomes an event. It still cannot see a silent stall (section 4) |
| Service health | None | `MidiDiagnostics.PingService(n)`: round trips to the service, with timings. "A ping doesn't tell you whether a particular transport or device has a problem" [S] | Separates "the service is stuck" (L2) from "the device or driver is stuck" (L1) without installing anything else [I] |
| Who holds the KeyLab | None (the guide needed `midi.exe`) | `MidiReporting.FindAllSessionsWithMatchingOpenUmpEndpoint(id, includeRelatedMidi1Ports)`, with each session's process name, pid and start time [S] | The doctor's "holders" check, FL included [I] |
| Data through both ports | Two handles per direction | One connection; both groups arrive in one ordered, timestamped stream [S] | One owner, one stream: fits the hub ruling [I] |
| App-to-app endpoints | Not available | Virtual devices, which WinMM apps can see as MIDI 1.0 ports [S: api-back-compat; kb/virtual-device-app] | A possible later option: give FL a hub port, so the hub is the only writer to the KeyLab [I] |
| Speed | — | WinRT calls cost tens to hundreds of ns in PyWinRT 4 [S: PyWinRT 4.0 notes]. The device leg is about 10 ms [S: A16 D0] | Negligible [I] |

## 4. What it does not give us

- **It does not get around the service or Arturia's driver.**
  - Native sends go through the same `SendMidiMessage` path in MidiXProc as WinMM [S: `MidiEndpointConnection_SendInfrastructure.cpp`].
  - The KSA transport then writes to the same kernel-streaming device under Arturia's driver [S:local: endpoint parent; S: data-translation table].
  - So machine-wide wedges hit every API alike: a driver that stops draining wedges the service (#1084, fix in the end-of-November rollout); a vendor driver's close that never returns hangs midisrv (#1286, open, 2026-10-20) [S].
- **A send result tracks our message into the service, not to the device.**
  - `WaitForEndpointReceiptOnSend` "waits for the service to confirm it got the message" [S].
  - When the buffer to the service is full, a send waits up to 1,000 ms, then drops the message and returns `BufferFull`. Once the channel is marked stalled, later sends fail at once [S: `MidiXProc.cpp`, the full-buffer branch and the end of `SendMidiMessage`].
  - The client's result comes only from that channel. An error inside the service on the device write, such as the coming kernel-streaming write timeout that switches the output off after three timeouts [S: `MidiKS.h` 105-107, `MidiKs.cpp` 595-707], does not reach the result [I from the code].
  - USB MIDI 1.0 has no acknowledgements. **Only a round trip proves the KeyLab is alive** (the Device Inquiry), and that is as true here as with WinMM [I].
- **The watcher cannot see a silent stall.** It reports endpoints added and removed. During the 10-26 hang, Windows logged no USB or PnP event for the KeyLab [S:local: guide §"Start here" 5]. So the endpoint stayed, and so would the connection [I].
- **No rate limiting across apps and no collision protection.** #60 is open. The scheduler does not throttle [S]. The burst governor stays our job, which means the hub [I].
- **The preview copy may not match this PC's service.** Microsoft gives no guarantee that it works with the service now in Windows [S: Preview 11]. midisrv here is 10.0.26100.7705, from August [S:local]. This is gate P1 below.

## 5. Known issues that matter to us

| Issue | State | What it is | Relevance |
|---|---|---|---|
| #60 | open | No handling for SysEx from several apps colliding [S] | Affects every API. The hub as single writer |
| #1286 | open | A vendor driver that never finishes a close hangs midisrv; the workaround is still being enabled [S] | Same class of failure as the Arturia-driver hypothesis [I] |
| #1195 | open | A stalled driver wedges WinMM open and close machine-wide [S] | Keep one long-lived connection; never open per write [I] |
| #1084 | fixed, end-of-Nov rollout | A device that stops draining its input wedges the service until it is unplugged [S] | Same |
| #1040 | fixed, Q4 2026 to Q1 2027 | Incoming SysEx through KSA on Microsoft's older USB driver (`usbaudio.sys`) loses bytes at random [S] | Ours runs on Arturia's driver, not that one, but goes through the same KSA path. Identity replies could be damaged until the fix arrives [I] |
| #1146, #1263 | fixed, rollout | WinMM got nothing or lost messages while the native API got everything [S: Preview 11] | A direct argument for the native API |
| #1016, #1037 | open | midisrv can't restart while WinMM or WinRT MIDI 1.0 clients are open; those clients don't survive a service restart [S] | Ladder step 5 side effects |
| #968 | open | App-to-app MIDI stops being received after the receiving app is reopened a few times [S] | Watch for it if we use virtual devices or loopbacks |
| #906 | open | WinRT MIDI 1.0 input is silent after a replug on 25H2 [S] | The reason not to use the older `winrt-Windows.Devices.Midi` from Python |
| COM extensions | by design | A raw receive callback disables listeners and virtual devices on that connection [S] | Pick one receive path per connection |

## 6. Reaching it from Python

**A. PyWinRT 4 binding of the API's metadata file (recommended to try first)**

- PyWinRT 4's generator, `PyWinRT.exe`, "writes a table and type stubs instead of C++, so projecting a component of your own needs no compiler" [S: PyWinRT 4.0 notes].
  - It needs the .NET 10 runtime [S]. Microsoft.NETCore.App 10.0.8 is installed here [S:local].
  - The package is built with `winrt-table-compiler` and runs on `winrt-runtime` 4.x [S: versioning.md].
- **Gap risk.** A member whose call shape is not in the runtime's list of supported shapes is reported when the binding is generated, and raises when used [S]. Unknown until we generate.
- **It needs its own virtual environment.** The global environment has `winrt-runtime` 3.2.1 plus about 90 `winrt-*` 3.2.1 packages [S:local]. Version 4 cannot load 3.x packages [S].
- **Loading the DLL without registration:**
  - PyWinRT activates classes through C++/WinRT's `get_runtime_activation_factory_impl` [S: pywinrt `runtime/src/interp.cpp` ~1173].
  - When `RoGetActivationFactory` fails, that code tries `Windows.Devices.Midi2.dll`, then `Windows.Devices.dll`, using the "search default directories" flag of `LoadLibraryExW` [S: cppwinrt `strings/base_activation.h` 56-68, `base_agile_ref.h` 74-77].
  - That flag covers the app's directory, directories added with `AddDllDirectory`, and System32 [S: Learn, LoadLibraryExW].
  - Python's `os.add_dll_directory` calls `AddDllDirectory` [S: CPython 3.11 `posixmodule.c` 14796-14834].
  - So putting the preview DLL and `.pri` in a folder we add should activate [I; this is gate P1]. Once Windows has its own copy, registration takes over by itself [S].
- **Threads:**
  - Event handlers run on WinRT threads.
  - The connection waits for each handler to finish, so copy the message to a queue and return [S].
  - comtypes and pythoncom make the importing thread single-threaded; set `sys.coinit_flags = 0` first [S: pywinrt docs/threads.md].
- **The fastest path is out of reach, and we don't need it.** Microsoft's allocation-free send and receive (`IMidiEndpointConnectionRaw`, IID `8087b303-0519-31d1-31d1-000000000020`) is a plain COM interface, not WinRT, so PyWinRT does not cover it [S: COM-extensions doc]. At our message rates we don't need it [I].

**B. A small helper process speaking JSON over a pipe (fallback)**

- C#: Microsoft's samples target `net10.0-windows10.0.26100.0` with CsWinRT 2.2.0 [S: `client-basics-cs.csproj`; main already references an unreleased `0.99.95-preview.13`]. Building needs the .NET SDK, which is not installed; only runtimes are [S:local].
- C++/WinRT needs Visual Studio Build Tools; none are installed [S:local]. Rust has no toolchain here [S:local].
- Its advantage is isolation: a wedged call kills the helper, not the hub [I].

**C. Rejected:**
- Raw ctypes calls against the WinRT interfaces, which means hand-copying interface ids and layouts [I: high risk].
- The older WinRT MIDI 1.0 API, because of #906 and because its sends return no result [S].
- Node: the samples README links an `electron-js` folder, but it is not in the repo [S].

**Design note [I]:** put a transport interface under the hub. Use WinMM today, with the `winmidi.py` fixes from guide 4.1, and switch to the native backend once the proof passes. The hub's governor, watchdog and leases do not change.

## 7. Installs and downloads for Daniel's approval (none done)

| Priority | What | Source | Size | Why |
|---|---|---|---|---|
| 1 | `Windows.Devices.Midi2.0.99.92-preview.11.nupkg` (the API as DLL, `.winmd` and `.pri`; preview licence) | github.com/microsoft/MIDI/releases/tag/inbox-preview-11 | 102,998,997 bytes [S: GitHub API] | The API before the November rollout. Unpack only, no installer |
| 1 | PyWinRT 4.0.2 (generator, MIT) | nuget.org/packages/PyWinRT | 681,939 bytes [S] | Writes the Python binding |
| 1 | In a new venv: `winrt-runtime` 4.0.3 (cp311 x64 wheel), `winrt-table-compiler` 4.0.0, `hatchling`, and the 4.x `winrt-Windows.Foundation` and `.Collections` | PyPI | 254,046 and 12,198 bytes; others small; all 349 projection wheels total 6.7 MB [S] | Runtime and build. Leaves the global 3.2.1 environment alone |
| 2 | Tools 0.99.94-preview.12 x64 (already on the guide's list) | release inbox-preview-12 | 223,376,824 bytes [S] | `midi.exe` and `mididiag`. Our own native listener covers much of ladder step 3 once item 1 works [I]. Its Windows App SDK 2.5.1 runtime is already installed here [S:local] |
| fallback | .NET SDK 10.0.403 win-x64 | builds.dotnet.microsoft.com | 215,399,928 bytes [S: HEAD] | Only if the C# helper is chosen |
| zero install | Wait for the in-box API | Windows Update | — | End of November plus 30-45 days to switch on [S] |

## 8. Minimal proof plan (none of P0-P3 touches the KeyLab)

- **P0. Done, read-only.** All the facts in this report marked [S:local].
- **P1. Load gate.** After approval for priority 1, generate the binding in a separate venv and record which call shapes are missing. Then:
  - `os.add_dll_directory(<folder holding the DLL and .pri>)`;
  - `MidiApi.IsSystemProvided()` should return False;
  - `GetCurrentlySelectedApiMode()`;
  - `EnsureServiceAvailable()` should return True. midisrv is already running, so this starts nothing [S:local; I].
  - Receipt: JSON. Fail means helper route B.
- **P2. Service ping.** `MidiDiagnostics.PingService(20)`: success count and latency percentiles.
- **P3. Loopback round trip in one process.** Session "aurora-native-proof", connections to diagnostic loopbacks A and B. Send our real encodings (the inquiry, DAW connect, an LED write, a 22-word frame), each as one call. Assert:
  - the words received on B equal the words sent;
  - the reassembled bytes equal the original bytes;
  - the send flags, and latency p50/p95 from the receive timestamps;
  - 12 messages per 100 ms for 60 s;
  - scheduled sends at +5, +20 and +100 ms: arrival error;
  - wait-for-receipt on versus off;
  - each error path: send after disconnect gives `EndpointConnectionClosedOrInvalid`; an oversize call gives `TransmissionWordCountExceeded`; a timestamp more than 5 minutes ahead gives `TimestampOutOfRange`;
  - a 30-60 min soak, with read-only handle and thread counts for python and midisrv.

  Run P2 and P3 when Daniel is not recording: they open service connections, though not to the KeyLab [I].
- **P4. Daniel's go: metadata only, no connection.** Enumerate the KeyLab endpoint (block names, group map, parent VID/PID). `MidiReporting.FindAllSessionsWithMatchingOpenUmpEndpoint(keylab, True)` should list FL's session.
- **P5. Daniel's go, Daniel present.**
  - A listen-only native connection to the KeyLab, with a WinMM capture beside it. Press keys and pads. This differential test is ladder step 3 without the Tools [I, after Pete Brown's method in #1177].
  - Then the native Device Inquiry on group 2, observing guide 3's rules about FL.
- **P6. Daniel's go.** The native backend inside the hub, with the watchdog (guide 4.3), then the T1 soak.

## 9. Corrections to the brief and our documents

- The brief's "Microsoft.Windows.Devices.Midi2 SDK runtime" is the model from before September 2026. The namespace is now `Windows.Devices.Midi2`, there is no runtime installer, and the Tools' copy of the DLL must not be used to build [S].
- Guide 5.6: the Windows App SDK 2.5.1 runtime the Tools would install is already present (`Microsoft.WindowsAppRuntime.2` 2.5.1.0) [S:local].
- Guide, Windows MIDI Services lane §6: `midi1monitor` now ships in the Tools package [S: Preview 12].

## 10. Open questions

1. Does the Preview 11 copy work with this PC's August midisrv? (P1)
2. Does PyWinRT's list of supported call shapes cover `SendMultipleMessagesWordList`, `FillWords` with its four outputs, and `MessageReceived`? (P1)
3. The KeyLab endpoint's `GetSupportedMaxMidiWordsPerTransmission`.
4. Is the DAW port really group index 1? (P4)
5. At the next hang: does a native listener see keys that WinMM misses, or neither? That decides service versus driver or device. (P5 and the watchdog)
6. Is the KeyLab class compliant, so that it could move off Arturia's driver? Arturia's driver claims the whole USB device (its compatible ids are `USB\COMPOSITE`), which hides the MIDI interface class [S:local]. This belongs to another lane.

Files read:
- E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-hang-study-2026-10-26.md
- E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-dev-guidance-and-hang-guide-2026-10-27.md
- E:\AI-Setup\arsenal\keylab\winmidi.py
- E:\AI-Setup\arsenal\keylab\protocol.py
- E:\AI-Setup\docs\library\design\20261022_a16-d0-control-center-hub_3325c3.md

Scratch encoder (pure computation, no MIDI): <scratch>\ump_sysex7.py

Main sources:
- microsoft.github.io/MIDI: sdk-reference pages for MidiEndpointConnection, MidiSendMessageResultsEnum, MidiEndpointConnectionSettings, MidiClock, MidiSession, MidiApi, MidiDiagnostics, MidiReporting, MidiEndpointDeviceWatcher, MidiMessageReceivedEventArgs and the COM extensions; kb pages kernel-streaming-aggregate, mapping-midi1-port-concepts, data-translation, ump-data-format-primer, moving-from-winmm-to-wms, porting-midi-libraries, api-back-compat, best-practices, minimum-requirements, endpoint-ids, how-to-switch-between-class-drivers
- github.com/microsoft/MIDI (MIT): release notes for inbox-dev-preview-1, -8 and -9 and inbox-preview-10, -11 and -12; `samples/app-manifest/app.manifest`; `src/in-box/Libs/MidiXProc/MidiXProc.cpp`; `Client/WinRT/core/MidiEndpointConnection_SendInfrastructure.cpp`; `Libs/MidiKs/MidiKs.cpp`; `Inc/MidiKS.h`; issues #60, #906, #968, #1016, #1037, #1040, #1084, #1146, #1195, #1263, #1286
- github.com/pywinrt/pywinrt (MIT): docs (installing, threads, versioning, release notes 4.0) and `runtime/src/interp.cpp`
- github.com/microsoft/cppwinrt (MIT): `strings/base_activation.h`, `base_agile_ref.h`
- Learn: LoadLibraryExW
- CPython 3.11: `Doc/library/os.rst`, `Modules/posixmodule.c`
- PyPI and nuget.org metadata; .NET 10 release metadata

---

## Research lane: the USB layer and closer-to-the-metal paths (verbatim)

# KeyLab 88 mk3, the USB layer: what's under the hood, and what "closer to the metal" would really cost (usb-layer lane, 2026-10-27)

## Bottom line

**The keyboard can't be taken more "direct to metal" without breaking FL, Analog Lab and firmware updates, and doing so would not touch the hang's leading suspect.**

- **The stack today.** Every message passes through six layers:
  - our ctypes code;
  - WinMM (`wdmaud2.drv`);
  - the Windows MIDI service (midisrv, on its "KSA" path for older drivers);
  - Arturia's kernel-streaming driver;
  - Arturia's USB driver, which is Thesycon's TUSBAudio 5.72 under Arturia's name;
  - the USB hub and host controller.
- **The bottom is plain USB-MIDI 1.0.** Both KeyLab ports almost certainly share one pair of USB data channels (endpoints), carried as 4-byte packets. There is no faster or simpler protocol hiding under the wrapper. Going lower changes who handles those packets, not what the keyboard receives.
- **Option (c), WinUSB through Zadig: not recommended.** It takes both ports away from FL, Analog Lab, MIDI Control Center and the piano page. WinUSB allows one process at a time. Firmware updates would need the Arturia driver put back first. Its one real gift, seeing what happens on the wire, is available passively from USBPcap with no driver swap.
- **Option (b), Microsoft's open-source class driver: the one "closer to the metal" move worth making, as a controlled experiment.** It replaces the closed Thesycon driver, our top hang suspect, with Microsoft's MIT-licensed driver. FL keeps working if the port names survive, and the evidence says they probably can. The price: Arturia firmware updates need the Arturia driver back, and Analog Lab's integration depends on the names.
- **Option (a), keep the driver and the OS MIDI stack: the right default now.**
  - Fix the four `winmidi.py` defects.
  - Build the doctor and the watchdog.
  - Make the hub the single writer.
  - "The PC does more of the heavy lifting" by sending far less, not by sending lower down.
- **New, and needing no driver change:** two software recovery rungs that were missing from the ladder.
  - `pnputil /restart-device` reloads the driver stack.
  - The documented hub "cycle port" request is a replug without touching the cable.
  - Both need administrator rights, and each run is Daniel's call.
- **Another experiment that leaves the driver alone:** Windows' Legacy API mode removes midisrv and `wdmaud2.drv` from the path. It is machine-wide and fully reversible.

Grades: **[S]** a cited source says it. **[S:local]** a read-only query on this machine shows it (the query is named). **[I]** my inference.

---

## 1. What's under the hood on this PC

All of section 1 comes from read-only queries: Get-PnpDevice, Get-PnpDeviceProperty, `pnputil /enum-devices`, registry reads, file version info, the INF text, and the System event log.

| Layer | What's there | Grade |
|---|---|---|
| Host controller | AMD USB 3.20 eXtensible Host Controller (`PCI\VEN_1022&DEV_43FD`) → USB Root Hub (USB 3.0) → **port 8, no hub in between** (`Port_#0008.Hub_#0002`, BIOS path `...XH00.RHUB.POT8`). Siblings on that root hub: a USB 2.0 hub (1A40:0101) and an ITE device (048D:5711) | [S:local] |
| USB device node | `USB\VID_1C75&PID_02CE\7656400341020110`. Hardware ID `...&REV_1500`. Compatible IDs end in `USB\DevClass_00` and **`USB\COMPOSITE`**, so it is a multi-interface device with no class at device level | [S:local] |
| Who owns the whole device | **Arturia's `arturiausbmidi`** (oem22.inf = `arturiausbmidi.inf`, 1.7.0.0, dated 2025-08-20, signed by Microsoft's hardware program). It matches the whole device by VID/PID at rank `00FF0001`. Windows' own composite driver (`usb.inf`, `USB\COMPOSITE`) also matches but is "Outranked" at `00FF2006`. So Windows never splits the KeyLab into per-interface nodes, and Microsoft's MIDI class drivers never get a chance to match | [S:local: pnputil `/drivers`] |
| What the driver really is | `arturiausbmidi.sys` reports Product "TUSBAudio Class Driver" 5.72.0.0. The KS driver reports "TUSBAudio Kernel Streaming Driver". The API DLLs report "TUSBAudio API DLL". The INF carries a Thesycon-style licence record (customer 1629, version 0x00050048 = v5.72, a list of Arturia VID/PIDs) | [S:local]. Thesycon makes TUSBAudio [S: thesycon.de/eng/usb_audiodriver.shtml] |
| Device stack | `\Driver\arturiausbmidi` → `ACPI` → `USBHUB3` | [S:local: DEVPKEY_Device_Stack] |
| KS child | `TUSBAUDIO_ENUM\VID_1C75&PID_02CE&KS\...` on `arturiausbmidiks` (oem11.inf). Stack: `ksthunk` → `arturiausbmidiks` → `arturiausbmidi`. It registers the KS audio, render and capture interface classes | [S:local] |
| Windows MIDI Services | `SWD\MIDISRV\MIDIU_KSA_16201702556534547415` (class MidiEndpoint), plus four WinMM port nodes under the KS child: `_0_0` "KeyLab 88 mk3 MIDI" and `_0_1` "KeyLab 88 mk3 DAW" (input interface class `{504be32c-…}`); `_1_0` MIDI and `_1_1` DAW (output class `{6dc23320-…}`). So pin 0 = MIDI and pin 1 = DAW, in both directions | [S:local]; GUIDs read as MIDI in/out classes [I] |
| Firmware updates | The INF sets **`DFUProtocol = 2`** for the KeyLab 88 mk3. MIDI Control Center imports `TUSBAUDIO_StartDfuDownload`, `…StartDfuUpload`, `…StartDfuRevertToFactoryImage`, `…GetDfuStatus` and `…LoadFirmwareImageFromFile`, and has a "DFUUpdater" class with bootloader handling. Arturia Software Center's agent carries the same DFU updater and TUSBAudio calls | [S:local: INF; strings in `MIDI Control Center.exe` and `ArturiaSoftwareCenterAgent.exe`] → **firmware updates on Windows run through Arturia's driver** [I] |
| Private API | 81 distinct `TUSBAUDIO_*` names in `arturiausbmidiapi_x64.dll`, **none for MIDI**. There are raw class/vendor control requests, device and driver statistics, and `GetDeviceUsbMode` | [S:local] → MIDI leaves Arturia's driver only through kernel streaming; there is no private MIDI back door [I] |
| What Arturia's driver logs | Only event 3, "Audio Controller initialization failed.", 124 times from 2026-06-16 to 2026-10-26 23:31, once per arrival. Nothing else, ever. The KS driver logs nothing | [S:local: System log] |
| Driver tuning in the INF | Sample-rate and clock-source settings (`KsSampleRateControl`, `RestoreClockSourceAtStart`, `RestoreSampleRateAtStart`) on a MIDI-only device | [S:local] → an audio-interface framework applied to a keyboard; event 3 is probably that audio path failing harmlessly at every start [I] |
| Firmware history | `usbflags` holds one key per revision this PC has seen: `1C7502CE0500`, `…1101`, `…1201`, `…1500`. All have `osvc = 00 00`, meaning the device offers no Microsoft OS descriptor. Two more Arturia PIDs appear: `1C75021B` rev 0100 and `1C7502CB` rev 0200. Neither is in Arturia's INF | [S:local]. 1101/1201/1500 match firmware 1.1.1, 1.2.1 and 1.5.0 [S: the Arturia lane's firmware table]; 0500 and the two PIDs are unexplained (perhaps bootloader identities or other hardware) [I] |
| Firmware without SysEx | REV_1500 matches Daniel's 1.5.0 | [S:local; S: hang study] → `doctor` can print the firmware version from Plug and Play with no SysEx [I] |
| Class drivers present but unused | `usbaudio.sys` 10.0.26100.8972 (the old MIDI 1.0 class driver, via `wdma_usb.inf`, matching `USB\CLASS_01`). **`usbmidi2.inf` "USBMidi2-ACX"** (DriverVer 10.0.26100.9168) is in the driver store and matches `USB\CLASS_01&SUBCLASS_03&PROT_00`, but has never been installed for any device (no service key). `winusb.sys` 10.0.26100.8972 is present | [S:local] |
| usbmidi2's licence | Its INF header is an MIT licence: AMEI, Microsoft, AmeNote | [S:local: `C:\Windows\INF\usbmidi2.inf`] |
| Power | USB selective suspend is **on** in the active plan, on AC and battery. The Windows power-management (WMI) query returned an error ("Invalid object"); I read that as no device-level power control registered for the KeyLab, but did not confirm it | [S:local: powercfg; WMI query]; meaning [I] |
| Port naming setting | `HKLM\SOFTWARE\Microsoft\Windows MIDI Services` has only `Midi2DiscoveryEnabled=1` and the four transports enabled (KSA, KS, Loopback, Virtual). No naming override, so the default applies | [S:local] |
| Native MIDI 2.0 API | **0** `Windows.Devices.Midi2` classes registered. Only the WinRT MIDI 1.0 classes (`Windows.Devices.Midi.dll`) exist | [S:local] |
| Uptime | Device first seen 2025-11-17. Arturia driver installed 2026-06-11. Last arrival 2026-10-26 23:31:45 (Daniel's power cycle) | [S:local] |

**FL's saved KeyLab setup is keyed by WinMM port name.**
- `HKCU\Software\Image-Line\FL Studio 26\Devices\MIDI input\KeyLab 88 mk3 DAW` → ScriptFolder "KeyLab mk3 Akashic".
- `…\KeyLab 88 mk3 MIDI` → "KeyLab mk3 Arturia dev".
- FL also stores each port's identity reply. DAW: `00 20 6B 02 00 0A 08 7F 7F 7F 7F`. MIDI: `00 20 6B 02 00 0A 08 3C 01 01 01`. The device answers differently per port.
- **There is a precedent on this PC:** entries for a KeyLab mkII, "KeyLab mkII 88" and "MIDIIN2 (KeyLab mkII 88)". Those are Windows' classic class-driver names. [S:local; I for the reading]

## 2. What a message looks like at the bottom

- **Packets.** USB-MIDI 1.0 moves MIDI in 32-bit "event packets" over bulk data channels (endpoints). Byte 0 holds a Cable Number (high nibble) and a Code Index Number (low nibble). One endpoint carries up to 16 "embedded jacks" (cables) [S: USB-IF, *Device Class Definition for MIDI Devices 1.0*, https://www.usb.org/sites/default/files/midi10.pdf, section 4; read through a search summary, not downloaded].
- **SysEx framing.** SysEx rides 3 bytes per packet: code 0x4 for start or continue, and 0x5, 0x6 or 0x7 for an end carrying 1, 2 or 3 bytes [I: from my knowledge of the spec's table; not re-read this run].
- **Both ports share one data path [I, strong].**
  - On Linux's in-box driver the KeyLab mk3 shows exactly two ports, "midi" and "daw" [S: forum.arturia.com/t/5294, Bidinou post 7].
  - Linux names them `<iProduct> <iJack>`: "KeyLab 61 mk3 KeyLab 61 mk3 MID" and "…DAW" [S: same thread, post 17, 2025-04-26].
  - Linux builds port names from the card name plus the jack string [S: lkml 2021 patch "generate midi streaming substream names from jack names"; linux-stable commit 0759e77a, Takashi Iwai, 2025].
  - So the KeyLab names its jacks itself, roughly "KeyLab NN mk3 MIDI" and "KeyLab NN mk3 DAW" [I]. It most likely presents them as cables 0 and 1 on one pair of endpoints [I]. Which pin maps to which cable is also [I].
- **What follows: a stall of that endpoint pair kills both ports at once.** That fits the hang's "both ports, both directions" signature [I].
- **The traffic is tiny at USB level.** A 66-byte screen frame is 22 packets, 88 bytes on the wire. At the guide's estimate of about 190,000 frames a day, that is roughly 17 MB a day, seconds of bus time [I: arithmetic]. The load that matters is on the keyboard's own processor (parsing and drawing), not on USB [I].

## 3. Option (a): keep Arturia's driver and talk through the OS MIDI stack

| Variant | What it changes | Costs and risks | Verdict |
|---|---|---|---|
| **a1. WinMM, hardened (today's path)** | Nothing in the system. Fix the four `winmidi.py` defects from guide §4.1: `lpData` should be `c_void_p`; re-queue input buffers off the callback thread and wait ≥20 ms after `midiInStart`; make the `send_sysex` timeout loud; call `midiInStop` before `midiInReset` and check the result codes | Code only | **Do now.** Cheapest robustness win, and the doctor's probe is false without it [S: guide §4.1] |
| a2. WinRT MIDI 1.0 (`Windows.Devices.Midi`) | Adds device connect/disconnect notifications, which WinMM lacks [S: microsoft/MIDI docs/kb/api-back-compat.md] | Same midisrv, KSA and Arturia path. On 25H2, WinRT MIDI 1.0 input goes silent after a replug (#906, open) [S: community lane]. A Cubase user's drops stopped after moving off WinRT [S: forum.arturia.com/t/5892]. Python needs WinRT bindings from PyPI (an install for Daniel to approve) | No |
| a3. Native Windows MIDI Services API (`Windows.Devices.Midi2`) | UMP endpoints, endpoint notifications, scheduled timestamps, virtual devices [S: api-back-compat.md] | "In box in Windows 11 25H2 and later starting in 2027". The preview package `Microsoft.Windows.Devices.Midi2` was "never supported for redistribution … being dropped entirely in 2027" [S: docs/kb/porting-midi-libraries.md]. Not on this PC (0 classes) [S:local]. Still the same KSA and Arturia path below | Revisit in 2027. Not a hang fix |
| **a4. Legacy API mode** (`UseLegacyMidi=1` under `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Drivers32`, restart) | Removes midisrv and `wdmaud2.drv`. WinMM then talks almost straight to Arturia's KS driver [S: docs/kb/how-to-change-api-mode.md] | Machine-wide, needs a restart. "Ports aren't multi-client" except where the driver shares ports itself [S: same doc; api-back-compat.md]. Arturia calls its driver "Multi-Client" [S: Arturia KB 4407871884818]. Thesycon shares input always and output only "optionally" [S: thesycon.de]. So FL plus our hub on the DAW **output** must be tested. Every other device loses multi-client. **Our close path must stop calling `midiOutReset`**: in legacy mode it sends about 2,064 note-off and sustain messages [S: guide §2, Learn `midiOutReset`], and a burst that size could itself freeze the KeyLab [I] | A good, reversible **experiment for "the service is the culprit" (M2)**, not a default |

None of a1-a3 removes Arturia's driver, the leading suspect (M1). They improve how we see and survive a hang, not whether it happens [I].

## 4. Option (b): switch the KeyLab to Microsoft's class driver

**How it would be done (Daniel's hands, FL closed).**
- The KeyLab is one composite device owned whole by Arturia's driver, so the switch has two steps [S:local; I].
  1. Device Manager → "Arturia USB MIDI Devices" → KeyLab 88 mk3 → Update driver → Browse → Let me pick → **"USB Composite Device"** (`usb.inf`, already listed as a matching driver [S:local]). Windows then creates per-interface nodes (`&MI_xx`).
  2. The MIDI-streaming interface then matches both "USBMidi2-ACX" (`usbmidi2.inf`) and "USB Audio Device" (`wdma_usb.inf`) [S:local INFs]. Microsoft's guide shows how to pick between them; the troubleshooting app also has a Drivers page for this [S: docs/kb/how-to-switch-between-class-drivers.md].
- Microsoft's cautions [S: same doc]:
  - close the DAW first;
  - unplug, restart and replug afterwards;
  - "If a device needs a driver from its manufacturer, neither of these two drivers will work for it";
  - "there's a Plug and Play bug … that can put the old driver back after an update."

**Is the KeyLab class compliant?** Very likely at the interface level [I].
- Linux's in-box driver runs it with both ports, and the screen and buttons work [S: forum t/5294 post 17].
- Arturia's manual says it is class compliant on Mac, and that Windows needs Arturia's driver "for Analog Lab and DAW integration" [S: manual p.10, via the Arturia lane].
- I could not see the interface classes from Windows: no per-interface nodes have ever existed here [S:local, absence].

**What survives and what breaks:**

| Thing | On the class driver | Grade |
|---|---|---|
| Multi-client | Kept: midisrv makes every driver multi-client (Arturia's old reason, "class-compliant devices serve one app at a time", predates it) | [S: api-back-compat.md; Arturia KB 6878166158108] |
| Port names | **Decides everything.** Under "Automatic" (the default) or "New style", a device that names its jacks gets those names, used as supplied when they start with the device name. That is likely "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW", the same as today. Under "Legacy WinMM compatible" they become "KeyLab 88 mk3" and "MIDIIN2 (KeyLab 88 mk3)", the same shape as the mkII entries in FL's registry | [S: docs/kb/how-midi1-port-names-are-generated.md and midi1-name-mapping.md]; outcome for the KeyLab [I]. **Caveat:** those docs describe Microsoft's current code on GitHub. Whether this PC's midisrv (10.0.26100.7705) already ships "Automatic" is unverified [I] |
| FL Studio | Works over WinMM either way. If names change, the script assignments (keyed by name) must be redone once in MIDI settings | [S:local: FL registry; I] |
| Analog Lab integration (screen and preset sync) | Arturia staff: "the MIDI name must be the same as on Windows". Linux users had to rename ports to get the screen back. Analog Lab itself uses WinMM and not Arturia's API | [S: forum t/5294 posts 14 and 17; S:local: `Analog Lab V.exe` strings] → fine if names hold, broken if they don't [I] |
| MIDI Control Center | Finds and opens devices through the TUSBAudio API (`TUSBAUDIO_EnumerateDevices`, `OpenDeviceByIndex`) and does DFU through it | [S:local strings] → will not see the KeyLab, and firmware updates fail, until the Arturia driver is back [I] |
| Firmware updates (MCC or Software Center) | Same as above | [S:local; I] |
| Our toolkit | `_match()` picks ports by "keylab" plus "daw"/"midi" substrings. Under legacy names no port contains "daw", and the code would pick the wrong one | [S:local: `winmidi.py:76-89`; I] |
| Staying switched | Arturia's INF outranks the composite driver, so any reinstall of Arturia's driver (MCC, Analog Lab and Software Center installers bring it) re-binds the KeyLab | [S:local ranks; S: Arturia KB 6878166158108; I] |
| Reversal | Same Device Manager path, picking "KeyLab 88 mk3 / Arturia" (oem22.inf stays in the driver store) | [S:local; I] |

**What it buys.**
- It replaces the closed, audio-oriented Thesycon stack with Microsoft's open-source MIDI driver. A hang on it could be read in code we can see [S:local licence; I].
- With usbmidi2, midisrv uses its native "KS" path instead of the KSA translation path [S: docs/kb/kernel-streaming.md, kernel-streaming-aggregate.md].
- Microsoft's maintainer recommends the in-box driver for class-compliant devices [S: microsoft/MIDI #1263, via the community lane]. Microsoft also kept `usbaudio.sys` because the new driver "isn't compatible with every device" [S: switch-drivers doc].
- Most importantly, it is **the A/B test for M1**: same soak on the class driver. No hang points at Arturia's driver; the same hang points at the firmware or midisrv [I].

## 5. Option (c): WinUSB or libusb direct, through Zadig

**What it would take.**
- Bind WinUSB to the KeyLab, either the whole device or, after the composite split in §4, the MIDI-streaming interface. Zadig "replaces" the existing driver, can target one interface (`MI = 0x01`), and signs its INF with "a unique self-signed certificate generated on the fly, which is then installed on the current machine". It also warns that other applications "may no longer be able to access it afterwards" [S: github.com/pbatard/libwdi/wiki/Zadig].
- The keyboard has no Microsoft OS descriptor (`osvc = 00 00`), so WinUSB would never bind on its own; it needs that custom INF [S:local; I].

**What breaks.**
- Both ports leave Windows MIDI, because they share one interface and one endpoint pair [I, §2]. So FL, Analog Lab, MCC and the piano page's Web MIDI all lose the KeyLab.
- WinUSB serves one application at a time ("Supports multiple concurrent applications: No") [S: learn.microsoft.com/…/usbcon/winusb-considerations].
- To keep FL working, our hub would have to be the KeyLab's USB host driver and **re-publish two virtual port pairs** with the right names.
  - Creating virtual devices needs the 2027 in-box API, or the unsupported preview [S: api-back-compat.md; porting doc], or a third-party virtual-MIDI driver.
  - FL's identity check needs the Device Inquiry passed through [S:local: FL's IDString].
  - Every hub crash means a dead keyboard in FL, and every key adds a process hop [I].
- Firmware updates need Arturia's driver back, because they go through TUSBAudio DFU [S:local].
- The self-signed root certificate is a system trust change, Daniel's call [S: Zadig wiki].

**What it buys.**
- Visibility at the endpoint (transfer results, stalls, timeouts) and direct pipe resets [I].
- It cannot stop a firmware hang. If the KeyLab's USB core stops answering, our code sees the same silence, sooner [I].
- The visibility part is available passively from USBPcap with every driver unchanged [S: guide §5.6; I].

**Verdict: no.**

## 6. Closer-to-metal tools that need no driver change

| Tool | What it does | Grade | Use |
|---|---|---|---|
| `pnputil /restart-device "USB\VID_1C75&PID_02CE\7656400341020110"` | Reloads Arturia's driver stack in one command, without cutting power | Present in this pnputil [S:local: `pnputil /?`]. Admin needed [I] | Ladder step 6, scriptable from `doctor --ladder` with Daniel's yes each time |
| `IOCTL_USB_HUB_CYCLE_PORT` (root hub, port 8) | "Power-cycles the port". User-mode, Windows 8+, admin only | [S: learn.microsoft.com/…/usbioctl/ni-usbioctl-ioctl_usb_hub_cycle_port]. Whether this root hub really drops power (VBUS) is hardware-dependent [I] | Ladder step 7 **without touching the cable**. If the KeyLab's screen survives the cycle, power didn't drop and the result separates "USB link" from "whole firmware". If it reboots, it equals step 8 [I] |
| A control-channel (endpoint 0) probe through the hub (`IOCTL_USB_GET_DESCRIPTOR_FROM_NODE_CONNECTION`, the documented call USBView uses) | Asks the device for a descriptor over its control channel, not the MIDI channels | [I]. Not run: it would touch the KeyLab. **Before trusting it as a liveness probe, confirm with USBPcap that the request reaches the wire** (the hub driver caches some descriptors) [I] | A second probe for `doctor`. Control channel answers but MIDI channels don't: the device's USB core is alive and the MIDI function or pipes are stuck. Neither answers: the device's USB stack is gone [I] |
| Firmware from Plug and Play | `REV_1500` = 1.5.0, no SysEx needed | [S:local] | `doctor` usb line |
| Arturia's private API (`TUSBAUDIO_QueryDeviceStatistics`, `GetDeviceUsbMode`, `ClassVendorRequestIn/Out`) | Driver statistics and raw control requests through Arturia's driver | Exists [S:local]. No public header: Thesycon licenses its SDK to its customers [S: thesycon.de] | **Don't build on it** (closed licence, undocumented). Facts only |
| USBPcap (see §8) | Passive capture of every packet, drivers unchanged | [S: guide §5.6] | Settles M1 vs M2 vs firmware at the next hang |

## 7. Recommendation, honestly ranked

1. **Option (a) now, no system changes:**
   - fix the four `winmidi.py` defects;
   - build `doctor` (add the firmware-from-Plug-and-Play line and FL's stored identity replies) and the watchdog;
   - make the hub the only process that opens the DAW output (D0, R0.1-R0.2). That also closes the per-process governor gap.
   - **"The PC does the heavy lifting" by sending less:** send only changed pads (PadRenderer already does this), coalesce, and make the 2 s screen resend conditional instead of constant. Rough cost: 43,200 identical frames a day from a 2 s resend, ~190,000 with `--pulse` [I]. That is the direct lever on hypothesis T1 (days of constant traffic) [I].
2. **At the next hang:** walk the ladder with the two new software rungs (restart-device, then cycle port) before any power cycle. Note the time and the rung that worked [I].
3. **Then one change at a time, each soaked with the watchdog running:**
   - **(b) the class-driver A/B** for M1. Check the port names first; revert at once if FL or Analog Lab can't see "KeyLab 88 mk3 DAW", and revert before any firmware update.
   - or **(a4) Legacy API mode** for M2.
   - Don't stack them, and don't stack either with the selective-suspend change (T5) [I].
4. **USBPcap** only if steps 2-3 leave M1 and M2 tied.
5. **Not option (c).** Its costs fall on FL, Analog Lab and firmware updates; its benefit is available passively.

The hub (D0) is unaffected by any of these choices. It owns the DAW output through whatever driver is bound, and should open ports by stable identity rather than by name substrings, so that a driver or naming change can't silently re-point it [I].

## 8. Downloads, installs and settings for Daniel's approval (none done)

| What | Source | Size | Why |
|---|---|---|---|
| USBPcap 1.5.4.0 (installs a kernel USB filter driver) + Wireshark | github.com/desowin/usbpcap; wireshark.org | 195,040 bytes [S: guide §5.6]; Wireshark not checked | Wire-level truth at the next hang |
| Windows MIDI Services Tools 0.99.94-preview.12 | github.com/microsoft/MIDI/releases/tag/inbox-preview-12 | 223,376,824 bytes [S: guide §5.6] | Troubleshooter Drivers page for (b); `midiksinfo` (the kernel-streaming pin view); endpoint monitor |
| Thesycon USB Descriptor Dumper (`tdd.exe`) | thesycon.de [S: #1061, via the Windows MIDI lane] | Not checked | Read the KeyLab's interface layout once. It asks the device for its descriptors, so run it with the KeyLab idle and FL closed |
| Setting: driver switch for (b) | Device Manager | — | The class-driver experiment |
| Setting: `UseLegacyMidi=1` + restart | regedit, per the Microsoft doc | — | The midisrv experiment (a4) |
| Setting: admin rights for the recovery rungs (an elevated prompt or a scheduled task) | — | — | `doctor --ladder` restart-device and cycle-port steps |

## 9. Questions for Daniel

1. Did you ever install or update KeyLab firmware **without** MIDI Control Center or Analog Lab? This decides whether (b) can coexist with updates, or only be switched off before them.
2. Do the Arturia PIDs `021B` and `02CB`, and the KeyLab revision `0500`, ring a bell: another Arturia device, or a bootloader session?
3. Under (b), would you accept redoing FL's two script assignments once, if the names change?

## 10. Lane conduct

- **Rule slip:** one Bash command used `cd "/c/Program Files (x86)/Arturia/MIDI Control Center"`, outside the repository, to list that folder. It was read-only and in a throwaway subshell. Every later command used absolute paths.
- The tool harness automatically saved a copy of `C:\Windows\INF\oem22.inf` (the 224 KB text) to the session's tool-results folder when its output was too long to display. It is a copy of a local system file, not a download.
- Never touched: the KeyLab, its MIDI ports, FL Studio, ports 8793/8794/8796, any driver, service or setting.
- No downloads (WebFetch was used on HTML pages only; GitHub was read through `gh api` to stdout), no installs, no repo edits, no commits.
- Everything else was read-only: Plug and Play and registry queries, INF text, file versions, string searches in installed binaries, the event log, `pnputil` enumeration and help, `powercfg /q`.

Files read:
- E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-hang-study-2026-10-26.md
- E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-dev-guidance-and-hang-guide-2026-10-27.md
- E:\AI-Setup\arsenal\keylab\winmidi.py
- E:\AI-Setup\docs\library\design\20261022_a16-d0-control-center-hub_3325c3.md
- C:\Windows\INF\oem22.inf (arturiausbmidi.inf), C:\Windows\INF\oem11.inf (arturiausbmidiks.inf), C:\Windows\INF\usbmidi2.inf, C:\Windows\INF\wdma_usb.inf
- C:\Program Files\Arturia\USBMidiDriver\x64\ (driver, KS driver and API DLL versions)

Sources:
- [Microsoft: How to switch between MIDI class drivers](https://github.com/microsoft/MIDI/blob/main/docs/kb/how-to-switch-between-class-drivers.md)
- [Microsoft: How MIDI 1.0 port names are generated](https://github.com/microsoft/MIDI/blob/main/docs/kb/how-midi1-port-names-are-generated.md)
- [Microsoft: Map MIDI 1 port names to new endpoints](https://github.com/microsoft/MIDI/blob/main/docs/kb/midi1-name-mapping.md)
- [Microsoft: Kernel Streaming Aggregate transport](https://github.com/microsoft/MIDI/blob/main/docs/kb/kernel-streaming-aggregate.md)
- [Microsoft: Kernel Streaming transport](https://github.com/microsoft/MIDI/blob/main/docs/kb/kernel-streaming.md)
- [Microsoft: Application backwards compatibility](https://github.com/microsoft/MIDI/blob/main/docs/kb/api-back-compat.md)
- [Microsoft: How to change the API mode](https://github.com/microsoft/MIDI/blob/main/docs/kb/how-to-change-api-mode.md)
- [Microsoft: Minimum requirements](https://github.com/microsoft/MIDI/blob/main/docs/kb/minimum-requirements.md)
- [Microsoft: Porting a MIDI library](https://github.com/microsoft/MIDI/blob/main/docs/kb/porting-midi-libraries.md)
- [Microsoft Learn: Choose a driver model (WinUSB)](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/winusb-considerations)
- [Microsoft Learn: IOCTL_USB_HUB_CYCLE_PORT](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usbioctl/ni-usbioctl-ioctl_usb_hub_cycle_port)
- [Thesycon TUSBAudio](https://www.thesycon.de/eng/usb_audiodriver.shtml)
- [Thesycon TL-USB DFU](https://www.thesycon.de/eng/usb_dfu.shtml)
- [Zadig (libwdi wiki)](https://github.com/pbatard/libwdi/wiki/Zadig)
- [USB-IF MIDI 1.0 class definition](https://www.usb.org/sites/default/files/midi10.pdf) (cited, not downloaded)
- [Arturia forum: KeyLab mk3 on Linux](https://forum.arturia.com/t/status-of-keylab-mk3-analog-lab-on-linux/5294)
- [Arturia: Firmware updates procedures](https://support.arturia.com/hc/en-us/articles/19308012283036-Firmware-updates-procedures)
- [Arturia: Firmware update failures](https://support.arturia.com/hc/en-us/articles/19388096110364-Firmware-updates-failures-What-can-I-do)
- [LKML 2021: substream names from jack names](https://lkml.iu.edu/hypermail/linux/kernel/2102.2/04029.html)
- [linux-stable 0759e77a: duplicated MIDI substream names](https://git.sceen.net/linux/linux-stable.git/commit/sound?id=0759e77a6d9bd34a874da73721ce4a7dc6665023)

---

## Research lane: the protocol in depth, for robust delivery (verbatim)

**The KeyLab 88 mk3 does not confirm anything we send it: no acknowledgement, no error reply, no state report, in any source we have. The one message we know it answers on this unit is the standard Device Inquiry.** So robust delivery has to be built on the PC, as state-based delivery:

- the hub keeps the authoritative picture of what the device should show;
- it sends only absolute "set this element to this" packets, and only for elements that changed;
- it uses the Device Inquiry as a heartbeat and as a fence at the end of a batch;
- it repaints the whole picture whenever there is evidence the device lost its state.

Neither the device nor the host can confirm that a colour or a frame actually rendered. Only Daniel's eyes, or a camera, can.

Grades: **[S]** a cited source, **[S:local]** read or measured on this machine, **[I]** my inference. Line numbers are as read today. Bitwig is cited at commit 43c1a00153 (MIT), saxofonbrian at 6321b072a1 (MIT). Arturia's FL scripts and the Ableton Live decompile are facts only.

---

## 1. What the KeyLab sends back to the host

| Message | When | Use for delivery | Grade |
|---|---|---|---|
| **Identity reply** `F0 7E 7F 06 02 00 20 6B 02 00 0A <model> v1 v2 v3 v4 F7`, 17 bytes | Every time we asked: 4 of 4 on each port during the 20 s capture of 10-26 23:34, arriving in the same 10 ms print tick as the inquiry. None at all during the hang. | The only confirmed request and reply. Proves a full round trip through the device's MIDI layer. | [S:local] `liveness_fresh.txt`, hang study. Prefix: [S] Bitwig `MidiProcessor.java:130`. Length: [S:local] |
| Model byte | `02`, `04`, `08` for the 49, 61 and 88 | Confirms which unit answered | [S] `device_KL3.py:2`. That `08` is the 88: [I], matching MCC's `familyMemberId "0588"` [S:local] `KeyLab3 88.json` |
| Version bytes | Part of the reply | Firmware check. MCC formats the version as `"$3.$2.$1"`, so 1.5.0 should read v1=00, v2=05, v3=01. Our capture cannot show them yet (the `lpData` bug below). | [S:local] `KeyLab3 88.json` firmwareFormat; [I] |
| Pad hits in the DAW bank | User action | Shows the device is alive and in DAW mode. Says nothing about our writes. | [S:local] `99 00 7F` (channel 10, note 0) followed by pressure on **channel 1**, `A0 00 xx`; [S] `KL3Process.py:350-355` (notes 0-11) |
| CCs in DAW mode: transport 20-27 and 41-44, screen buttons 45-52, faders 105-113, encoders (relative), touch CCs, dial 116/117 | User action | Passive mode detection: in Arturia mode the same controls send different CC numbers | [S] saxofonbrian "CC in DAW mode" and "CC in Arturia mode"; `KL3Process.py:286-332` |
| **Acknowledgement of LED, screen, connect or properties writes** | **None known** | — | [S, by absence] Arturia's FL script never reads anything back (no `OnSysEx` in `device_KL3.py`). Bitwig waits a fixed 1 s after connect (`MidiProcessor.java:133`) and only logs other SysEx (:135). saxofonbrian lists no reply. Bounded: we have **no capture of our own** that listened while writing LED or screen SysEx to a healthy unit [S:local] |
| **Unsolicited mode or program report** | **Unknown for the mk3** | Would be a free "back in DAW mode, repaint" trigger | The sibling devices do send one: Essential mk3 `21 11 40 02 00 <mode>`, pad mode `21 11 40 00 00 <m>` [S] `essentialMk3/.../SysExHandler.java:27-28, 140-153`; MiniLab 3 `02 00 40 62 01/02` [S] `MiniLab3Process.py:168-171`. No mk3 source handles one [S] |
| Configuration read reply `21 09 40 lo hi value` | Answers `20 09 40 lo hi` | An Arturia-native query: it would prove Arturia's own SysEx parser is alive and could read stored settings | [S] saxofonbrian, "The configuration family 21 03 40". The read and reply rows are not marked as measured there. Untested on our unit. |
| NAK or parser errors | None reach the host as far as we know | — | The firmware has internal strings such as "unknow screen Id in SysEx42 Display" [S:local, earlier firmware lane, `keylab-mk3-surface-map-2026-10-22.md:38`]. No evidence they are ever sent out [I] |

**How the protocol is built, as far as the sources show:** after `F0 00 20 6B 7F 42`, payload byte 0 is a **command ID**, byte 1 the patch (01 Arturia, 02 DAW), and byte 2 the parameter type (00 properties, 03 LED, 04 display, 05 connection, 06 bank, 07 program, 08 soft connection).
- Bitwig calls byte 0 "Command ID" for the sibling Essential mk3 [S] `SysExHandler.java:197`.
- The parameter types come from `ParamId.py:25-33` [S].
- Command values seen for the mk3 LED packet: `00` (Arturia, renders colour here), `02` (Arturia in `KL3Return.py:209, 221, 231`; renders white on our unit, [S:local] README), and `04` (Bitwig's LED packet for every light, [S] `RgbButton.java:26-36`; never tried here).
- In the sibling dialect (MCC calls it arturia_v3), `01` is a GET that the device answers: MiniLab 3 "REQUEST PAD" `01 00 40 03` and "REQUEST MODE" `01 00 40 01` [S] `minilab3/SysExHandler.java:94-101`. The mk3 is arturia_v4 [S:local, MCC JSONs], and saxofonbrian's read uses `20`/`21`.
- In both dialects the reply seems to echo the request's second byte (`01 11 …` → `21 11 …`; `20 09 …` → `21 09 …`). That suggests a transaction ID we could use to match replies [I, a guess from two dialects].
- `eProgram` (07) and `eBank` (06) are in Arturia's list but no script sends them. Bitwig defines `00 02 06 01` and never sends it [S] `MidiProcessor.java:37`.

## 2. What the host can ask

1. **Device Inquiry** `F0 7E 7F 06 01 F7`. Measured here, including while FL was open (10-27 00:36, no visible disruption) [S:local, hang study].
   - FL, Bitwig and Live all use it as their identity check [S, integrations lane].
   - The reply goes to every app with the input open, FL included [I, Windows MIDI lane]. How FL reacts to a stray reply is unknown beyond that one observation [I].
2. **Configuration read** `20 09 40 lo hi` [S saxofonbrian]. Unknown risk on firmware 1.5.0. The neighbouring write (`21 03 40`) instantly throws the unit into User mode with no way back except a physical press [S], so a typo is costly. Needs Daniel's explicit go and a bench session.
3. **Global-parameter reads.** MCC holds the global settings (DAW Protocol, Display Brightness, Sleep Mode, Welcome Page, Low Power and others) at `paramId 64` (0x40) with a `globalParamId` [S:local] `KeyLab3 88.json`. The exact read packet MCC uses is not in any readable source [I]. It lives in the MCC binary, which is VM-only work under the house reverse-engineering rule.
4. **No state dump, current-program query or LED read-back** exists in any source for the mk3 [S, by absence]. Arturia's sibling scripts define `MemoryRequest()` but never call it [S:local, grep of the MiniLab 3 and Essential mk3 folders].

## 3. Signals on the host side (each hop, not end to end)

| Signal | What it proves | What it can't prove |
|---|---|---|
| `midiOutLongMsg` returns 0 | The service finished its write to Arturia's driver. The call is synchronous with a "send complete" wait [S, Windows lane: `MidiSrvPort.cpp`, `MidiXProc.cpp`] | That the device received, parsed or showed it |
| Returns 1 (`MMSYSERR_ERROR`) | The write did not complete within 1 s. The pipe is marked stalled and later sends are dropped [S, same] | Which layer stalled |
| Returns 6 (`MMSYSERR_NODRIVER`) | The device left, or left and came back. Close, wait 2-3 s, reopen by name [S #1267, #696] | — |
| `MHDR_DONE` flag | Nothing. It is already set when the call returns on the new stack [S/I, lane]. Our 1 s wait in `winmidi.py:143-145` never waits [S:local] | — |
| A frame visible on screen | Nothing about now: the frozen "Dbadd9" frame survived the hang [S:local, hang study] | — |

## 4. How the integrations keep the surfaces correct

**Arturia's FL script: repaint everything, never check.**
- No pacing and no dedup; every packet goes straight out [S] `KL3Dispatch.py:64-66`.
- About 48 packets at start [S] `KL3Return.py:92-147`.
- A full LED repaint on any `OnRefresh` except flags 4 and 4096 [S] `device_KL3.py:141-152`.
- Repaints DAW pads 82-93 on every song step during playback [S] `KL3Return.py:218-265`.
- Keeps a cache of the footer labels, with a "refresh all" [S] `KL3Pages.py`, `PagedDisplay.SetButton` and `RefreshAllCTXButtons`.
- No identity gate, no reconnect.

**Bitwig, KeyLab mk3:**
- Asks the identity question first, sends the DAW connect only after a reply, and draws "Connected" 1 s later. It never retries [S] `MidiProcessor.java:55-58, 129-143`.
- The framework holds the wanted state of every light. `flush()` calls `updateHardware()` [S] `KeylabMk3ControllerExtension.java:218-221`. A packet goes out only when a light's state changed, compared on RGB plus blink [S] `RgbLightState.java:74-87`, `RgbButton.java:47-67`. That this fires only on change is the framework's behaviour [I].
- **Forced resend for a known overwrite:** `refreshLight()` clears the state so the next flush resends it [S] `RgbButton.java:51-53`. It is called when Back is released [S] `ContextScreen.java:96-98`, which suggests the firmware changes that LED itself when the button is pressed [I].
- A 50 ms tick re-evaluates blinking lights, so only changes go out [S] `MidiProcessor.java:64-80, 98-112`.
- Screens are sent on every value change, with no pacing, dedup or replay [S] `ContextScreen.java:126-140, 330-334`.
- No re-identify, no periodic refresh, no recovery [S, by absence].
- Sends disconnect on exit [S] :94-96.

**Bitwig, Essential mk3 (sibling):** the only recovery loop in the family [S] `SysExHandler.java:79-108, 126-139, 180-194`:
- every outgoing SysEx is held in a queue until the handshake completes;
- after 1 s with no reply it sends disconnect, waits 100 ms and asks again;
- a reply sends the connect and re-activates processing;
- it parses the device's mode reports.

**Bitwig, MiniLab 3 (sibling):** [S] `minilab3/SysExHandler.java:94-148`
- connect, then a query for the pad state and one for the mode, 3 ms apart;
- drops a message identical to the last one sent;
- waits 2 ms after each pad packet;
- holds packets until processing is ready.

**Ableton Live:** [S, integrations lane; facts only]
- sends the inquiry twice and waits 0.5 s;
- on a reply, sends its hello and then `refresh_state()`, a full repaint;
- re-identifies when the ports change;
- LEDs, the home screen and labels are sent only when changed; popups are not deduplicated.

**saxofonbrian:** [S] "Sending, in practice"
- one complete message per call (sending raw single bytes lost 2-4% of packets);
- a 60 ms queue between screen packets, because two back-to-back screen packets race on the device and one is silently dropped;
- a per-LED cache in KeyLabLive.

**Ours today:**
- `PadRenderer` keeps a per-pad cache and sends only changes, with `resync()` [S:local] `ledframe.py:21-53`.
- `ScreenWriter` sends only changes, the newest frame wins, 100 ms minimum spacing, and an optional blind re-send [S:local] `screen.py:404-470`.
- The VJ engine's `PadPainter` repaints the pads after a DAW-pad press [S:local] `vj.py:1520-1565`.
- Our FL script keeps "wanted" and "shown" caches, paces itself, and repaints everything on `OnDoFullRefresh` [S:local] `fl/device_AuroraKeyLab.py:126-176, 339-353`.

**The flaw shared by all our caches:** they mark an element "shown" when `midiOutLongMsg` returns 0. During a hang the cache believes the pads are painted, and after a power cycle nothing repaints unless someone calls `resync()` [S:local; I].

## 5. How long the device keeps what we send

| Event | Effect | Grade |
|---|---|---|
| Nothing happens | LED colours stay latched | [S:local] `ledframe.py` docstring, from observation |
| DAW disconnect | Every LED is cleared | [S:local] Rill's lesson, 10-26 21:40 |
| Program switch away and back | Pads go to resting white, so the painted state is lost | [S:local] Rill's note, 10-26 21:55 |
| Power cycle | Pads show a yellow-to-red gradient, screen is black, and the DAW handshake must be sent again | [S:local] hang study; [S] saxofonbrian ("screen stayed dead" without a reconnect) |
| Sleep, then wake on a key | The screen came back with its last frame (seen during the hang). Pads after a wake: unknown | [S:local]; [I] |
| Popup 23/24/25 | Gone after about 1 s. Whether the previous persistent screen comes back by itself is **unknown** | [S:local] README |
| FL with Arturia's script | Repaints the DAW pads every step and the LEDs on every refresh | [S] `KL3Return.py:258-265` |
| Screen-button LEDs | Can only be set through the footer screen packets (`00 02 04 <id>`), not the LED family | [S] saxofonbrian "Screen buttons" |

What the hub must hold and replay:
- the 12 pads (DAW bank);
- the 34 button LEDs;
- the 8 footer packets (labels and colours);
- the persistent screen;
- the pad-port property `00 02 00 14 02 01 00` [S] `KL3Return.py:147`;
- whether it owns the DAW session.

## 6. What the hub design (D0) already specifies, and its gaps

**Already in D0** (`docs/library/design/20261022_a16-d0-control-center-hub_3325c3.md`):
- One process owns the DAW output (R0.1, lines 57-60, 131).
- One governor shared by every layer and client (R0.2).
- A pure compositor (theme, mode, overlay, alert layers) feeding `PadRenderer`, which sends only changes (lines 75-83).
- An LCD lane with at least 60 ms spacing; popups expire back to the persistent screen (85-86). That matches saxofonbrian's 60 ms [S].
- Last-write-wins coalescing with a counter (126-128).
- `resync()` and a full repaint at start, plus a dead-man (109-113).

**Gaps** [I, except where cited]:
1. **No identity gate or liveness check.** D0 was written before the hang study.
2. **It repaints only when the hub starts.** It should also repaint on:
   - the port reappearing;
   - a fresh reply after silence;
   - a return to DAW mode;
   - FL handing over;
   - a known overwrite.
3. **The clean exit sends `daw_connect(False)`.** With FL open, that would clear FL's LEDs, against the house rule of never sending connect or disconnect while FL runs. It must only happen when the hub owns the session.
4. **The 2 s blackout watchdog would have to open the DAW port itself.** That makes a second writer, against R0.1, and it would paint into a link that may be the thing that hung.
5. **Port 8794 is now the VJ engine's** [S:local] README `vj` row.
6. **The hub cannot govern FL's own writes.** D8's "Aurora Link" relay (lines 85-97) is the only way to make it a true single writer while FL is open.

## 7. What we can rely on (ranked)

1. **Desired-state cache plus absolute writes plus change-only sending.** Every LED and screen packet is an absolute "set", so re-sending is always safe [S: packet shapes]. All three mature integrations use this pattern [S]. This is the "PC does the heavy lifting" design. **Reliable [S/I].**
2. **The identity reply as a heartbeat.** Silence means the link or the device is stuck [S:local]. **Reliable now** for detecting presence, even before the `lpData` fix, because the bytes we match on (`7E`, `06 02`) come before the first `00` [S:local] `keylab_liveness.py` filter. Checking the version bytes needs the fix.
3. **The identity reply as a fence.** Within one client the service keeps order [S, Windows lane], and the reply travels the same port and parser as our SysEx. So a reply after a batch should mean the device's MIDI layer took in the whole batch [I]. It does **not** prove the packets were applied: screen packets can be dropped on the device [S saxofonbrian]. **Plausible; needs E3 below.**
4. **"Epoch" resets.** Treat any of these as "the device forgot", clear the cache, then gate on a reply and repaint everything:
   - the port vanishing or returning;
   - error 6;
   - a reply after a run of silences;
   - DAW-port traffic resuming after only MIDI-port traffic;
   - an FL start or stop.

   **Reliable as a policy [I]**, built from the facts in section 5.
5. **Send result codes as negative confirmation only.** 0 means the driver accepted it; 1 means the device or driver is not draining (stop painting and probe); 6 means close, wait and reopen [S]. **Reliable for detecting failure, never success.**
6. **Targeted resend after a known overwrite** (a press of Back, an FL repaint, a DAW-pad press) [S Bitwig; S:local vj].
7. **Replace the blind re-send every 2 s with the triggers above.** Days of constant traffic is the leading hang suspect (T1) [S, guide §3.2]. A heartbeat every 5 minutes plus event-triggered replay costs far less [I].
8. **For drills and soak tests only: Daniel's eyes or a camera on the pads.** This is the only end-to-end proof of rendering [I].

**Not reliable:**
- the `MHDR_DONE` flag;
- "no error";
- a frame visible on the screen;
- a cached `shown` state after any epoch event.

## 8. Experiments that would settle the unknowns

None of these were run. Each needs Daniel's go, FL closed, and a liveness check before and after. All but E1 need the `lpData` fix and buffer re-queueing in `winmidi.MidiIn` first [S:local `winmidi.py:43, 239-258`].

- **E1, receive-only census.** Listen on both inputs while Daniel switches Prog DAW → Arturia → User → DAW, lets the unit sleep, wakes it, and opens and closes Settings. Does the mk3 report mode or sleep the way its siblings do?
- **E2, echo census.** Send one each of LED, screen, connect and the properties packet, 2 s apart, while listening on both inputs. Is there any acknowledgement?
- **E3, fence.** Twenty inquiries alone versus twenty inquiries each sent after 12 LED writes; compare reply latency. Does the reply queue behind our SysEx?
- **E4, port symmetry.** Ask on the DAW port only. Which inputs carry the reply?
- **E5, configuration read** (riskiest; explicit go). One `20 09 40 53 01` (pad 1, bank A record per saxofonbrian). Never send `21 03 40`.
- **E6.** Does the persistent screen come back by itself after a popup? (eyes)
- **E7.** Do the painted pads and screen survive sleep and wake? (eyes)
- **E8.** Do the version bytes match Settings > Global (1.5.0) under MCC's `$3.$2.$1` format?
- **Also untested:** command ID `04` (Bitwig's) against `00`.

## 9. Daniel's "more direct to metal" idea, within this lane

The packets above are already the device's own protocol. The wrapper in between is WinMM → midisrv → kernel streaming → Arturia's driver 1.7.0.0, which is built on Thesycon's framework.

- **Thesycon API.** `C:\Program Files\Arturia\USBMidiDriver\x64\arturiausbmidiapi_x64.dll` exports 83 `TUSBAUDIO_*` functions [S:local]. Among them:
  - `QueryDeviceStatistics`, `QueryDriverStatistics`;
  - `RegisterDeviceNotification`, `ReadDeviceNotification`;
  - `ClassVendorRequestIn` and `ClassVendorRequestOut`: USB control requests, a separate path from the MIDI data;
  - `GetDeviceUsbMode`;
  - and the firmware-update `StartDfu*` functions.

  This could be a health probe that does not depend on MIDI, and would help tell a USB-link stall (M1) from the rest [I]. The function signatures and structures are only in Thesycon's licensed SDK, so whether it is usable is **unknown**. The firmware-update calls must never be touched.
- **Raw WinUSB** would mean replacing Arturia's driver, which breaks FL, Analog Lab and MCC. Not recommended [I].
- **The Windows MIDI Services native API** belongs to the transport lane.

The biggest win available today is not a lower layer. It is to stop sending what the device already shows, and to have one owner of the port.

## 10. Rule notes

- **Rule slip:** I parsed the export table of Arturia's driver DLL with `pefile` on the host before loading the reverse-engineering skill. The house rule counts parsing a binary we did not build as VM work. Nothing was executed.
- After loading the skill I did **not** run the planned strings scan of the firmware or MCC binaries. Both are listed as VM work for Daniel to decide.
- GitHub sources were read with `gh api` to stdout only. Nothing was downloaded or installed, nothing touched the KeyLab, its ports, FL or ports 8793/8794/8796, and there were no repo edits or commits.

**Files cited:**
- E:\AI-Setup\docs\library\design\20261022_a16-d0-control-center-hub_3325c3.md
- E:\AI-Setup\docs\library\design\20261022_a16-d8-fl-script-handoff_3384d8.md
- E:\AI-Setup\arsenal\keylab\winmidi.py
- E:\AI-Setup\arsenal\keylab\ledframe.py
- E:\AI-Setup\arsenal\keylab\governor.py
- E:\AI-Setup\arsenal\keylab\screen.py
- E:\AI-Setup\arsenal\keylab\vj.py
- E:\AI-Setup\arsenal\keylab\fl\device_AuroraKeyLab.py
- E:\AI-Setup\arsenal\keylab\README.md
- E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-hang-study-2026-10-26.md
- E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-dev-guidance-and-hang-guide-2026-10-27.md
- %USERPROFILE%\Documents\Image-Line\FL Studio\Settings\Hardware\Arturia KeyLab mk3\ (device_KL3.py, KL3Dispatch.py, KL3Connexion.py, KL3Process.py, KL3Return.py, KL3Plugin.py, KL3Pages.py, ParamId.py)
- %USERPROFILE%\Documents\Image-Line\FL Studio\Settings\Hardware\Arturia MiniLab 3\ and \Arturia KeyLab Essential mk3\
- C:\ProgramData\Arturia\MIDI Control Center\Resources\KeyLab3 88.json
- C:\Program Files\Arturia\USBMidiDriver\x64\ (arturiausbmidi.inf, arturiausbmidiapi_x64.dll)
- <scratch>\liveness_fresh.txt and keylab_liveness.py

---

## Fix round 1: the fixer's report (verbatim; branch worktree-wf_efc891a3-dd0-1)

All five fixes and the README correction are committed on branch `worktree-wf_efc891a3-dd0-1`. Each fix has a hardware-free test that fails on the old code and passes now. `py -m pytest tests/test_keylab_*.py` gives 521 passed, 4 skipped [S:local]. One requirement is not met: the branch diff still changes `docs/PHYSICS.md` and `docs/PRIOR_ART.md` (see "Not met" below).

Nothing touched the KeyLab, its ports, FL or ports 8793/8794/8796. I downloaded and installed nothing, and did not push or touch master.

**Commits** (worktree `E:\AI-Setup\.claude\worktrees\wf_efc891a3-dd0-1`, based on 420b8d3a9; master has since moved to e660d6175):
- `f9b9f024e`: the winmidi fixes, the port-wide governor, and the tests.
- `df77deb28`: the README burst row and Files line.
- `32c61f5f5`: a bucket holds at most 128 admit times, and trimming an oversized bucket is now linear.

**The fixes.** All "before" readings were measured on the old code against a fake winmm, `tests/keylab_fake_winmm.py` [S:local].
1. **`lpData` is now `c_void_p`.**
   - Before: an identity reply was captured as `F0 7E 7F 06 02 00 00 00 30 F3 0B 25 CB 01 00 00 00`, cut at the first 00 and filled with junk.
   - After: all 17 bytes come back exactly. The struct layout is unchanged; a test checks this.
2. **`MidiIn` re-queues its buffers.**
   - Before: the input went dry at reply 4 of 30 with 4 buffers, and `start()` returned 0.4 µs after `midiInStart`.
   - After:
     - All 30 replies arrive through 4 buffers, with no WinMM call on the callback thread.
     - Buffers go back to the driver from a separate re-queue thread. The bookkeeping lives in `_dispatch`, so subclasses that replace `_cb` (like `vj.LiveIn`) keep working.
     - `start()` waits 20 ms after `midiInStart`.
3. **`send_sysex` reports what happened.**
   - Before: a header the driver never handed back caused a silent 1.0 s wait, then an unprepare that the driver refused, then the buffer was dropped. A prepare or unprepare failure was silent or unnamed.
   - After:
     - A timeout raises `SysexTimeout`, and the header is kept alive instead of freed. It is reclaimed on the next send or at close.
     - Each failing step raises `WinMMError` with its name and MMRESULT.
     - `out.sends` keeps the codes and timing of the last 256 sends.
4. **`MidiIn.close` order and result codes.**
   - Before: no `midiInStop` call, and a close that returned 65 passed silently.
   - After:
     - Close runs stop, reset, unprepare, close, and checks every code. A failure prints one line on stderr and raises.
     - `stop()` returns its code instead of raising, so `m.stop(); m.close()` always reaches close.
     - After a failed close (the leak after a power cycle, microsoft/MIDI #1157), the callback and buffers are kept alive for the life of the process.
5. **The burst governor is now port-wide.**
   - Before: three processes together reached **36 per 100 ms**, and two outputs in one process reached 24.
   - After: 12 in both cases.
6. **README:** the burst row now says the "~36" is inherited, not measured on this unit; Arturia's FL script sends about 48 at start; the ceiling is per port across processes; FL's scripts send outside it. The `MidiIn` docstring now names its tests and what is still unconfirmed.

**How the port-wide governor works** (`governor.PortGovernor`, same API as before; `MidiOut` builds one keyed by the port it opened):
- **Storage:** one small JSON file per port in the main checkout's `state/arsenal/keylab/governor/`, so tools run from a worktree share it. A "2- " rename prefix maps to the same port.
- **Locking:** an OS byte-range lock, which Windows releases if its holder dies.
- **Clock:** `time.perf_counter`, which on Windows is the machine-wide QueryPerformanceCounter [S:local: they differed by 0.9 µs in one reading].
- **Fairness:** each send reserves the next free slot in arrival order, plus a 2 ms margin for late wake-ups. My first version without reservations let one process starve another, which the overlap check caught.
- **Failure handling:** a corrupt file costs one window's wait and is rewritten; a lock held for more than 2 s costs one window; a folder that can't be written falls back to the old in-process ceiling.
- **Cost:** an uncontended admit takes 15 µs median, 21 µs p99 [S:local].
- **The headline test:** `test_three_processes_on_one_port_never_exceed_the_ceiling_together` starts three real processes on one start time, each flooding 36 packets. It checks that the floods overlapped and that the merged admit times are at most 12 in any 100 ms (and exactly 12, so the budget is used). It passed five runs in a row.

**Not met: `docs/PHYSICS.md` and `docs/PRIOR_ART.md`.** The pre-commit hook rewrites both on every commit. PHYSICS.md carries "Derived at <sha>", and the only ways around the hook are `--no-verify` or plumbing, which I didn't use. At merge, run `git checkout master -- docs/PHYSICS.md docs/PRIOR_ART.md`. Master's PHYSICS.md also appears to have been generated from a working tree with uncommitted changes: the `TEMP` row and `_BOUNDED_READ_CAP` differ from what the committed code produces [I].

**Other notes:**
- The authorship hook added two lines to `state/authorship/seats.jsonl`; they are left uncommitted because they weren't a named path.
- Two CI checkers already fail, from causes outside these files: duplicate class names in `core/`, and the PHYSICS sheet being stale.
- **FL script mismatch:** the committed copy (sha1 EFF394A6…) is consistent: its header says it "never colours a pad" and `OnInit` doesn't. The uncommitted copy in the main tree has `OnInit` painting `HUE_RAMP` (lines 306-312) while its header (line 21) still says "never colours a pad". I didn't edit it. Its own pacing counts outside the port bucket.

**Choices for Daniel or Rill:**
- The budget is per port, so the MIDI and DAW ports each get 12 per 100 ms even though they share one USB link. Counting them as one device is a one-line change to the key.
- The deliberate limit probes (`ledbench burst`, the probe's burst) don't write into the shared bucket.
- `MidiOut.close` does not raise by default (it prints a line); `MidiIn.close` raises.
- Close still calls `midiOutReset`, which in legacy mode sends about 2,064 note-offs.
- Like a send error already did, a `SysexTimeout` stops the screen service.

**Still needs a hardware check** (with Daniel's go, FL closed):
- A real identity reply arrives whole: 17 bytes starting `F0 7E 7F 06 02 00 20 6B`.
- Windows MIDI Services hands input buffers back through the callback, and re-queueing holds up over a long soak.
- The done flag is set when the call returns on today's stack (`sends[-1]` should show `done=True` with a sub-millisecond wait).
- A normal close prints nothing; after a power cycle, the expected codes are 6 and 65.
- The shared bucket file appears while the screen service and VJ engine run together, and the beat marker's timing is unaffected.

Files are in `E:\AI-Setup\.claude\worktrees\wf_efc891a3-dd0-1`:
- `arsenal\keylab\winmidi.py`
- `arsenal\keylab\governor.py`
- `arsenal\keylab\README.md`
- `tests\keylab_fake_winmm.py`
- `tests\test_keylab_winmidi.py`
- `tests\test_keylab_governor_port.py`

## Fix round 1: the adversarial verdict (verbatim)

**merge:** False

**must_fix:**
- A header the driver still owns is freed if the caller drops the MidiOut, and vj.run drops it. A header from a SysexTimeout (or from a failed unprepare) is parked only in the instance list `MidiOut._parked`. vj.run (arsenal/keylab/vj.py lines 2609-2614) sends daw_connect and, on any exception, runs `led_out = None` without calling close. That frees the header and the buffer while the driver may still write to them. [S:local] scratchpad/adv/test_adv_drop.py does exactly what vj.run does: a weakref to the parked header is dead after `led_out = None; gc.collect()`. Fix: when `_parked` is non-empty, move it into the module's `_KEPT_ALIVE`, either from a `MidiOut.__del__` or at the moment of parking. Then pin it with the drop test.
- The port-wide ceiling holds for the reserved slots, but not always for the calls that reach the driver, and the headline test checks the wrong one. `test_three_processes...` asserts `governor.log`, which holds slot times; the device sees the `midiOutLongMsg` times. When a sending process has busy pure-Python threads (the VJ engine's analysis threads are this kind of load), a send reached the driver up to 146-277 ms after its slot, and 13-14 packets per 100 ms reached the driver while the slots stayed at 12. [S:local] scratchpad/adv/gil_run.py: 3 processes with one of them GIL-busy gave 13 at the driver in 6 of 6 runs; 4 processes x 2 outputs gave 13-14; raising the guard to 6 ms did not help. Fix, either: (a) make it hold at the driver, by doing the window check and stamping the time under the bucket lock right before midiOutLongMsg; or (b) narrow the claim in the README 'Burst limit' row and the governor docstrings to 'slots: 12 per 100 ms; the driver can see one more per concurrently sending thread when a sender's Python is busy', and change the headline test to assert driver-call times (fake.long_msgs) with a GIL-busy child.

**summary:**

Verdict: do not merge yet. Two must-fixes remain. Each is small. Everything else I attacked held.

How I tested: I exported the branch (32c61f5f5) and its base (420b8d3a9) with git archive into scratch. Every run went through a guard plugin that refuses any load of winmm.dll, and it recorded 0 attempts. I did not touch the KeyLab, its ports, FL, 8793/8794/8796, the repo or the worktree. No governor bucket file was created in the main checkout.

**Suites.** [S:local]
- Branch: 521 passed, 4 skipped. Base: 491 passed, 4 skipped. The branch adds only new test files, so there is no regression.
- All 30 new tests fail or error against the old code.
- The headline 3-process test and the two-outputs test passed 5 times out of 5.

**Holds** [S:local, scratchpad/adv/test_adv_winmidi.py and test_adv_governor.py]:
- **Capture whole:** the real 17-byte identity reply, an all-zero SysEx, and a reply that exactly fills the buffer all arrive with every byte. A short reply after a long one carries no leftover tail.
- **Never runs dry:** 200 SysEx went through 24 buffers and through 4 buffers, including back-to-back with no wait for the re-queue: 0 dropped, no WinMM call from the callback. A MIM_LONGERROR buffer is re-queued too. Closing during a flood came out clean 60 times out of 60.
- **Timeout:** a timed-out send parks its header and buffer. The buffer is intact after gc while the MidiOut is alive. A second timeout does not unprepare the first header. The headers are reclaimed after the reset at close. With a dead driver, close reports reset=6, unprepare=65 and close=65, keeps the memory, and prints one stderr line.
- **Close:** the order is stop, reset, unprepare, close. With the device gone, the input close reports 6, 6, 65, 65.
- **Governor across processes:** 2, 3 and 4 processes, and 4 processes alongside 32 CPU-burning processes, all stayed at 12 per 100 ms, counted both as slots and as driver calls.
- **Crashed holder:** a holder killed while holding the lock let the next admit through in 0.4 ms with no fallback. Processes killed mid-flood, followed by a fresh flood, left no stale lock and no fallbacks.
- **One clock:** a child process's perf_counter always fell between the parent's readings, so every process shares one clock.

**Notes for Daniel (not blocking):**
1. **Latency under load.** The bucket file adds about 7 calls per packet that let other threads take over. On the fake driver, with a 0.3 ms driver round trip, one 12-packet frame took [S:local, scratchpad/adv/frame_lat.py]:

   | Load in the sending process | Before | After |
   |---|---|---|
   | None | 7.1 ms | 9.0 ms |
   | One thread at half load | 12.4 ms | 14.8 ms |
   | One fully busy thread | 45 ms | 96 ms |
   | Two fully busy threads | 89 ms | 380 ms |

   This makes the beat-marker hardware check a real one.
2. **Frozen holder.** A holder that stays frozen costs 2 s plus one window on every admit (3 admits took 6.3 s), not the "one window" in the report.
3. **MidiIn.close now raises by default.** In chordview, `listener.close(); out.close()` then skips the output's close. In screen.keys_loop the raise comes out of a `finally` inside its thread.
4. **Merge conflict.** Merging into master conflicts only in docs/PHYSICS.md, on its "Derived at" line; both doc files are rewritten by the pre-commit hook. At merge, take master's copies of docs/PHYSICS.md and docs/PRIOR_ART.md. This confirms the fixer's [I]: master's PHYSICS.md lists `_BOUNDED_READ_CAP`, which is not in core/comm/toolbox.py at 420b8d3a9 or on master.

**Still needs hardware:** whether Windows MIDI Services hands buffers back the same way, the 20 ms settle after start, and the timing of the done flag.

**hardware_check:**

With FL Studio CLOSED, open PowerShell in E:\AI-Setup\.claude\worktrees\wf_efc891a3-dd0-1 (or in E:\AI-Setup after the merge) and paste this one line. It takes about 5 seconds and sends 40 standard identity requests, 10 per second, through the governor:

py -c "import time;from arsenal.keylab import winmidi as W;ins=[W.MidiIn(prefer=p) for p in ('daw','midi')];[i.start() for i in ins];o=W.MidiOut(prefer='daw');[(o.send_sysex(bytes.fromhex('F07E7F0601F7')),time.sleep(0.1)) for _ in range(40)];time.sleep(0.5);[print(i.name,len([e for e in i.events if e[2]=='sysex']),[e[1].hex(' ') for e in i.events if e[2]=='sysex'][:1],'requeued',i.requeued,i.requeue_errors) for i in ins];print('last send',o.sends[-1]);print('close',[i.close() for i in ins],o.close())"

It passes if all of these hold:
(1) At least one input line shows 40, and its reply is 17 bytes starting 'f0 7e 7f 06 02 00 20 6b'. Whole replies prove the capture fix. Getting 40 replies through 24 buffers proves the re-queue works on Windows MIDI Services.
(2) On that line, 'requeued' equals the count and the error list is [].
(3) The 'last send' line shows done=True and a wait_s under 0.001.
(4) Every close code is 0, and no red 'winmidi:' line appears.
(5) The file state\arsenal\keylab\governor\keylab-88-mk3-daw.json now exists under E:\AI-Setup.

If the input lines show 0, the reply was lost (the device hang or the start race). Note which line and stop there; do not retry in a loop.

---

## Fix round 2: the fixer's report (verbatim; branch worktree-wf_efc891a3-dd0-7)

I fixed both must-fix items on branch **`worktree-wf_efc891a3-dd0-7`**. With one sender's Python busy, the fake driver sees 12 per 100 ms in 6 of 6 runs, down from 13–14. A header the driver still owns now survives a dropped `MidiOut`. The full KeyLab suite passes: 534 tests, 0 failures, 4 skipped. I never touched the KeyLab, its ports, FL or ports 8793/8794/8796; every test and probe ran against the fake winmm with private bucket directories.

One requirement is not met. The repo's pre-commit hook regenerates and stages `docs/PHYSICS.md` and `docs/PRIOR_ART.md` on every commit, so the branch diff changes both. I did not bypass the hook. To take master's versions at merge: `git checkout master -- docs/PHYSICS.md docs/PRIOR_ART.md`.

## Commits (on master's e660d6175)
- `b7e4e1122`: merge of `worktree-wf_efc891a3-dd0-1`, with master's PHYSICS.md and PRIOR_ART.md taken in the conflict.
- `527f20d23`: the winmidi header fix and the vj.run close.
- `3dc783b67`: the governor gate, the lock fix, the README and the tests.

## Fix 1: a header the driver still owns outlived nothing
- **What changed:** a header now goes into the module's `_KEPT_ALIVE` the moment it is parked (`MidiOut._park`), and comes out only after the driver hands it back and it is unprepared, so nothing leaks.
- **Also fixed:**
  - A Ctrl-C (or a governor error) between the prepare and the done flag used to drop the header. Now a header the driver took is parked, and one it never took is unprepared (`_give_back`).
  - `vj.run` now closes the output when the connect send fails, so the port handle is returned too.
- **Evidence [S:local]:**
  - The drop test reported the header's weakref **dead** before the fix and **alive** after.
  - The same holds after a failed unprepare.
  - The interrupt test: 0 parked before, 1 after.
  - The vj.run test: the output stayed open before, and is closed after.
  - The tests are in `tests/test_keylab_winmidi.py` (4 new) and `tests/test_keylab_vj.py::test_run_closes_the_daw_output_when_the_connect_send_fails`.

## Fix 2: the ceiling now holds at the driver (option a)
**How the governor works now.** A send meets it twice:
1. `admit()` reserves the next free slot, first come, first served, as before.
2. `gate(call)` wraps the `midiOutLongMsg` call itself. The call is registered as "in flight" just before it starts and gets its end time just after it returns. A new call may start only while fewer than 12 calls are in flight or ended within the last 100 ms.

No 100 ms window can then hold more than 12 calls, however late each one ran: the last one registered saw all the others. The lock is never held across the driver call. A Windows MIDI Services send can wait 1 s, and the older KS write has no limit [S: hang guide, Windows MIDI Services lane, section 2]. An entry left by a dead process stops counting after 5 s.

**A second defect, found while measuring.** Holding the bucket lock used to give up the GIL (the file read/write and `msvcrt.locking`). A busy process therefore held every process's sends for a **median 62 ms per send, max 171 ms**, and managed 7–8 sends per second. The bucket is now memory-mapped and locked with `LockFileEx` through a ctypes call that keeps the GIL and never blocks (x64). Now the median is 0.037 ms and the max 0.22 ms [S:local]. The bucket file grew from 4 KB to 16 KB to hold the in-flight entries.

**Cross-process test.** `test_three_processes_on_one_port_never_exceed_the_ceiling_together_at_the_driver` runs 3 real processes against one port. One has 2 spinning threads. It checks the merged times at which each process's fake driver received its calls: ≤12 per 100 ms. The slots must still reach exactly 12, so the port still gets its full budget.
- Before: 13 (`assert 13 <= 12` failed). After: it passed in 5 of 5 repeats.
- Fake-clock tests cover late sends, a call still in flight, a dead process's entry, the in-process fallback, and a full bucket at the 128 limit.
- A lock-hold test with 2 spinning threads requires a median under 5 ms.

**Adversarial rerun [S:local], 3 repetitions each:**

| | Peak calls per 100 ms at the driver | Port rate under load |
|---|---|---|
| Before | 13–14 | 24–35 per second |
| After | 12 | ~115 per second |

The scripts are in `<scratch>\r2\` (`gil_run2.py`, `hold_probe.py`, `hold_probe2.py`).

The README burst row, the file list, and the governor and winmidi docstrings now say this.

## Still needs a hardware check
- **Rate on the real driver:** the fake driver's call never gives up the GIL, but the real ctypes call does. In a busy process, the in-flight entry stays counted until the GIL comes back, so expect a somewhat lower port rate with the VJ engine busy [I]. Measure it once Daniel allows port use.
- **The device side:** the ceiling at the call equals the ceiling at the device only if Windows MIDI Services returns after the device write [S: Microsoft's code] [I for the device]. The 12-per-100-ms figure itself is still for probe P24.
- **vj.run's new close:** `midiOutReset` does nothing for output on Windows MIDI Services today [S: hang guide]. In legacy mode it would send about 2,064 note-offs. Every close already does this; the new path only adds one more close.

Nothing was downloaded or installed. The working tree still shows hook output I did not commit: line-ending-only changes to `docs/MODULE_INDEX.md` and `docs/PORTS.md`, and the post-commit hook's `state/authorship/seats.jsonl` entry.

Changed files:
- `E:\AI-Setup\.claude\worktrees\wf_efc891a3-dd0-7\arsenal\keylab\governor.py`
- `E:\AI-Setup\.claude\worktrees\wf_efc891a3-dd0-7\arsenal\keylab\winmidi.py`
- `E:\AI-Setup\.claude\worktrees\wf_efc891a3-dd0-7\arsenal\keylab\vj.py`
- `E:\AI-Setup\.claude\worktrees\wf_efc891a3-dd0-7\arsenal\keylab\README.md`
- `E:\AI-Setup\.claude\worktrees\wf_efc891a3-dd0-7\tests\test_keylab_governor_port.py`
- `E:\AI-Setup\.claude\worktrees\wf_efc891a3-dd0-7\tests\test_keylab_winmidi.py`
- `E:\AI-Setup\.claude\worktrees\wf_efc891a3-dd0-7\tests\test_keylab_vj.py`

## Fix round 2: the adversarial verdict (verbatim)

**merge:** True

**must_fix:**
(none)

**summary:**

Verdict: merge. Every fix on worktree-wf_efc891a3-dd0-7 (3dc783b67) held up when I tried to break it. I exported the branch with git archive into scratch and never opened the KeyLab ports. I used only the fake winmm or stub driver calls, with private bucket directories.

What I tried, and what happened [S:local]:

1. **The identity reply comes back whole.** The 17-byte reply with 00 bytes was captured exactly. It also came back exact when it reused a buffer that had held a 42-byte message, when it filled a 17-byte buffer exactly, and when its body was all 00.

2. **A listener does not run dry.** 200 replies with 2, 4 or 24 buffers, paced: none dropped. 200 back to back into 24 buffers: none dropped. The same burst with 2 threads keeping Python busy: none dropped. Every run got 200 of 200 in order, with no re-queue errors and no WinMM call from the callback thread.

3. **A done-flag timeout is reported and the header is kept.**
   - The timeout raises SysexTimeout after about 50 ms. The record shows done=False and the header is parked.
   - I dropped the MidiOut, ran gc and made 40,000 allocations. The driver's raw pointer still read the exact 15 bytes and the header. Round-1 code fails this same test ("freed and reused").
   - A real Ctrl-C during the wait (_thread.interrupt_main) parks the header.
   - An interrupt before the driver call unprepares the header.
   - An interrupt after the call, before its code is stored, gets the unprepare refused, so the header is parked.

4. **Close order and result codes.**
   - MidiOut closes in the order reset, unprepare, close, with every code returned. strict raises only after every step has been tried.
   - When the reset does not hand a header back, close reports MIDIERR_STILLPLAYING and keeps the header. No unprepare is tried on it.
   - MidiIn closes in the order stop, reset, unprepare, close, even while the device keeps sending. No buffer is queued again after the stop.

5. **The ceiling holds across processes.** I ran 36 runs: 6 scenarios with 2 to 4 processes, 1 to 3 sender threads each, 0 to 2 busy threads, and driver calls of 0 to 140 ms that give up the GIL, plus real MidiOuts on the fake. The peak at the driver was 12 per 100 ms in every run. Round-1 code on the same harness peaked at 13 to 14 in 6 of 6 runs, so the harness does catch the old defect.

6. **Crashed or frozen holders.**
   - A process killed while holding the lock: the next send took 0.3 ms with no fallbacks. The lock is released, nothing is left stale.
   - A process that called os._exit while holding it: 0.2 ms.
   - A process killed with 1 call in flight: no stall. With 12 in flight: a 5.0 s stall, then normal, as designed.
   - 20 random kills in the middle of a flood: the worst send took 101 ms, there were no fallbacks, and the bucket was valid each time.
   - A holder frozen for 5 s: no deadlock. The slowest send took 4.2 s through the fallback, the peak was 9 per 100 ms, and sends were normal after it let go.

7. **No regression.** The full keylab suite on the exported branch: 534 collected, 530 passed, 4 skipped. The new tests passed 3 times in a row.

Not blocking, but worth a follow-up:

- **(a) The gate is not first come, first served.** Take a sender whose Python is busy, sending one message every 250 ms next to an idle process flooding at the ceiling. Behind the gate its slowest send took 155 ms in one run and 1.96 s in another. With the slot alone (no gate) it never took more than 110 to 141 ms. A busy sender flooding the port with the gate shows the same tail: up to 1.27 s. That busy-and-idle pair goes against the README's one-LED-writer rule. The setup Daniel actually runs is a busy VJ engine flooding plus an idle screen service at 4 per second. There the screen service's slowest send took 70 to 77 ms, which is fine. The fix is first-come order at the gate, or the planned hub service as the only writer.
- **(b) The done timeout includes the gate wait.** `send_sysex` starts its done timeout before the gate, so a long gate wait uses up the budget. On an asynchronous driver that could raise a false timeout. Windows MIDI Services is not affected, because the flag is set when the call returns.
- **(c) A failed input close can skip the output close.** `MidiIn.close()` is strict by default, so in chordview `listener.close(); out.close()` skips `out.close()` when the input close fails, for example after a power cycle. On master that close never raised.
- **(d) A writer killed in the middle of a write can leave valid JSON.** When I forced a half-write, the result parsed and the in-flight list and end times were dropped, so the bucket was not reset. For one window that could let through more than 12 [I].
- **(e) Ctrl-C right after the lock is taken leaves it held** [I, not reproduced]. If it lands between LockFileEx returning and the `try:`, the lock stays held by that handle until close(). Other processes then wait 2 s per send through the fallback.
- **(f) Merge conflict.** The branch conflicts with master in docs/PHYSICS.md, which the commit hook regenerates; master's 54767d92d also changed it. Take master's docs/PHYSICS.md and docs/PRIOR_ART.md, as the fixer said.

The scripts are in `<scratch>\adv\` (`run_flood.py`, `child_flood.py`, `crash_tests.py`, `starve_probe.py`, `fairness.py`) and in `scratchpad\v2full\tests\test_adv_verify_winmidi.py`. Nothing was committed, downloaded or installed. FL and ports 8793/8794/8796 were not touched.

**hardware_check:**

FL can stay open. This sends only the Device Inquiry (F0 7E 7F 06 01 F7, 30 times over about 7 s): no DAW connect, no pads, no screen. It is the same message that was answered alongside FL on 10-27.

In PowerShell:

```
cd E:\AI-Setup\.claude\worktrees\wf_efc891a3-dd0-7
py -c "import time; from arsenal.keylab import winmidi as W; i=W.MidiIn(prefer='daw'); i.start(); o=W.MidiOut(prefer='daw'); q=bytes.fromhex('F07E7F0601F7'); [(o.send_sysex(q), time.sleep(0.2)) for _ in range(30)]; time.sleep(0.5); r=[d for t,d,k in i.events if k=='sysex' and d[:5]==bytes.fromhex('F07E7F0602')]; print(len(r), 'replies of 30 |', len(r[0]) if r else 0, 'bytes |', r[0].hex(' ') if r else '-'); print('requeued', i.requeued, '| requeue errors', i.requeue_errors, '| parked', o.parked, '| all done', all(s['done'] for s in o.sends), '| slowest call ms', round(max(s['wait_s'] for s in o.sends)*1e3, 2)); print('out close', o.close()); print('in close', i.close(strict=False))"
```

It passes if:
1. It prints "30 replies of 30 | 17 bytes | f0 7e 7f 06 02 00 20 6b ..." and the bytes after 00 20 6b are not all zeros. That means the capture fix works.
2. requeued is 30 or more (more than the 24 buffers), with requeue errors [], parked 0 and all done True. That means the long-lived listener works and no header was kept back.
3. Both close lines show every code as 0.
4. `Get-Content E:\AI-Setup\state\arsenal\keylab\governor\keylab-88-mk3-daw.json` shows "admits": 30. That means the port-wide governor counted the real port.

"slowest call ms" records how long the real Windows MIDI Services call takes, for the rate question the fixer left open. If there are 0 replies, the keyboard may be in the hang: run the recovery ladder from the hang guide before power-cycling.
