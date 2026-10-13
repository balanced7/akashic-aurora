# Hardware, firmware and signals: the house's introductory reverse-engineering playbook

Status: current
Class: report
Arc: reverse-engineering-arsenal

- **Reverse-engineering arsenal, 2026-10-13.** One of eight topic reports written the night Daniel asked
  the house to "know how to reverse engineer anything". His words, verbatim: *"Please add it to our
  repository of knowledge, I want us to know how to reverse engineer anything, I would love to make an
  archero style game but actually give a viable upgrade path and make releases of new weapons and effects
  for free. Thats for a future time but I want us to have the whole reverse engineering arsenal."*
- **Topic (light, introductory):** the MIDI and USB devices we own (MIDI monitors, USB descriptors,
  SysEx), logic analysers and sigrok, firmware images (binwalk, unblob) inside a VM, software-defined
  radio basics, and the legal limits (radio rules, anti-circumvention).
- **Author:** Claude (the Vandor seat), as a research subagent. Sources were read on 2026-10-13.
- **What was touched on this machine (all read-only):** a Plug-and-Play device listing, device
  properties, one headless run of Microsoft's USBView (already installed with the Windows SDK) saving a
  text report to the session scratchpad, a read of the Arturia KeyLab mk3 FL Studio script folder and
  the MIDI Control Center resource JSON, file sizes and hashes of two KeyLab firmware files in Downloads,
  and three small Python demos that only use data we generated. **Nothing was installed, no driver was
  changed, no MIDI or SysEx message was sent to any instrument, no firmware was opened or executed, no
  git command was run.** FL Studio was running at the time (HW-E9), which is one more reason nothing was
  sent to the KeyLab.
- **Discipline credit:** the evidence discipline below is adopted from the REA skill by morluto
  (github.com/morluto/rea, `.agents/skills/reverse-engineer-anything/SKILL.md`). We take its habits, not
  its server machinery, and describe them in our own words.
- **Not legal advice.** Every legal note here is orientation for a non-lawyer, and the jurisdiction the
  house acts from is not recorded in this report (it is an open unknown, see section 9).

---

## 0. The one-page version

1. **Hardware reverse engineering is mostly reading what the device already tells you.** A USB device
   hands the computer a full self-description the moment it is plugged in. A MIDI instrument answers a
   standard "who are you?" question. Vendors ship editor files and DAW scripts in readable form. Read
   those first; sniff traffic second; open firmware last, and only in a disposable VM.
2. **We already did a real one tonight.** The KeyLab 88 mk3's USB self-description (HW-E3) shows a MIDI
   function with **two virtual cables each way** (the "MIDI" and "DAW" ports you see in FL Studio) and a
   hidden **"Firmware Updater" interface** that speaks the USB DFU 1.1 firmware-upgrade protocol.
   Microsoft's own viewer mislabels that updater block as a "HID descriptor"; re-reading the raw bytes
   against the DFU spec fixes it (section 5.1). Lesson: a tool's label is an inference, not an
   observation.
3. **Two vendor files disagree** about how the KeyLab identifies itself over MIDI (FL Studio's script
   versus Arturia's editor JSON). We record both and do not pick. One harmless, standard Identity
   Request, sent when FL is closed and Daniel says go, settles it (section 5.2).
4. **The firmware file tells us things without being opened:** the device's USB revision number
   `0x1500` lines up with the downloaded firmware file `1_5_0`; the `.confirm` file's "checksum" is a
   plain MD5 of the download (integrity, not authenticity). Arturia's editor JSON also carries a field
   named `productKey` for the updater; we do not reproduce it, and that is where this playbook stops
   (section 5.3).
5. **Tools, in one line each:** a MIDI monitor (Windows MIDI Services console and monitor, MIDI-OX,
   ReceiveMIDI) for messages; USBView or UsbTreeView for descriptors; USBPcap+Wireshark (Windows) or
   usbmon (Linux) for USB traffic; sigrok/PulseView with a logic analyser for wires; binwalk 3 and unblob
   for firmware **inside a Linux VM**; an RTL-SDR with SDR++/GNU Radio/URH/rtl_433/inspectrum for radio
   (receive only). None of the capture tools are installed here today, and the house owns no logic
   analyser or SDR that this PC has ever seen (HW-E8, HW-E15).
6. **Host safety is the binding constraint.** This machine runs without Defender or updates by the
   owner's choice. So untrusted firmware and captures are analysed only in a disposable Linux VM with
   networking off and no shared folders. Not the default WSL distro (it mounts C: and E: read-write and
   can launch Windows programs), and not Docker Desktop (it hosts `akashic-redis`, the house substrate).
   Neither a VM nor Windows Sandbox is enabled today; enabling one is Daniel's call.
7. **Legal shape, in one breath:** understanding and interoperating with things we own is broadly
   protected (Sega v. Accolade; Sony v. Connectix; EU Software Directive arts. 5(3), 6 and 8; UK CDPA
   s.50B; Canada Copyright Act s.41.12). Breaking a technical lock is a separate question
   (US DMCA s.1201 and its exemptions). Radio is its own world: receive your own devices freely, never
   intercept others' private traffic, and never transmit without a licence or outside a device's
   certification.

---

## 1. The discipline we borrow (credit: morluto/rea)

REA is an MCP server plus a skill for reverse-engineering shipped artifacts. Its tooling is
Linux-centred; what transfers to us is the **habit set**, restated here for hardware:

| Habit | What it means on a hardware bench |
|---|---|
| **Route the target first** | Decide what the artifact *is* (a live USB device, a MIDI port, a firmware file, a wire, a radio signal) and pick the first tool from that. Section 10 is the routing table. |
| **Observations vs inferences vs unknowns, with evidence IDs** | Every finding below carries an `HW-E` number pointing at the exact command, file or spec page. "USBView printed X" is an observation. "So the device does Y" is an inference. |
| **Summary first; never repeat an identical analysis without a changed input** | One USBView dump was taken and reused for every USB finding. A second dump only makes sense after something changes (a firmware update, a different device). |
| **Inspect resources and configuration alongside code; never infer behaviour from names** | The KeyLab's FL script and editor JSON were read before any thought of traffic capture. A field *named* `productKey` tells us its name, not its function. |
| **A finding ledger with confidence, search boundary and unknowns; revisit the checklist at the end** | Section 9. |
| **Separate observed behaviour from design choices when rebuilding** | If we ever build a KeyLab bridge, "the DAW port expects this handshake" (observed in vendor code) is kept apart from "we chose to show game state on the screen" (our design). |
| **Never choose an example on the user's behalf** | The brief named "devices we own", so the examples are the KeyLab 88 mk3 and the Scarlett 2i2 4th Gen that are plugged in. The firmware files in Downloads are inventoried, not analysed: whether to analyse them is Daniel's choice. |
| **Bounded negative searches stay bounded** | "No logic analyser or SDR found" means: none among the 1,349 devices in this PC's Plug-and-Play store, for the ID list in HW-E15. It does not mean the house owns none. |

---

## 2. Concepts, plainly (with hardware analogies)

### 2.1 The layer cake

Every hardware question sits on one layer of this stack, and each tool sees only some layers:

```
meaning        "Daniel pressed middle C fairly hard"           <- documentation, vendor files, your judgement
messages       Note On, ch 1, note 60, velocity 100            <- MIDI monitor, sigrok 'midi' decoder
bytes          90 3C 64                                        <- MIDI monitor (raw view), USB capture payload
framing        UART 8N1 at 31,250 baud | USB-MIDI 4-byte packet <- logic analyser + decoder | USB capture
electricity    a current loop on a DIN cable | USB D+/D- pair  <- logic analyser / oscilloscope
radio          a modulated carrier at some frequency           <- SDR
```

Analogy: this is the same idea as a CPU's stack of abstractions, from transistors to ISA to programs. A
logic analyser is a die photo of *time* on one wire. A MIDI monitor is a disassembler for the message
stream. Most mistakes come from asking a tool about a layer it cannot see.

### 2.2 MIDI 1.0 in ten facts

1. **Status bytes and data bytes.** A message starts with a status byte (top bit 1) and is followed by
   data bytes (top bit 0, so values 0 to 127). Analogy: an opcode followed by operands.
   (midi.org, *Summary of MIDI 1.0 Messages*.)
2. **Channel messages** carry the channel in the low four bits: `8n` Note Off, `9n` Note On, `An` Poly
   Pressure, `Bn` Control Change, `Cn` Program Change, `Dn` Channel Pressure, `En` Pitch Bend.
3. **Real-time bytes** (`F8` clock, `FA` start, `FC` stop, `FE` active sensing, `FF` reset) are single
   bytes that may appear anywhere in the stream, even inside another message. Analogy: interrupts.
4. **Running status**: a sender may omit a repeated status byte. A parser that forgets this misreads
   long runs of notes. (This is a widely documented MIDI 1.0 rule; the midi.org summary page we fetched
   does not spell it out.)
5. **System Exclusive (SysEx)** is the vendor's private channel: `F0`, a manufacturer ID, any number of
   7-bit data bytes, then `F7`. Analogy: model-specific registers. Every vendor implements them
   differently. Some (Roland, for one) publish full maps; many publish nothing.
6. **Manufacturer IDs** are 1 byte or 3 bytes (`00 xx xx`), assigned by the MIDI Association and AMEI.
   From the official table: Arturia `00 20 6B`, Focusrite/Novation `00 20 29`, Kawai `40`, Roland `41`,
   Korg `42`, Yamaha `43`.
7. **Universal SysEx** uses two reserved IDs: `7E` (non-real-time) and `7F` (real-time). The one that
   matters for us is the **Identity Request** `F0 7E <device> 06 01 F7`. A device that supports it replies
   `F0 7E <device> 06 02 <manufacturer ID> <family: 2 bytes> <member: 2 bytes> <software revision: 4 bytes>
   F7`. Analogy: the CPUID instruction. Roland's TB-3 MIDI Implementation document (2014) shows both
   messages byte by byte (HW-E14).
8. **Seven-bit packing.** Because data bytes cannot use the top bit, vendors repack 8-bit data. Roland
   splits a byte into two nibbles (`ABh` travels as `0Ah 0Bh`). Others send one "high bits" byte before
   every seven data bytes. Analogy: line coding such as 8b/10b in PCIe, where you spend bits to keep a
   property. Expect to find a packing scheme in any bulk dump.
9. **Checksums.** Roland's data-set messages end with a checksum byte; many vendors do something
   similar. If you change one parameter and two bytes change, one of them is often a checksum.
10. **The wire.** Classic 5-pin DIN MIDI is a serial line at **31,250 baud, 8 data bits, no parity, 1 stop
    bit, least significant bit first** (sigrok's MIDI decoder states this). A 3-byte note takes about
    0.96 ms on the cable (HW-E10).

**Designed-in discovery beats reverse engineering.** MIDI 2.0 adds MIDI-CI (Capability Inquiry) and
Property Exchange, where a device describes itself on request. Where a device supports them, ask
before you guess.

**SysEx IDs for our own experiments.** Under the MIDI Association's policy of 2025-10-15, ID `7D` is
for non-commercial, non-public work (schools, research, personal projects) and must not ship in a
public product. ID `7C` is free for non-commercial public releases but only for MIDI 2.0 discovery
mechanisms, not custom messages. A paid ID is a one-time fee. So: a house experiment uses `7D`; anything
we release needs a proper answer first.

**SysEx in the browser.** Web MIDI treats SysEx as a separate, stronger permission
(`requestMIDIAccess({sysex: true})`), because SysEx can rewrite device settings or firmware. The
house's piano page asks for `sysex: false` today (`arsenal/web/piano.js`, per the piano alpha census),
so it cannot see or send SysEx.

### 2.3 USB in ten facts

1. **Descriptors are the device's spec sheet.** On plug-in the host asks the device for its
   descriptors: one **device** descriptor (18 bytes: USB version, class, vendor ID, product ID, release
   number `bcdDevice`, string indexes), one or more **configurations**, each holding **interfaces**,
   each holding **endpoints**, plus **string** descriptors (human-readable names) and
   **class-specific** descriptors. (Craig Peacock, *USB in a NutShell*, beyondlogic.org.)
2. **Class codes say which "driver family" fits.** `bDeviceClass = 0x00` means "look at each
   interface". Interfaces then say Audio (`0x01`), HID (`0x03`), Application-Specific (`0xFE`, which
   includes DFU firmware upgrade), Vendor-Specific (`0xFF`), and so on. Analogy: a chiplet package. One
   plug, several functions, each with its own driver.
3. **USB-MIDI** is a subclass of Audio: an AudioControl interface (subclass `0x01`) plus a
   **MIDIStreaming** interface (subclass `0x03`). Inside, "jacks" describe where MIDI enters and leaves.
   **Embedded** jacks are the USB side; **External** jacks are physical DIN ports (or the vendor's
   description of them). (USB-IF, *Device Class Definition for MIDI Devices 1.0*, 1999-11-01, by Mike
   Kent of Roland and Geert Knapen of Philips; HW-E12.)
4. **USB-MIDI event packets are 4 bytes:** a header byte holding the **cable number** (high nibble, 0 to
   15) and a **Code Index Number** (low nibble), then up to three MIDI bytes padded with zeros. The CIN
   says what kind of bytes follow: `0x8`-`0xE` mirror channel messages; `0x4` means SysEx starts or
   continues; `0x5`/`0x6`/`0x7` mean SysEx ends with 1, 2 or 3 bytes; `0xF` is a single raw byte. So a
   Note On on cable 0 travels as `09 90 3C 64`. Cable numbers are how one USB pipe carries several
   "ports". Analogy: virtual channels on one link.
5. **Transfers** come in four kinds: control (setup and descriptors), bulk (USB-MIDI uses bulk),
   interrupt (HID input, status notifications) and isochronous (audio streams).
6. **Software sniffers see requests, not wire packets.** USBPcap and Linux usbmon capture the requests
   (URBs) the host's USB stack handles. They do not see the bus's own handshakes. The Wireshark wiki
   says this outright. For protocol work that is almost always enough.
7. **USB full speed is 12 Mbit/s.** A cheap 24 MHz logic analyser cannot follow it (section 2.4), so
   USB is a software-capture job.
8. **Composite devices on Windows** get a parent node, and normally per-interface child nodes
   (`...&MI_00`, `...&MI_01`). A vendor driver can claim the whole device instead, as Arturia's does for
   the KeyLab (HW-E2). Then Device Manager shows no interface children, and you need a descriptor viewer
   to see the interfaces.
9. **HID report descriptors** (USB-IF HID 1.11 plus the HID Usage Tables 1.7) describe every button and
   axis a game controller has. Reading one is how a game learns a controller's layout lawfully. This is
   relevant to the future game.
10. **DFU (Device Firmware Upgrade 1.1)** is the standard firmware-update protocol. A *run-time*
    interface is class `0xFE`, subclass `0x01`, protocol `0x01`. Protocol `0x02` is "DFU mode". A
    9-byte functional descriptor of type `0x21` lists what the device allows: download, upload,
    detach behaviour, transfer size and DFU version (HW-E13). **Type `0x21` is also the HID
    descriptor's type code.** That collision is the trap in section 5.1.

### 2.4 Logic analysers in eight facts

1. A logic analyser samples wires and records only "above or below the threshold" at each tick.
   Analogy: a 1-bit ADC per pin, with the sample rate as the shutter speed.
2. **Sample fast enough:** Saleae's guidance is at least 4x the signal bandwidth for digital and 10x
   for analogue. MIDI DIN at 31.25 kbaud is trivial (1 MHz gives 32 samples per bit; HW-E10). USB full
   speed at 12 Mbit/s needs about 48 MHz, which is beyond the common 24 MHz FX2-based analysers.
3. **Protocol decoders stack.** In sigrok, the `uart` decoder turns edges into bytes. The `midi`
   decoder stacks on top and turns bytes into notes. The USB chain is `usb_signalling` then
   `usb_packet` then `usb_request`. The sigrok wiki lists 131 decoders, including I2C, SPI, CAN,
   1-Wire, JTAG, SWD, SPI flash, IR NEC and on-off keying.
4. **sigrok** (GPL-3.0-or-later) is the free suite: libsigrok, libsigrokdecode, `sigrok-cli`, the
   PulseView GUI and SmuView. Latest releases: libsigrok 0.5.2, libsigrokdecode 0.5.3, sigrok-cli 0.7.2,
   PulseView 0.4.2, with Windows release and nightly installers. Typical commands:
   `sigrok-cli --scan`, `sigrok-cli --driver fx2lafw --config samplerate=1m --time 3s -o cap.sr`, and
   `sigrok-cli -i cap.sr -P uart:baudrate=31250,midi -A midi`.
5. **fx2lafw** (GPL-2.0-or-later) is open firmware for Cypress FX2 chips. It turns many cheap 8-channel,
   24 MHz boards into sigrok devices. The sigrok wiki warns that some "clones" copy another maker's USB
   IDs and ship that maker's software illegally. Buy a board sold under its own name, and use sigrok
   with it, not someone else's software.
6. **Saleae Logic 2** is proprietary software for Saleae's own analysers (Windows, macOS, Linux). It has
   a gRPC automation API with a Python wrapper, and Saleae now advertises MCP-driven workflows. The
   hardware is the cost. We did not verify its demo-device or offline behaviour.
7. **Voltage and ground.** Know the logic level (1.8, 3.3 or 5 V) and the analyser's input tolerance
   before clipping on. Connect ground first, to the target's ground. A 5-pin MIDI cable is a current
   loop, not a logic-level line, so probe a logic-level point (an opto-isolator's output on a board you
   own, or a MIDI-to-TTL breakout) rather than the DIN pins blindly.
8. **On a board you own,** the usual first finds are a **UART console** (TX, RX, GND, often 115200
   baud), an **SPI flash chip** (readable with `flashrom`, GPL, after a backup and with the right
   voltage), and **debug ports** (JTAG, SWD). Reading your own board's console is ordinary engineering.
   Defeating a chip's read-out protection is circumvention territory (section 7) and is out of scope.

### 2.5 Firmware images in eight facts

1. **A firmware image is nested boxes.** A header, then compressed blobs, file systems (squashfs, UBI,
   ext), bootloaders, sometimes encrypted or signed sections, and padding. Analogy: a GPU BIOS, which
   holds tables, a compressed payload and a signature.
2. **Signatures (magic bytes)** mark known formats: gzip starts `1F 8B 08`, ELF executables start
   `7F 45 4C 46`, U-Boot images `27 05 19 56`, little-endian squashfs `hsqs`. binwalk is a fast
   signature scanner with extractors attached.
3. **Entropy** measures how random the bytes look, from 0 to 8 bits per byte. Padding is near 0, text and
   code sit around 4 to 6, and **compressed and encrypted data both sit near 8**. In our toy image the
   gzip stream measured 7.99 and the random block 7.98 (HW-E11). **Entropy alone cannot tell compressed
   from encrypted.** A recognised header can. Analogy: on a die shot, SRAM looks uniform while logic
   looks random; but two different random-looking blocks look the same.
4. **binwalk 3** (MIT, rewritten in Rust; originally by Craig Heffner, now ReFirmLabs). Main flags:
   `-e` extract, `-M` recurse into extracted files ("matryoshka"), `-E` entropy graph (`-p` saves it as
   a PNG), `-a` search all offsets, `-y`/`-x` include or exclude signatures, `-d` output directory,
   `-l` JSON log, `-L` list signatures. Install via Docker, Cargo or source.
5. **unblob** (MIT, by ONEKEY) finds where each chunk *starts and ends*, extracts recursively, reports
   unknown chunks instead of skipping them, and writes a metadata report with entropy. It runs on Linux
   (pip, Nix, Kali package) or via its Docker image. It needs external extractors (7-Zip, unar,
   e2fsprogs, lz4, zstd, and so on).
6. **Heavier tools** emulate or score: **EMBA** (GPL-3.0) does extraction, static checks, SBOM and
   *emulation-based* dynamic analysis, so it **runs untrusted firmware code** and needs a dedicated VM.
   **FACT** (GPL-3.0, Fraunhofer FKIE) unpacks, runs analysis plugins and **compares firmware
   versions**. It is a server-sized tool; the recommended spec is 16 cores and 64 GB of RAM.
7. **Extractors are attack surface.** CVE-2022-4510 (published 2023-01-25, CNA ONEKEY): a crafted PFS
   file made binwalk 2.1.2b to 2.3.3 write outside its extraction folder, enabling code execution
   through binwalk's plugin directory. The tool you point at hostile firmware can itself be the way
   in. That is why this work happens in a VM.
8. **REA's firmware route** (`inspect_firmware_regions`, `extract_firmware`) wraps caller-supplied
   binwalk 3.1.x and unblob 26.6.x on Linux x64. It enforces size, time and memory limits, never
   overwrites a destination, and records SHA-256 hashes and lineage for each extracted file. It states
   that it does no emulation, mounting or execution. That makes it a good fit *inside* our future
   analysis VM.

### 2.6 Software-defined radio in eight facts

1. **An SDR digitises a slice of spectrum and lets software do the rest.** Analogy: fixed-function
   graphics hardware giving way to programmable shaders. The tuner moves a slice to 0 Hz; the ADC samples
   it; demodulation is code.
2. **IQ samples** are pairs (in-phase, quadrature) stored as complex numbers, so the software knows
   which way the signal rotates. With complex samples, **a sample rate of N samples/s shows N Hz of
   spectrum**, centred on the tuned frequency. (Marc Lichtman, *PySDR*, CC BY-NC-SA 4.0.)
3. **The DC spike** at the centre of the display is usually the receiver's own oscillator leaking
   through. Tune slightly off to one side.
4. **RTL-SDR**: about USD 30, a TV-tuner dongle (RTL2832U) turned into a receiver by the work of Antti
   Palosaari, Eric Fry and Osmocom (Steve Markgraf). Covers roughly 24 to 1766 MHz with common tuners,
   about 2.56 MS/s stable, 8-bit samples. **Receive only.** On Windows it needs the WinUSB driver
   installed with Zadig, on the *right* device (section 6).
5. **Software:** **SDR++** (GPL-3.0, Alexandre Rouma) to look and record; **GNU Radio** (GPL-3.0) to
   build processing flowgraphs; **radioconda** (Ryan Volz's distribution) to install GNU Radio, gqrx and
   inspectrum on Windows; **inspectrum** (GPL-3.0, Mike Walters) to measure symbols in a recording;
   **Universal Radio Hacker** (GPL-3.0, Johannes Pohl and Andreas Noack, USENIX WOOT 2018; repository
   archived 2026-03-29) to demodulate and infer protocol fields; **rtl_433** (GPL-2.0, Benjamin Larsson)
   which decodes 386 kinds of ISM-band sensors (weather stations, doorbells, tyre-pressure sensors) and
   is receive-only.
6. **Typical simple signals** are on-off keying (OOK, the carrier on or off), ASK and FSK. Most cheap
   sensors and remotes use them.
7. **Recordings need metadata.** **SigMF** (CC BY-SA, from the DARPA Brussels Hackfest 2017) pairs a
   `.sigmf-data` sample file with a `.sigmf-meta` JSON file stating the data type (for example
   `cf32_le`), sample rate and centre frequency. A raw `.cu8` with no record of its rate is half a
   finding.
8. **The lawful primary source for any radio product sold in the US** is its FCC ID record: frequency
   range, power, test reports, and often internal photos and manuals. The FCC's equipment-authorisation
   search lives at fcc.gov/oet/ea/fccid. Our automated fetch was refused (HTTP 403), so this is cited
   from general knowledge, not read tonight.

---

## 3. The method, step by step

### 3.0 The general hardware loop (every playbook below is a specialisation)

1. **Write the question down** and what evidence would answer it ("which port does the KeyLab's screen
   listen on?" needs: the port list, the message format, one observed effect).
2. **Inventory without touching:** Plug-and-Play listing, device properties, installed vendor software,
   files already on disk. Hash anything that might change.
3. **Read what ships in readable form:** manual and MIDI Implementation Chart, vendor DAW scripts,
   editor resource files, Linux drivers for the same device family, public interoperability projects.
   *This step alone answers most questions.*
4. **Ask the device the standard questions:** USB descriptors (passive) and the MIDI Identity Request
   (one harmless query). MIDI-CI if it is a MIDI 2.0 device.
5. **Observe passively:** a MIDI monitor while you press things; a USB capture only if needed.
6. **Change one thing at a time and diff:** move one knob in the vendor editor, capture, compare.
   Expect checksums and 7-bit packing.
7. **Corroborate:** two independent evidence types agree, or the finding stays an inference.
8. **Write the ledger** (observations, inferences, unknowns, search boundaries) and the checklist
   verdict. Keep raw captures out of the repo.

### 3.1 Playbook P1: a MIDI device we own

1. Inventory the ports: Device Manager or `Get-PnpDevice`. On this PC, Windows MIDI Services runs and
   presents the KeyLab as "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW" (HW-E1).
2. Read the vendor files (P1 is mostly this step for the KeyLab; see 5.2).
3. Passive monitor: Windows MIDI Services' `midi endpoint monitor` (it can also capture to a file with
   annotations) or its MIDI Monitor app; MIDI-OX; or `receivemidi dev "<name>" ts dump`. Endpoints in
   Windows MIDI Services are multi-client, so monitoring does not steal the port from FL Studio.
4. Identity Request: send `F0 7E 7F 06 01 F7` (device ID `7F` addresses all devices) and record the
   reply bytes. **Only with Daniel's go and when no performance or session is running.**
5. To learn a vendor editor's SysEx: monitor while changing *one* setting in the editor; diff; repeat.
   Seeing the editor's outgoing bytes may need a USB capture (P2). Our inference is that an endpoint
   monitor shows what *arrives* at an endpoint, not what another app sends to the device.
6. Never send a SysEx write you inferred until a backup exists (store the device's settings in the
   vendor editor first), and never send firmware-update or DFU messages at all.
7. Ledger the message formats with evidence IDs.

**Legal note (P1):** observing your own instrument and its vendor files to interoperate is the
textbook protected case: US fair use and 17 U.S.C. s.1201(f), EU Directive 2009/24/EC arts. 5(3) and 6
(which art. 8 says contracts cannot override), UK CDPA s.50B and s.296A, Canada Copyright Act s.41.12.
Copying a vendor's script or editor files into our repo is different: those files are copyrighted
("All rights reserved" in Arturia's generated modules). Write our own code from the facts. Not legal
advice.

### 3.2 Playbook P2: a USB device we own

1. `Get-PnpDevice -PresentOnly` and `Get-PnpDeviceProperty` give the VID, PID, revision (`REV_xxxx`),
   compatible IDs and the bound driver (HW-E1, HW-E2).
2. Full descriptors: **USBView**, which is already on this PC at
   `C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\usbview.exe`. It runs headless as
   `usbview.exe /q /f /saveall:<file.txt>` (or `/savexml:`), writing to a file of your choice.
   Alternatively use Uwe Sieber's **UsbTreeView** (freeware, portable, decodes more classes and shows
   descriptor hex). On Linux use `lsusb -v`.
3. Re-decode class-specific descriptors against the class spec whenever the viewer's label matters
   (section 5.1 shows why).
4. Traffic, only if needed: **USBPcap** with Wireshark on Windows. It is a kernel filter driver (driver
   GPL-2.0, command-line tool BSD-2-Clause, by Tomasz Moń) and needs admin and a driver install, so it is
   Daniel's call on this machine. The Wireshark wiki notes it once broke keyboards and mice on some
   systems. The alternative is a Linux VM with the device passed through and `usbmon` on the host.
   **Start the capture before plugging the device in** to catch enumeration.
5. Filter the capture to the target device's address. Captures from a shared root hub can include
   **keyboard input, that is, passwords**. Keep captures out of the repo.
6. Public precedent to learn from: Geoffrey D. Bennett reverse-engineered the Focusrite Scarlett USB
   control protocol by watching Focusrite Control 2.3.4 talk to an 18i20 with usbmon (July-August 2018,
   per the header of the Linux kernel's `mixer_scarlett2.c`). That became the upstream kernel driver,
   the `alsa-scarlett-gui` panel (GPL-3.0-or-later) and a firmware utility. Per Libre Arts (2025-03-04),
   Focusrite now provides him technical information and devices. Our Scarlett 2i2 4th Gen is on his
   supported list. *Inference:* since Focusrite Control does not run on Linux, he probably ran it in a
   Windows VM with USB passthrough; the header does not say.

**Legal note (P2):** reading descriptors is reading what the device publishes to every host; no lock
is involved. Capturing your own device's traffic for interoperability is the Bennett pattern. If a
protocol is encrypted or authenticated with a key, deriving that key is a s.1201 question. Stop and
ask. Not legal advice.

### 3.3 Playbook P3: wires on a board we own (logic analyser + sigrok)

1. Identify the candidate signals from the board's markings, the chip datasheets (part numbers on the
   chips) and the FCC ID photos.
2. Measure voltage levels with a multimeter before connecting anything. Connect ground first.
3. Pick the sample rate (at least 4x the bit rate) and capture a short window around the event you
   trigger (press a key, power on).
4. Decode in PulseView or `sigrok-cli` with stacked decoders. Confirm the decoder's settings (baud
   rate, bit order, polarity) are *observed*, not assumed: a wrong baud rate produces confident nonsense.
5. Save captures as `.sr` with a note of the sample rate and channel map.
6. Practise first on public, permitted material: **sigrok-dumps** (public domain; folders for `uart`,
   `i2c`, `spi`, `usb`, `jtag`, `swd`, `ook` and many more; there is no `midi` folder) and on our
   synthetic MIDI line (HW-E10).

**Safety (P3):** wrong voltage destroys parts; mains-powered devices can be lethal inside. Work only
on unplugged low-voltage boards or ones powered by their own low-voltage supply. **Legal note (P3):**
probing your own board is lawful; defeating read-out protection or secure boot to extract code is
circumvention (section 7). Not legal advice.

### 3.4 Playbook P4: a firmware image (VM only)

1. **Identify:** file name, size and SHA-256 on the host (metadata only), plus where it came from and
   the vendor's licence terms.
2. **Move it into the analysis VM** (networking off, no shared folders, snapshot taken). Never
   double-click it, never run its updater on the host, never commit it to the repo.
3. **Triage:** `file`, `strings -n 8`, `binwalk <img>` (signatures) and `binwalk -E <img>` (entropy).
4. **Read the entropy map with care:** flat near 8 everywhere with no known header points to encryption
   or an unknown compressor. A header at the start of a high-entropy region means compression you can
   unpack.
5. **Extract:** `unblob -e <outdir> <img>` or `binwalk -eM <img>`. Record each extracted file's hash
   (REA-style lineage).
6. **Inventory what came out:** file systems, configuration files, strings, embedded licences (GPL
   components imply a source-code offer from the vendor), version strings.
7. **Compare versions** (for example 1.2.1 against 1.5.0) to see what changed. FACT exists for this at
   scale; a hash and size diff works for two images.
8. **Stop at encryption or signatures.** Record "encrypted: contents unknown" as an honest finding.
   Do not hunt for keys.
9. Emulation (EMBA, QEMU) *executes* the firmware. That is a separate, explicit step in a throwaway VM.

**Legal note (P4):** analysing firmware of a device you own for understanding, repair or
interoperability is broadly defensible (EU arts. 5(3) and 6; US s.1201(f) and the 37 C.F.R. s.201.40
repair and security-research exemptions; Canada s.41.121 for maintenance and repair). Decrypting
protected firmware, bypassing signature checks, or redistributing the image is where it stops.
Firmware licences (EULAs) may forbid reverse engineering. That clause is unenforceable for the
protected acts in the EU and UK, but in the US *Bowers v. Baystate* (Fed. Cir. 2003) enforced such a
clause. For radio devices, modified firmware can also break the device's radio certification (FCC
47 C.F.R. s.2.944; EU Radio Equipment Directive art. 3(3)(i), which per FSFE was never activated). Not
legal advice.

### 3.5 Playbook P5: radio, receive-only

1. Find the frequency from the label, the FCC ID record or the manual (most house sensors sit at
   433.92, 868 or 915 MHz).
2. Look in SDR++ or gqrx with the waterfall; tune slightly off-centre to dodge the DC spike.
3. Record a short IQ file with SigMF metadata (or at least the sample rate and frequency in the
   filename).
4. Try `rtl_433` first (`rtl_433 -r file.cu8` works offline on recordings). If unknown, open it in
   inspectrum or URH to measure the symbol timing and demodulate.
5. Keep recordings of *our own* devices only. Practise on the public `rtl_433_tests` recordings
   (`tests/GROUP/DEVICE/SET`).
6. Never transmit. URH and HackRF can transmit and "replay"; that needs a licence or a certified device
   within its limits, and replaying someone else's remote is not ours to do.

**Legal note (P5):** see section 7.4. Short version: in the US, receiving publicly accessible radio is
generally lawful, but intercepting cellular or cordless calls, or encrypted transmissions, is not
(18 U.S.C. s.2511), and divulging intercepted private radio content is barred (47 U.S.C. s.605). In the
UK, listening to messages you are not authorised to receive is an offence (Wireless Telegraphy Act 2006
s.48). Not legal advice.

---

## 4. Tools: what each is for, licence and cost, status on this PC

| Tool | Layer / purpose | Licence, cost | Platforms | On this PC (HW-E8) |
|---|---|---|---|---|
| Windows MIDI Services console `midi` and MIDI Monitor | Enumerate, monitor (with capture to file), send, SysEx files; multi-client endpoints | MIT, free (Microsoft) | Windows | Service and transports present; the SDK Runtime and Tools (console and monitor) are **not installed** (per the 2026-09-14 FL jam inventory) |
| MIDI-OX (Jamie O'Connell, Jerry Jorgenrud) | Classic monitor, filter, SysEx view and send | Copyrighted freeware for non-commercial use | Windows | Not installed. Download only from midiox.com; search results include crack sites. |
| ReceiveMIDI / SendMIDI (Geert Bevin) | CLI monitor and sender; `syx` writes SysEx to a file | GPL-3.0, free | Win/macOS/Linux | Not installed |
| Protokol (Hexler) | Monitor for MIDI, OSC, Art-Net, gamepads | Free (EULA) | Win/macOS/Linux/mobile | Not installed |
| USBView (Microsoft) | Device/config/interface/endpoint descriptors; headless `/saveall:` | Free (Windows SDK); source in Windows-driver-samples | Windows | **Installed** |
| UsbTreeView (Uwe Sieber) | Richer descriptor decoding, hex dumps | Freeware, portable | Windows | Not installed |
| USBPcap + Wireshark | USB request capture | USBPcap: driver GPL-2.0, CMD BSD-2; Wireshark GPL | Windows | Not installed (kernel filter driver: Daniel's call) |
| usbmon + Wireshark | USB request capture | Part of Linux; free | Linux (VM) | n/a |
| sigrok: sigrok-cli, PulseView, libsigrokdecode | Logic capture and 131 protocol decoders | GPL-3.0-or-later, free | Win/macOS/Linux | Not installed |
| fx2lafw | Open firmware for cheap FX2 analysers | GPL-2.0-or-later | (runs on the analyser) | No analyser seen by this PC |
| Saleae Logic 2 | Analyser software, automation API, MCP workflows | Proprietary; needs Saleae hardware | Win/macOS/Linux | Not installed |
| flashrom | Read/write SPI and other flash chips | GPL, free | Linux mainly | n/a |
| binwalk 3 | Signature scan, extraction, entropy | MIT, free | Linux/macOS (Docker, Cargo) | Not installed |
| unblob (ONEKEY) | Chunk-accurate extraction with reports | MIT, free | Linux (pip/Nix/Docker) | Not installed |
| EMBA | Firmware security analyser with emulation | GPL-3.0 | Kali/Ubuntu/Docker | n/a |
| FACT (Fraunhofer FKIE) | Unpack, analyse, compare firmware versions | GPL-3.0 | Debian/Ubuntu/Kali server | n/a |
| REA (morluto) | Evidence-ledgered firmware and capture inspection over MCP | see repo | Linux x64 for firmware | n/a |
| RTL-SDR dongle | Receive-only SDR hardware | about USD 30 | USB | None seen by this PC |
| SDR++ | Receive, waterfall, recording | GPL-3.0 | Win/Linux/macOS/BSD | Not installed |
| GNU Radio (radioconda) | Signal-processing flowgraphs | GPL-3.0 | Win via radioconda | Not installed |
| inspectrum | Offline signal measurement | GPL-3.0 | Linux/macOS/Win (conda) | Not installed |
| Universal Radio Hacker | Demodulate, infer protocol fields | GPL-3.0 (archived 2026-03-29) | Win/Linux/macOS | Not installed |
| rtl_433 | Decode 386 ISM sensor protocols; JSON/MQTT out | GPL-2.0 | Win/Linux/macOS | Not installed |
| Windows Sandbox | Disposable Windows VM | Included with Windows Pro | Windows 11 Pro | **Feature disabled** |
| Hyper-V | Full VMs | Included with Windows Pro | Windows 11 Pro | **Feature disabled** |
| WSL 2 | Linux distros | Included | Windows | Present (Ubuntu, Ubuntu-24.04, Ubuntu-Migrate, docker-desktop). **Not an analysis sandbox by default.** |

---

## 5. Worked examples

### 5.1 W1: the KeyLab 88 mk3's USB self-description (real, ours)

**Command (HW-E3):** `usbview.exe /q /f /saveall:<scratchpad>\usbview_all.txt`, once, read-only. The
KeyLab is a Full Speed device at hub port 2 (serial number redacted here).

**Observations (from the dump):**

- Device descriptor: USB 2.0, `bDeviceClass 0x00` (classes are per interface), `bMaxPacketSize0` 64,
  `idVendor 0x1C75` (Arturia), `idProduct 0x02CE`, **`bcdDevice 0x1500`**, strings "Arturia" and
  "KeyLab 88 mk3", one configuration.
- Configuration: `wTotalLength 0x0097` (151 bytes), 3 interfaces, self-powered, 0 mA from USB.
- Interface 0: class `0xFE` subclass `0x01` protocol **`0x02`**, string **"Firmware Updater"**, no
  endpoints, followed by a 9-byte descriptor of type `0x21` that USBView printed as a **"HID
  Descriptor"** with `bNumDescriptors 0x40`, and then 64 entries running far past the configuration's
  end (the values after the 151st byte are not device data).
- Interface 1: Audio / AudioControl, header `bcdADC 1.00` pointing at interface 2.
- Interface 2: Audio / **MIDIStreaming**, two bulk endpoints (`0x02` OUT, `0x81` IN, 64 bytes each),
  and these class-specific descriptors (hex as USBView printed them):

```
07 24 01 00 01 61 00            MS header, MIDIStreaming 1.00, class block = 0x61 (97) bytes
06 24 02 01 01 07               MIDI IN jack  #1 embedded   (string 7)
06 24 02 02 02 00               MIDI IN jack  #2 external
09 24 03 01 03 01 02 01 08      MIDI OUT jack #3 embedded, fed by jack 2 (string 8)
09 24 03 02 04 01 01 01 00      MIDI OUT jack #4 external, fed by jack 1
06 24 02 01 05 09               MIDI IN jack  #5 embedded   (string 9)
06 24 02 02 06 00               MIDI IN jack  #6 external
09 24 03 01 07 01 06 01 0A      MIDI OUT jack #7 embedded, fed by jack 6 (string 10)
09 24 03 02 08 01 05 01 00      MIDI OUT jack #8 external, fed by jack 5
06 25 01 02 01 05               endpoint 0x02 (to device): cable 0 -> jack 1, cable 1 -> jack 5
06 25 01 02 03 07               endpoint 0x81 (to host):   cable 0 -> jack 3, cable 1 -> jack 7
```

**Decoded by our script (HW-E4, Appendix A), with arithmetic cross-checks:**

- The class-specific block adds up to 97 bytes, matching the header. The whole configuration adds up
  to 151 bytes (six 9-byte descriptors plus 97), matching `wTotalLength`. Both are observations.
- **Two virtual cables in each direction** on one pair of bulk pipes.
- Re-reading USBView's "HID" fields as the raw bytes `09 21 0B FF 00 40 00 10 01` and decoding them as a
  **DFU 1.1 functional descriptor** gives: download yes, upload yes, manifestation-tolerant no,
  **will-detach yes**, detach timeout 255 ms, transfer size 64 bytes, `bcdDFUVersion 0x0110` (DFU 1.1).
  Every field lands on a sensible value.

**Inferences (with confidence):**

- *High:* USBView's label is wrong. Under a DFU interface, type `0x21` is the DFU functional
  descriptor, and its HID decoder walked past the descriptor's end. **A viewer's label is the viewer's
  inference.**
- *Medium-high:* cable 0 is the port Windows calls "KeyLab 88 mk3 MIDI" and cable 1 is "KeyLab 88 mk3
  DAW". The basis is the cable order plus Windows MIDI Services' endpoint names ending `_0_0`/`_0_1`
  and `_1_0`/`_1_1` (HW-E1). The jack name strings (indexes 7 to 10) were not printed by USBView, so this
  is not yet observed.
- *Medium:* the external-jack topology (embedded 1 to external 4, external 2 to embedded 3) matches the
  USB-MIDI spec's own "MIDI adapter" example. It may be boilerplate rather than a statement about
  physical DIN sockets. **Descriptors cannot tell you which connectors exist on the case.**
- *Unknown:* why the run-time DFU interface reports protocol `0x02`, which the DFU 1.1 spec reserves for
  DFU *mode* (run-time is `0x01`). It may be a vendor variant; the device works either way.

**Why it matters:** the device itself tells us how many ports it has, how they are wired, and that it
can be put into firmware-update mode over USB (will-detach). That last fact is a **do-not-touch**: never
send `DFU_DETACH` or any DFU request to the instrument.

### 5.2 W2: the KeyLab's DAW protocol from the vendor's own files (static, ours)

**Observations (HW-E5, the FL Studio script folder `Documents\Image-Line\FL Studio\Settings\Hardware\Arturia KeyLab mk3`):**

- `device_KL3.py` (by Farès Mezdour, version 1.1) declares FL's auto-detect patterns: Arturia's ID
  `00 20 6B`, then `02 00`, then `0A 02`, `0A 04` or `0A 08`, then `7F 7F 7F 7F`.
- Every SysEx the script sends goes through one function that wraps the payload as
  **`F0 00 20 6B 7F 42 <payload> F7`**.
- On start-up the script sends a "DAW connection" message whose payload is
  `00 <patch 02 = DAW> <param 05 = connection> 01`, so the full message is
  `F0 00 20 6B 7F 42 00 02 05 01 F7`. On exit it sends the same with `00` (disconnect). The parameter
  numbering comes from the generated module `ParamId.py`: properties 0, value 1, string 2, set-LED 3,
  display 4, connection 5, bank 6, program 7, soft-connection 8.
- The dispatcher module carries an MIT notice for Ray Juang (2020) inside an otherwise Arturia
  "all rights reserved" folder. **Two licences in one vendor folder.**
- The folder also holds Arturia's PDF *KeyLab mk3 FL Studio DAW User Guide* (2024-08-27).

**Observations (HW-E6, `C:\ProgramData\Arturia\MIDI Control Center\Resources\KeyLab3 88.json`):**

- `usbVendorId 7285` (= `0x1C75`), `manufacturerId "00206B"`, `familyId "0200"`, protocol name
  `"arturia_v4"`, version format `"$3.$2.$1"`, 976 parameter fields (the first is "Velocity Curve",
  `paramId 1`, with Linear/Logarithmic/Exponential/Fixed/Custom/Global), and one hardware alternative:
  `usbProductId 718` (= `0x02CE`), `familyMemberId "0588"`, sku `keylab-88-mk3`, with a
  `firmwareUpdater` block named `"mfreak"` that targets the same VID and PID and uses the file pattern
  `*.kl3`.

**The disagreement, kept open:** FL's patterns imply a family member written `0A 08` (88-key, by our
inference from 02/04/08 lining up with 49/61/88). The editor JSON says `"0588"` (the 49-key file says
`"0582"`). These cannot both be the literal reply bytes. `0x88` is not even a legal MIDI data byte, so
`"0588"` is probably an internal number, not wire bytes. **We do not pick.** The tie-breaker is one
observed Identity Reply.

**The runtime step (not executed; needs Daniel's go):** with FL Studio closed, send `F0 7E 7F 06 01 F7`
to "KeyLab 88 mk3 MIDI" and record the reply. Expected shape:
`F0 7E <dev> 06 02 00 20 6B 02 00 <member: 2 bytes> <revision: 4 bytes> F7`. If the editor's
`"$3.$2.$1"` format is read literally (our inference), three of the revision bytes should spell 1.5.0
in reverse order. The pass condition is that the member bytes and revision are written into the ledger
as observations.

**Design separation, for any future bridge:** "the DAW port expects `F0 00 20 6B 7F 42 ...` with
patch/param numbering" is *observed vendor behaviour*. "Show the game's wave number on the KeyLab
screen" would be *our design choice*. They stay in separate documents.

### 5.3 W3: facts about the firmware without opening it (ours)

**Observations (HW-E7, HW-E2, HW-E3):**

| File in `%USERPROFILE%\Downloads` | Size | Date | SHA-256 (prefix) |
|---|---|---|---|
| `KeyLab3_FW__1_2_1.kl3` | 7,722,297 | 2026-01-24 | `C1D6313C21F1...` |
| `KeyLab3_FW__1_5_0.kl3` | 7,550,541 | 2026-06-11 | `0CDA58219C3A...` |

- Each has a 108-byte `.confirm` JSON with `size`, `checksum` and `extension`. Recomputing **MD5** of each
  `.kl3` reproduces its `checksum` exactly (`8054a455...` for 1.5.0, `52deb8ea...` for 1.2.1).
- The live device reports `bcdDevice 0x1500` (also visible as `REV_1500` in its hardware ID).
- The editor JSON's updater block contains `extraParameters` with a `productCode` and a `productKey`
  array. **We deliberately do not reproduce those values.**

**Inferences:** *high:* the `.confirm` checksum is a download-integrity check, not an authenticity
signature (anyone can recompute MD5). *Medium-high:* the device is running firmware 1.5.0, encoded in
`bcdDevice` as BCD `15.00`. *Unknown:* whether the `.kl3` is encrypted or signed, and what the updater
does with `productKey`.

**The boundary, demonstrated:** a key-like parameter next to a firmware updater is exactly where an
understanding playbook stops. Using such a value to unpack, decrypt or re-sign firmware is
circumvention of a technical measure (section 7.2). There is also no house goal that needs the
firmware's insides: everything we want from the KeyLab (ports, messages, screen, LEDs) lives at the
MIDI level. If Daniel ever wants the 1.2.1 to 1.5.0 difference studied, the next step is P4 in a VM:
signatures and entropy only, then stop if it is encrypted.

### 5.4 W4: the Scarlett 2i2 4th Gen, and two Windows views that disagree (ours)

**Observations:** the descriptor says `bDeviceClass 0xEF`, subclass `0x02`, protocol `0x01` (a
multi-function device using Interface Association Descriptors), `idVendor 0x1235`, `idProduct 0x8219`,
`bcdDevice 0x0971`, High Speed, with an isochronous IN endpoint (audio) and an interrupt IN endpoint
(HW-E3). Plug and Play's compatible IDs for the same device say `USB\DevClass_00&SubClass_00&Prot_00`
and `USB\COMPOSITE` (HW-E2). The driver is `FocusriteUsb` 4.150.0.432.

**Inference / unknown:** Windows evidently normalises composite devices to class 00 in compatible IDs.
Microsoft's *Standard USB Identifiers* page describes composite handling but does not state this
substitution, so the *reason* stays unknown. **The descriptor bytes are primary; derived labels are
secondary.** For this device the deep work is already public (Bennett, P2 step 6), which is the best
outcome reverse engineering can have: someone did it in the open, and the vendor joined in.

### 5.5 W5: what a logic analyser sees on a MIDI cable (synthetic, ours)

Script `midi_wire_demo.py` (Appendix B) builds the UART waveform for `90 3C 64` at 31,250 baud, samples
it at 1 MHz (32 samples per bit), and decodes it with a ten-line UART decoder. This is the job sigrok's
`uart` then `midi` decoders do. Output (HW-E10):

```
1216 samples = 1216 microseconds of wire time
t=  128.0 us  byte=0x90  STATUS  stop bit ok=True
t=  448.0 us  byte=0x3C  data    stop bit ok=True
t=  768.0 us  byte=0x64  data    stop bit ok=True
=> Note On on channel 1: note 60, velocity 100
   one 3-byte message takes 0.96 ms on a DIN cable (10 bits per byte)
USB-MIDI event packet on cable 0: 09 90 3C 64
```

The same musical event is 30 bits of serial line on DIN and one 4-byte packet on USB. Which tool you
need depends on which of those two you can reach.

### 5.6 W6: entropy cannot tell compressed from encrypted (synthetic, ours)

Script `firmware_entropy_demo.py` (Appendix C) builds a toy image: a 64-byte header with magic `TOYF`,
a 27,437-byte gzip stream of structured text, 8 KiB of random bytes standing in for an encrypted
blob, 8 KiB of `FF` "erased flash", and plain config text. It then runs a toy signature scan and a
4 KiB entropy map (HW-E11):

```
SIGNATURE SCAN
  0x000000  toy firmware header
  0x000040  gzip stream
ENTROPY (bits per byte, 4 KiB blocks)
  0x000000-0x007000  7.89-7.96   <- gzip and random blocks look the same
  0x008000           6.51        <- block straddling random and padding
  0x009000           0.00        <- erased flash
  0x00A000-0x00B000  2.11, 4.36  <- padding into text
per-region: gzip 7.99, random 7.98, padding 0.00, config text 4.36, source text before gzip 4.53
```

The entropy map shows no boundary between the gzip stream and the "encrypted" block. Only the
signature scan's `gzip stream` hit at `0x40` tells you the first region can be unpacked.

### 5.7 Public, permitted practice material (not downloaded tonight)

- **sigrok-dumps** (public domain, github.com/sigrokproject/sigrok-dumps): real captures for dozens of
  protocols, for practising decoders.
- **OpenWrt images** (openwrt.org; GPL, with published source): firmware where the source is the
  answer key. Extract an image in the VM and check what you found against the source tree.
- **rtl_433_tests** (github.com/merbanan/rtl_433_tests): recordings of real sensors, for practising
  `rtl_433 -r` and inspectrum without owning an SDR.
- **Roland MIDI Implementation documents** (for example the TB-3, 2014): how a vendor *documents*
  SysEx, which is the target format for our own ledgers.
- **francoisgeorgy/microfreak-reverse** (François Georgy, archived 2024-04-05): a community write-up of
  the SysEx for Arturia's MicroFreak. The KeyLab's editor JSON names its updater `mfreak`, which
  suggests (inference only) that Arturia reuses MicroFreak-era updater code. Useful as a model of a
  published SysEx map.

Downloading any of these is a separate step: it needs Daniel's OK, and the data goes into the VM.

---

## 6. Mistakes that waste time (or break things)

1. **Trusting the viewer's label.** USBView called a DFU descriptor "HID" (W1). Re-decode against the
   class spec.
2. **Asking a tool about a layer it cannot see.** A MIDI monitor will not show USB control transfers.
   A 24 MHz logic analyser will not follow full-speed USB. Software USB capture will not show bus-level
   handshakes.
3. **Wrong baud rate or polarity in a decoder.** You get confident garbage. Measure one bit's width
   first.
4. **Forgetting running status and real-time interleaving** when parsing raw MIDI, so the byte count
   seems off.
5. **Reading 7-bit packed dumps as plain bytes.** Look for nibble splits or a high-bits byte every 8.
6. **Mistaking a checksum for a parameter** when diffing two dumps. One knob changing two bytes is the
   tell.
7. **Zadig on the wrong device.** Installing WinUSB for an SDR on the KeyLab's or Scarlett's entry breaks
   that device until the driver is rolled back. Check the VID and PID in Zadig before clicking Install.
8. **Starting a USB capture after plugging in** and missing enumeration (the descriptors).
9. **Committing captures.** USB captures can include keystrokes; MIDI captures can include whole
   performances. Keep raw captures in the scratchpad or VM, not the public repo.
10. **Using the default WSL distro or Docker Desktop as a sandbox.** WSL mounts C: and E: and can launch
    Windows programs by default (`[automount] enabled` and `[interop] enabled` are both on). Docker
    Desktop is the VM that hosts `akashic-redis`, and the 2026-09-11 outage showed how a
    WSL/Docker/kernel-pool problem takes the whole house down.
11. **Entropy over-reading.** High entropy is "compressed or encrypted", never "encrypted" alone.
12. **Sending inferred SysEx writes without a backup,** or anything firmware-related to the instrument.
13. **Two sources disagree, so pick the newer one.** Record both and design the observation that
    settles it (W2).
14. **Buying a "clone" analyser** that ships another vendor's software. Buy one sold under its own name.
15. **Bounded searches reported as global.** "Not found" always carries its search boundary.

---

## 7. Legal and safety notes (jurisdiction-aware; not legal advice)

### 7.1 Understanding and interoperating

- **US: fair use for intermediate copying.** *Sega Enterprises v. Accolade*, 977 F.2d 1510 (9th Cir.
  1992, Judge Reinhardt): disassembly is fair use when it is the only way to reach unprotected
  functional elements and there is a legitimate reason. It is also a *hardware-lock* case: Sega's
  console checked for a code that displayed Sega's trademark, and the court held that Sega, not
  Accolade, bore responsibility for that false labelling. *Sony Computer Entertainment v. Connectix*,
  203 F.3d 596 (9th Cir. 2000; panel of Choy, Canby and Silverman): intermediate copying of the
  PlayStation BIOS to build an emulator was fair use; the result was "modestly transformative".
- **US: trade secrets.** Reverse engineering is not "improper means" under the Defend Trade Secrets Act
  (18 U.S.C. s.1839(6)(B)).
- **EU: Directive 2009/24/EC.** Art. 5(3) lets a lawful user observe, study or test a program to find its
  ideas and principles. Art. 6 allows decompilation when indispensable for interoperability of an
  independently created program, with limits: the information must not already be readily available,
  only the needed parts may be decompiled, and the information may not be reused for a substantially
  similar program. Art. 8 makes contract terms contrary to art. 6 or 5(2)-(3) null and void. The CJEU's
  *SAS Institute v World Programming* (C-406/10, 2012) is widely cited for functionality and data file
  formats not being protected as such. We could not fetch its primary text tonight because EUR-Lex
  refused automated reads.
- **EU: trade secrets.** Directive (EU) 2016/943 art. 3(1)(b) makes acquisition by observing, studying,
  disassembling or testing a lawfully held product lawful, absent a valid contractual duty not to.
- **UK:** CDPA 1988 s.50B (decompilation for interoperability) and s.296A (contrary terms void).
- **Canada:** Copyright Act s.41.12 (interoperability, including devices in which the program is
  embedded) and s.41.121 (circumvention solely to maintain or repair a product, including diagnosis).
- **Contracts (EULAs, terms of service):** in the US a licence clause can forbid reverse engineering and
  be enforced (*Bowers v. Baystate*, 320 F.3d 1317, Fed. Cir. 2003, over Judge Dyk's dissent). In the EU
  and UK the protected acts above cannot be contracted away. Read the EULA before P4.

### 7.2 Anti-circumvention (the "lock" question)

- **US 17 U.S.C. s.1201** bars circumventing a technological measure that controls access to a
  copyrighted work, and trafficking in tools for it. The exemptions that matter here:
  **s.1201(f)** (reverse engineering for interoperability of an independently created program, by
  someone with the right to use the copy, where the information was not readily available);
  **s.1201(g)** (good-faith encryption research); **s.1201(j)** (security testing *with the owner's
  authorisation*); and the triennial **37 C.F.R. s.201.40** exemptions (last amended 2024-10-28),
  which per LII's rendering include **(b)(15)** diagnosis, maintenance and repair of lawfully acquired
  consumer devices and **(b)(18)** good-faith security research on lawfully acquired devices in an
  environment designed to avoid harm. The rule itself warns that other laws, such as the CFAA, may
  still apply.
- **Hardware-specific precedents:** *Chamberlain v. Skylink*, 381 F.3d 1178 (Fed. Cir. 2004), a
  universal garage-door remote: s.1201 liability needed a nexus to copyright infringement. *Lexmark v.
  Static Control*, 387 F.3d 522 (6th Cir. 2004), printer-cartridge authentication chips: lock-out code is
  largely functional, and the measure did not "effectively control access" because the code was readable
  from the printer anyway. The Ninth Circuit rejected the nexus rule in *MDY v. Blizzard* (2010), so the
  answer depends on the circuit.
- **What this means for us:** observing, reading published descriptors, monitoring our own traffic and
  reading vendor files in plain text involve no lock. **Decrypting firmware, using a vendor key,
  defeating read-out protection or secure boot, or bypassing a licence check is the boundary.** This
  playbook stops there and records the unknown. The house's scope rules also exclude DRM and licence
  cracking, anti-cheat or anti-tamper bypass, piracy and intrusion into systems we do not own, whatever
  an exemption might allow.

### 7.3 Assets versus mechanics (for the future game)

Game rules and mechanics are ideas (17 U.S.C. s.102(b)); art, sound, code and distinctive visual
expression are protected. *Tetris Holding v. Xio Interactive*, 863 F. Supp. 2d 394 (D.N.J. 2012,
Judge Freda Wolfson): copying Tetris's look (board dimensions, piece shapes and colours, the overall
visual style) infringed, even though the rules themselves were free. If you have to squint to tell
the two games apart, they are likely too similar. For an Archero-style game: study the upgrade-path
*mechanics* freely; draw, compose and code everything ourselves; avoid trade dress that mimics the
original's look and feel. Reverse-engineering a game's *assets* or its *online service* is out of
scope.

### 7.4 Radio

- **US.** Unlicensed (Part 15) devices must not cause harmful interference and must accept
  interference (47 C.F.R. s.15.5). Receiving is broadly lawful for transmissions readily accessible to
  the general public, but **18 U.S.C. s.2511** criminalises intercepting private electronic
  communications. Its public-access exceptions exclude cellular and cordless phone calls and encrypted
  or scrambled transmissions. **47 U.S.C. s.605** bars divulging the contents of intercepted private
  radio traffic (with exceptions for broadcast, amateur, CB and distress traffic). Some US states add
  their own scanner rules. Transmitting needs a licence (for example an amateur licence) or a certified
  device used within its certification. Radios whose software can change frequency, power or modulation
  fall under the software-defined-radio rules (47 C.F.R. s.2.944).
- **UK.** Wireless Telegraphy Act 2006 s.48: it is an offence to use radio equipment, without lawful
  authority, to obtain information about the contents, sender or addressee of a message, or to disclose
  it. Treat "anything not meant for general reception" as off-limits.
- **EU.** Rules vary by member state. The Radio Equipment Directive's art. 3(3)(i), the
  "only compliant software may be loaded" provision that the FSFE campaigned against, has no practical
  effect: per the FSFE (read 2026-10-13), the Commission dropped its delegated act in January 2026.
- **Our rule:** receive and decode **our own** devices; never decode or keep other people's private
  traffic; **never transmit** from the house without a licence and a reason.

### 7.5 Safety (host, electrical, device)

- **Host:** untrusted firmware, captures and documents are analysed only in a **disposable Linux VM**
  (networking off, no shared folders, snapshot before, revert after) or, for Windows-only tools, Windows
  Sandbox with networking disabled and the sample folder mapped read-only. Never execute untrusted code
  on the host. Samples and captures stay out of the repo. Both VM options are disabled on this PC today
  (HW-E8), so enabling one is Daniel's decision. Until then, this domain is limited to the read-only
  host steps used in this report.
- **Electrical:** measure before connecting, ground first, never probe mains-powered internals live.
- **Device:** never send DFU, firmware or bulk-write SysEx to the instruments. Back up settings before any
  write. Do not run flashrom on laptops (its own warning) and back up before writing any chip.
- **Privacy:** captures can contain keystrokes, performances and other people's radio traffic. Filter,
  minimise and keep them local.

---

## 8. How this domain serves the house (and the future game)

- **The piano studio:** a ledger of the KeyLab's ports and DAW protocol lets the piano page or a bridge
  drive the KeyLab's screen and pad LEDs. Everything needed is at the MIDI level, from vendor files plus
  one Identity Reply.
- **The future Archero-style game:** controllers are HID devices, and their report descriptors are the
  lawful map of every button and axis. The KeyLab itself could be a game controller with its screen as a
  HUD (an interoperability use, built from observed messages, with our own design kept separate).
- **The arsenal:** the same evidence discipline carries to every other topic report. Hardware simply
  makes the observation/inference split very concrete: the bytes either came off the device or they did
  not.

---

## 9. Finding ledger and checklist revisit

### 9.1 Evidence index

| ID | What | Where / how |
|---|---|---|
| HW-E1 | Present USB MIDI and audio devices, Windows MIDI Services endpoints (KeyLab MIDI/DAW `_0_0/_0_1/_1_0/_1_1`), Scarlett | `Get-PnpDevice -PresentOnly`, 2026-10-13 |
| HW-E2 | Hardware IDs, compatible IDs, drivers: KeyLab `USB\VID_1C75&PID_02CE&REV_1500`, `arturiausbmidi` 1.7.0.0, child `TUSBAUDIO_ENUM\...`; Scarlett `USB\VID_1235&PID_8219&REV_0971`, `FocusriteUsb` 4.150.0.432, `DevClass_00` + `USB\COMPOSITE` | `Get-PnpDeviceProperty` |
| HW-E3 | Full descriptors from USBView (KeyLab section, Scarlett section) | `usbview.exe /q /f /saveall:` into the scratchpad `usbview_all.txt` (216,475 bytes; includes device serials, so not copied to the repo) |
| HW-E4 | Decoded MIDI topology, length cross-checks, DFU re-decode | `usb_midi_topology.py` (Appendix A) |
| HW-E5 | Vendor FL script: hardware-ID patterns, SysEx wrapper `F0 00 20 6B 7F 42 .. F7`, DAW connect payload, ParamId table, MIT notice | `Documents\Image-Line\FL Studio\Settings\Hardware\Arturia KeyLab mk3\` |
| HW-E6 | Editor JSON identity fields, `arturia_v4`, `$3.$2.$1`, 976 fields, updater `mfreak` | `C:\ProgramData\Arturia\MIDI Control Center\Resources\KeyLab3 88.json` (and `KeyLab3.json` for the 49-key comparison) |
| HW-E7 | Firmware file sizes, SHA-256, `.confirm` = MD5 verified | `%USERPROFILE%\Downloads\KeyLab3_FW__*.kl3*`, hashed with `Get-FileHash` and Python `hashlib` (bytes read, not parsed or executed) |
| HW-E8 | Tool availability: none of wireshark, tshark, sigrok-cli, pulseview, binwalk, unblob, USBPcapCMD, 7z, qemu, VBoxManage on PATH; USBView present; Hyper-V and Windows Sandbox disabled; WSL distros listed | PowerShell checks, 2026-10-13 |
| HW-E9 | FL Studio (`FL64`) running at the time of the work | `Get-Process` |
| HW-E10 | Synthetic MIDI-on-UART decode | `midi_wire_demo.py` (Appendix B) |
| HW-E11 | Synthetic firmware signature and entropy scan | `firmware_entropy_demo.py` (Appendix C) |
| HW-E12 | USB-MIDI 1.0 spec: event packet, CIN table 4-1, MS interface table 6-1, Appendix A codes, authors | usb.org `midi10.pdf`, text extracted with pypdf |
| HW-E13 | DFU 1.1 spec: run-time protocol `01h`, DFU mode `02h`, functional descriptor `21h`, bmAttributes bits | usb.org `DFU_1.1.pdf`, text extracted with pypdf |
| HW-E14 | Roland TB-3 MIDI Implementation (2014-07-04, v1.10): Identity Request/Reply, checksum, nibble split | static.roland.com PDF, text extracted |
| HW-E15 | Bounded negative: no RTL-SDR (`0BDA:2832/2838`), Saleae (`21A9`), Saleae-clone (`0925:3881`), bare FX2 (`04B4:8613`), HackRF (`1D50:6089`), STM32-DFU (`0483:DF11`) or CH341 (`1A86:5512`) IDs or matching names among 1,349 PnP entries (present or remembered) | `Get-PnpDevice` filter |

### 9.2 Findings

| # | Finding | Type | Confidence | Evidence | Boundary / unknowns |
|---|---|---|---|---|---|
| F1 | KeyLab exposes 2 virtual MIDI cables each way on one bulk pair | observation | high | HW-E3, E4 | Jack names (strings 7 to 10) not read |
| F2 | Cable 0 = "MIDI", cable 1 = "DAW" | inference | medium-high | HW-E1, E4 | Needs the string descriptors or a monitor test |
| F3 | KeyLab has a run-time DFU "Firmware Updater" interface: will-detach, upload and download capable, DFU 1.1 | observation (re-decoded) | high | HW-E3, E4, E13 | Protocol `0x02` versus spec `0x01` unexplained |
| F4 | USBView mislabels the DFU functional descriptor as HID and reads past the configuration's end | observation + inference | high | HW-E3, E13 | Only USBView's build on this PC tested |
| F5 | DAW-port SysEx wrapper `F0 00 20 6B 7F 42 .. F7`; connect = `00 02 05 01` | observation (static vendor code) | high that FL sends it; device response unobserved | HW-E5 | Runtime effect not observed |
| F6 | Identity family code `02 00` | observation (two static sources agree) | medium-high | HW-E5, E6 | No reply observed |
| F7 | Family member bytes | **unknown** (sources disagree: `0A 08` vs `"0588"`) | n/a | HW-E5, E6 | Settled by one Identity Reply |
| F8 | Device runs firmware 1.5.0 (`bcdDevice 0x1500`) | inference | medium-high | HW-E2, E3, E7 | Identity Reply revision bytes would confirm |
| F9 | `.confirm` checksum = MD5 of the `.kl3` | observation | high | HW-E7 | Says nothing about signing or encryption |
| F10 | `.kl3` contents, encryption, signature | **unknown** (deliberately not opened) | n/a | n/a | P4 in a VM if Daniel wants; stop at encryption |
| F11 | Scarlett descriptor class `0xEF/02/01` while PnP compatible IDs say `DevClass_00` | observation | high | HW-E2, E3 | Reason undocumented in the MS page read |
| F12 | No logic analyser, SDR or flash programmer has been seen by this PC | bounded negative | as bounded | HW-E15 | Hardware never plugged into this PC is invisible |
| F13 | No disposable VM or sandbox is available today | observation | high | HW-E8 | Enabling one is a system change: Daniel's call |
| F14 | Compressed and encrypted regions are indistinguishable by entropy | observation (synthetic) | high | HW-E11 | Toy data, but the property is general |

### 9.3 Checklist revisit (the brief's questions)

| Question from the brief | Verdict |
|---|---|
| MIDI and USB devices we own | **Answered** for structure (F1-F6, F8, F11). **Partially** for identity (F7 open until one Identity Reply). |
| MIDI monitors | **Answered** (catalogue and commands). None installed; Windows MIDI Services core present, tools absent. |
| USB descriptors | **Answered** with a real decode and a real tool-label error. |
| SysEx documentation | **Answered** (spec facts, manufacturer IDs, Universal Identity, Roland's documented model, Arturia static evidence, MIDI Association ID policy). |
| Logic analysers and sigrok | **Answered conceptually** plus a synthetic example. **Unresolved in practice:** no hardware seen (F12). |
| Firmware images (binwalk, unblob) in a VM | **Answered conceptually** plus a synthetic example plus real metadata (F8-F10). **Unresolved in practice:** no VM (F13), no real image analysed (by design). |
| SDR basics | **Answered conceptually.** **Unresolved in practice:** no SDR (F12). |
| Legal limits (radio, anti-circumvention) | **Answered** for US, EU, UK and Canada. **Unresolved:** the jurisdiction the house acts from is not recorded here. |

---

## 10. (a) ROUTING TABLE: hardware, firmware and signals

| Artifact or question | First tool | Evidence it yields | What it cannot tell you |
|---|---|---|---|
| "What is plugged in, which driver owns it?" | `Get-PnpDevice` / `Get-PnpDeviceProperty` | VID, PID, revision, compatible IDs, driver name and version, parent/child nodes | Interface details when a vendor driver claims the whole device; anything about message formats |
| "What does this USB device say it is?" | USBView `/q /f /saveall:` (on this PC) or UsbTreeView | Device/config/interface/endpoint descriptors, strings, class-specific hex | Runtime behaviour; which physical connectors exist; viewer labels are inferences, so re-decode raw bytes |
| "How many MIDI ports, and how are they wired?" | USBView, then a USB-MIDI descriptor decode (Appendix A) | Jack topology, cable to jack map, endpoint sizes | Port *names* unless the string descriptors are read; what each port's protocol is |
| "What messages does this instrument send when I touch it?" | MIDI monitor (Windows MIDI Services `midi endpoint monitor`, MIDI-OX, ReceiveMIDI) | Timestamped messages, SysEx bytes | What another app sends *to* the device; USB-level control traffic |
| "Who is this MIDI device, which firmware?" | Universal Identity Request `F0 7E 7F 06 01 F7` (with Daniel's go) | Manufacturer ID, family, member, software revision | Anything vendor-specific; devices that do not implement it stay silent |
| "What does the vendor's editor or DAW script send?" | Read the vendor's shipped files first (scripts, editor JSON, manuals) | Message wrappers, parameter IDs, auto-detect patterns | Whether the device behaves as the file claims; files can disagree (W2) |
| "Both directions of USB traffic, vendor control requests" | USBPcap + Wireshark (Windows) or usbmon in a Linux VM | URBs with payloads, enumeration, timing | Bus-level handshakes; meaning of vendor payloads without diffing |
| "What is on this wire / header / test pad?" | Multimeter, then logic analyser + sigrok (`uart`, `i2c`, `spi`, `midi` ...) | Edges, timing, decoded bytes | Analogue faults (use a scope); anything faster than ~1/4 of the sample rate |
| "What is inside this firmware file?" | In the VM: `binwalk` / `binwalk -E`, then `unblob` | Signatures with offsets, entropy map, extracted tree with hashes | Encrypted or signed contents; behaviour (that needs emulation, a separate risky step) |
| "What changed between firmware versions?" | In the VM: hash and size diff, then unblob both and diff the trees (FACT at scale) | Changed files, strings, components | *Why* it changed; anything inside encrypted parts |
| "Is this region compressed or encrypted?" | Signature scan **and** entropy together | Header present means unpackable; no header plus about 8 bits/byte means unknown | Entropy alone never answers it |
| "What is this radio device sending?" | Label or FCC ID record, then SDR++ waterfall, then `rtl_433`, then inspectrum or URH | Frequency, modulation, symbol timing, decoded fields | Encrypted payloads; whether you may lawfully keep or decode others' traffic |
| "Can I legally do this?" | Section 7 of this report, then a human lawyer for anything beyond our own devices | Orientation by jurisdiction | Legal advice |

## 11. (b) Lessons the house should keep

1. **Use when** any hardware behaviour is in question, **before** sniffing or capturing anything: read
   what the vendor already ships in readable form (manuals, MIDI implementation charts, DAW scripts,
   editor resource JSON); it usually answers the question. **Don't when** the shipped files disagree
   with each other; then they are the question, and only a runtime observation settles it.
2. **Use when** a descriptor viewer or decoder labels a structure, **before** building on the label:
   re-decode the raw bytes against the class spec, because type codes are reused across classes (`0x21`
   is both HID and DFU). **Don't when** no raw bytes are available; then record the label as the tool's
   inference.
3. **Use when** two sources disagree about an ID, version or format, **before** choosing either: log
   both as an unknown and name the single observation that decides it. **Don't when** that observation
   would touch a device in use (FL Studio open, a performance running); schedule it instead.
4. **Use when** you need both directions of USB-MIDI or a vendor's control requests, **before** buying or
   wiring a logic analyser: capture at the USB stack (USBPcap or usbmon), since 12 Mbit/s USB outruns
   24 MHz analysers. **Don't when** a MIDI monitor already shows what you need; a USB filter driver is a
   system change on this machine.
5. **Use when** a firmware region measures near 8 bits per byte, **before** calling it encrypted: look
   for a compression header; entropy cannot tell compressed from encrypted. **Don't when** there is no
   header and a key-like vendor parameter sits nearby; stop there, it is the circumvention boundary.
6. **Use when** about to run binwalk, unblob, EMBA or any extractor on firmware or captures from outside
   the house, **before** the first command: move the sample into a disposable Linux VM with networking
   off and no shared folders, because extractors have had code-execution bugs (CVE-2022-4510).
   **Don't when** the only "sandbox" on hand is the default WSL distro or Docker Desktop (which hosts
   `akashic-redis`); wait for a real VM.
7. **Use when** choosing a logic analyser sample rate, **before** capturing: sample at least 4x the
   fastest digital rate (10x bandwidth for analogue), and measure the voltage level and ground first.
   **Don't when** the target is mains-powered or its voltage is unknown.
8. **Use when** receiving radio, **before** recording or decoding: keep to our own devices and
   publicly broadcast services, never cellular, cordless, encrypted or (UK) anything not meant for
   general reception; never transmit without a licence. **Don't when** a tool offers "replay"; that is
   transmitting.
9. **Use when** installing a WinUSB driver with Zadig for an SDR or analyser, **before** clicking
   Install: confirm the selected VID and PID, because replacing the KeyLab's or Scarlett's driver breaks
   them. **Don't when** the device already works with its vendor driver.
10. **Use when** sending anything to an instrument, **before** sending more than a Universal Identity
    Request: store a settings backup in the vendor editor, never send DFU or firmware messages, and keep
    any test SysEx on ID `7D` (private use). **Don't when** another app is using the device or Daniel
    has not said go.
11. **Use when** saving a USB, MIDI or radio capture, **before** it leaves the scratchpad or VM: filter it
    to the target device and strip anything personal (keyboards on the same hub leak keystrokes); never
    commit raw captures. **Don't when** the capture is a synthetic or public-domain sample meant for
    teaching.

## 12. (c) Gaps: new tools or verbs the house would need

1. **An analysis VM (the blocking gap).** A disposable Linux VM (Hyper-V, or VirtualBox if Daniel
   prefers) with snapshots, networking off by default and no shared folders, preloaded with binwalk 3,
   unblob plus its extractors, sigrok-cli, tshark, rtl_433, inspectrum and optionally REA's Linux
   firmware tools. Enabling Hyper-V or Windows Sandbox is a system-settings change, so it is **Daniel's
   decision**. A future `py agent_cli.py vm-analyse <file>` verb would copy a sample in read-only and
   return the report plus hashes.
2. **`usb-descriptors` verb.** It would wrap the already-installed USBView (`/q /f /savexml:`) and decode
   the classes we care about (USB-MIDI jacks and cables, DFU, HID report descriptors, Audio). It would
   emit JSON with `HW-E` style evidence IDs and **flag where the viewer's label and the re-decode
   disagree.** Appendix A is the seed. Serial numbers should be redacted by default (the repo is
   public).
3. **`midi-probe` verb.** It would send the Universal Identity Request to a named port, record the reply,
   and log monitored SysEx with timestamps into a ledger. It needs either the Windows MIDI Services SDK
   Runtime and Tools or a Python MIDI library (`mido`/`python-rtmidi` are not installed); either is an
   install, so Daniel's OK. It should refuse to send anything except an allow-list of read-only
   queries.
4. **A device ledger file** (a living, ours-only description of each instrument's ports and messages:
   KeyLab 88 mk3 first) so findings like F1-F9 are not rediscovered per session.
5. **Entry hardware (purchase decision, Daniel's):** a logic analyser sold under its maker's own name
   that sigrok supports, and an RTL-SDR receiver. Nothing of either kind has been seen by this PC (F12).
6. **USB capture path:** USBPcap is a kernel filter driver (risky on this machine's posture and history),
   so the safer route is USB passthrough into the analysis VM and usbmon there. This depends on gap 1.
7. **Jurisdiction record:** the legal notes are written for US, EU, UK and Canada. The house should
   record which law it actually acts under, so future playbooks can be specific.
8. **Saleae MCP watch item:** Saleae now advertises MCP-driven capture and decode. If the house ever buys
   Saleae hardware, that is a natural agent-facing door; unverified tonight.

---

## 13. Sources (read 2026-10-13 unless marked)

**Discipline**
- https://github.com/morluto/rea : the REA skill (`.agents/skills/reverse-engineer-anything/SKILL.md`), source of the evidence discipline in section 1 (credited as morluto/rea).
- https://github.com/morluto/rea/blob/main/docs/firmware-analysis.md : REA's firmware route; Linux x64, binwalk 3.1.x and unblob 26.6.x, limits, lineage, no execution.

**MIDI**
- https://midi.org/summary-of-midi-1-0-messages : official message table (status bytes, system messages, SysEx manufacturer ID sizes).
- https://midi.org/about-midi-part-3midi-messages : plain-language intro to status and data bytes, SysEx, real-time priority.
- https://midi.org/sysexidtable : the assigned manufacturer SysEx ID table (Arturia, Focusrite/Novation, Roland, Yamaha, Korg, Kawai).
- https://midi.org/new-midi-association-sysex-id-policies-as-of-oct-15-2025 : 2025 ID policy; `7D` for private non-commercial work, `7C` limited to MIDI 2.0 discovery.
- https://static.roland.com/assets/media/pdf/TB-3_MI_1.pdf : Roland TB-3 MIDI Implementation (2014); byte-level Identity Request and Reply, checksum, nibble split.
- https://github.com/francoisgeorgy/microfreak-reverse : François Georgy's community SysEx map for the Arturia MicroFreak (archived).
- https://www.w3.org/TR/webmidi/ : Web MIDI API; SysEx is a separate, stronger permission.
- https://microsoft.github.io/MIDI/tools/console/ : Windows MIDI Services console command tree (`midi endpoint monitor`, capture to file, `sysex`).
- https://microsoft.github.io/MIDI/tools/midi2monitor/ : Windows MIDI Monitor app (developer preview).
- https://github.com/microsoft/MIDI : Windows MIDI Services repository, MIT licence.
- https://github.com/gbevin/ReceiveMIDI : Geert Bevin's CLI monitor (GPL-3.0) with SysEx-to-file.
- https://hexler.net/protokol : Hexler's free Protokol monitor.
- http://www.midiox.com/ : MIDI-OX home (not fetchable: certificate error); freeware status per search results.
- https://raw.githubusercontent.com/sigrokproject/libsigrokdecode/master/decoders/midi/__init__.py : sigrok MIDI decoder; 31250 baud, 8N1, LSB-first, stacks on uart.

**USB**
- https://www.usb.org/sites/default/files/midi10.pdf : USB Device Class Definition for MIDI Devices 1.0 (1999; Mike Kent, Roland; Geert Knapen, Philips).
- https://www.usb.org/sites/default/files/DFU_1.1.pdf : USB Device Firmware Upgrade 1.1 (run-time vs DFU-mode protocol; functional descriptor).
- https://www.usb.org/hid : HID 1.11 class definition and HID Usage Tables 1.7.
- https://www.beyondlogic.org/usbnutshell/usb5.shtml : Craig Peacock's *USB in a NutShell*, descriptor fields.
- https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/usbview : USBView, where it ships, what it shows.
- https://raw.githubusercontent.com/microsoft/Windows-driver-samples/main/usb/usbview/uvcview.c : USBView source; `/saveall:`, `/savexml:`, `/f`, `/q` options.
- https://learn.microsoft.com/en-us/windows-hardware/drivers/install/standard-usb-identifiers : how Windows forms USB hardware and compatible IDs.
- https://www.uwe-sieber.de/usbtreeview_e.html : Uwe Sieber's UsbTreeView (freeware, portable).
- https://desowin.org/usbpcap/ and https://github.com/desowin/usbpcap : USBPcap (Tomasz Moń); licences, signed installers.
- https://wiki.wireshark.org/CaptureSetup/USB : USB capture on Windows and Linux; URBs, not bus packets.
- https://raw.githubusercontent.com/torvalds/linux/master/sound/usb/mixer_scarlett2.c : header records how Geoffrey D. Bennett learned the Scarlett protocol with usbmon (2018).
- https://github.com/geoffreybennett/alsa-scarlett-gui : Bennett's control panel (GPL-3.0-or-later); 2i2 4th Gen supported.
- https://librearts.org/2025/03/alsa-scarlett-gui-0-5/ : Aleksandr Prokudin (Libre Arts), 2025-03-04; Focusrite now supports Bennett.

**Logic analysers**
- https://sigrok.org/wiki/Main_Page : sigrok suite and licence.
- https://sigrok.org/wiki/Protocol_decoders : 131 decoders, stacking.
- https://sigrok.org/wiki/Sigrok-cli : command examples.
- https://sigrok.org/wiki/Downloads : release versions and Windows installers.
- https://sigrok.org/wiki/Fx2lafw : open FX2 firmware, clone warning.
- https://github.com/sigrokproject/sigrok-dumps : public-domain example captures (folder list read via the GitHub API).
- https://www.saleae.com/pages/downloads : Logic 2 platforms, MCP workflows.
- https://saleae.github.io/logic2-automation/ : Logic 2 gRPC automation API, Python wrapper.
- https://www.saleae.com/support/logic-software/capturing-data/what-sample-rate-is-required : 4x digital, 10x analogue guidance.
- https://www.flashrom.org/ : flashrom capabilities and safety warnings.

**Firmware**
- https://github.com/ReFirmLabs/binwalk and https://raw.githubusercontent.com/ReFirmLabs/binwalk/master/src/cliparser.rs : binwalk 3 (Rust, MIT) and its exact flags.
- https://cveawg.mitre.org/api/cve/CVE-2022-4510 : binwalk PFS path-traversal advisory (ONEKEY, 2023-01-25).
- https://unblob.org/ and https://unblob.org/installation/ : unblob (ONEKEY, MIT), installation and Docker usage.
- https://github.com/e-m-b-a/emba : EMBA (GPL-3.0), emulation-based firmware analyser.
- https://github.com/fkie-cad/FACT_core : FACT (Fraunhofer FKIE, GPL-3.0), firmware comparison.
- https://openwrt.org/about : OpenWrt, open firmware with source (practice answer key).

**Radio**
- https://www.rtl-sdr.com/about-rtl-sdr/ : RTL-SDR facts and history (Palosaari, Fry, Osmocom/Markgraf).
- https://pysdr.org/content/sampling.html : Marc Lichtman's PySDR on IQ sampling and the DC spike.
- https://greatscottgadgets.com/sdr/ : Michael Ossmann's SDR with HackRF course (CC BY).
- https://github.com/gnuradio/gnuradio : GNU Radio (GPL-3.0).
- https://github.com/ryanvolz/radioconda : radioconda; Windows installer; Zadig/WinUSB note.
- https://github.com/AlexandreRouma/SDRPlusPlus : SDR++ (GPL-3.0).
- https://github.com/miek/inspectrum : inspectrum (GPL-3.0), file formats.
- https://github.com/jopohl/urh : Universal Radio Hacker (GPL-3.0; WOOT'18; archived 2026-03-29).
- https://github.com/merbanan/rtl_433 and https://github.com/merbanan/rtl_433_tests : rtl_433 (GPL-2.0) and its test recordings.
- https://sigmf.org/ : SigMF recording metadata standard.
- https://www.fcc.gov/oet/ea/fccid : FCC ID search (automated fetch refused with 403; cited from general knowledge).

**Law (not legal advice)**
- https://www.law.cornell.edu/uscode/text/17/1201 : DMCA s.1201, including (f), (g), (i), (j).
- https://www.law.cornell.edu/cfr/text/37/201.40 : current s.1201 exemptions (repair (b)(15), security research (b)(18)), amended 2024-10-28.
- https://en.wikipedia.org/wiki/Sega_v._Accolade : 977 F.2d 1510 (9th Cir. 1992) summary (the primary opinion host refused automated fetch).
- https://en.wikipedia.org/wiki/Sony_Computer_Entertainment,_Inc._v._Connectix_Corp. : 203 F.3d 596 (9th Cir. 2000) summary.
- https://en.wikipedia.org/wiki/Chamberlain_Group,_Inc._v._Skylink_Technologies,_Inc. : 381 F.3d 1178 (Fed. Cir. 2004), nexus rule.
- https://en.wikipedia.org/wiki/Lexmark_International,_Inc._v._Static_Control_Components,_Inc. : 387 F.3d 522 (6th Cir. 2004), lock-out code.
- https://en.wikipedia.org/wiki/Bowers_v._Baystate_Technologies,_Inc. : 320 F.3d 1317 (Fed. Cir. 2003), EULA ban on reverse engineering enforced.
- https://en.wikipedia.org/wiki/Tetris_Holding,_LLC_v._Xio_Interactive,_Inc. : 863 F. Supp. 2d 394 (D.N.J. 2012), look and feel.
- https://www.law.cornell.edu/uscode/text/18/1839 : DTSA; reverse engineering is not improper means.
- https://www.legislation.gov.uk/eudr/2009/24/article/5 , /article/6 , /article/8 : EU Software Directive arts. 5, 6 and 8 (EUR-Lex refused automated reads).
- https://www.legislation.gov.uk/eudr/2016/943/article/3 : EU Trade Secrets Directive art. 3.
- https://www.legislation.gov.uk/ukpga/1988/48/section/50B : UK CDPA s.50B (with s.296A).
- https://laws-lois.justice.gc.ca/eng/acts/c-42/page-12.html : Canada Copyright Act ss.41.1, 41.12, 41.121.
- https://www.law.cornell.edu/uscode/text/18/2511 : ECPA interception offence and radio exceptions.
- https://www.law.cornell.edu/uscode/text/47/605 : unauthorised publication of communications.
- https://www.law.cornell.edu/cfr/text/47/15.5 : Part 15 general conditions.
- https://www.law.cornell.edu/cfr/text/47/2.944 : software-defined radio rule.
- https://www.legislation.gov.uk/ukpga/2006/36/section/48 : UK Wireless Telegraphy Act s.48.
- https://fsfe.org/activities/radiodirective/ : FSFE on the Radio Equipment Directive art. 3(3)(i).

**Host safety**
- https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-overview : Windows Sandbox; networking on by default, can be disabled.
- https://learn.microsoft.com/en-us/windows/wsl/wsl-config : `wsl.conf` automount and interop defaults, `.wslconfig` networking.

---

## Appendix A: `usb_midi_topology.py` (the seed of the `usb-descriptors` verb)

```python
"""Decode the KeyLab 88 mk3 USB-MIDI descriptors captured by USBView (2026-10-13)."""
MS_IFACE = ["07 24 01 00 01 61 00", "06 24 02 01 01 07", "06 24 02 02 02 00",
            "09 24 03 01 03 01 02 01 08", "09 24 03 02 04 01 01 01 00", "06 24 02 01 05 09",
            "06 24 02 02 06 00", "09 24 03 01 07 01 06 01 0A", "09 24 03 02 08 01 05 01 00"]
CS_EP = {0x02: "06 25 01 02 01 05", 0x81: "06 25 01 02 03 07"}
JACK_TYPE = {1: "EMBEDDED", 2: "EXTERNAL"}
b = lambda s: [int(x, 16) for x in s.split()]

for line in MS_IFACE:
    d = b(line)
    assert d[0] == len(d) and d[1] == 0x24              # bLength matches; CS_INTERFACE
    if d[2] == 0x01:
        print(f"MS_HEADER bcdMSC={d[4]:02X}.{d[3]:02X} wTotalLength={d[5] | d[6] << 8}")
    elif d[2] == 0x02:
        print(f"MIDI_IN_JACK  id={d[4]} {JACK_TYPE[d[3]]} iJack={d[5]}")
    elif d[2] == 0x03:
        n = d[5]
        print(f"MIDI_OUT_JACK id={d[4]} {JACK_TYPE[d[3]]} fed by {[d[6 + 2 * i] for i in range(n)]}"
              f" iJack={d[6 + 2 * n]}")
for ep, line in CS_EP.items():
    d = b(line)
    assert d[1] == 0x25 and d[2] == 0x01                # CS_ENDPOINT, MS_GENERAL
    for cable, jack in enumerate(d[4:4 + d[3]]):
        print(f"endpoint 0x{ep:02X} ({'to device' if ep < 0x80 else 'to host'}): cable {cable} = jack {jack}")
print("MS block:", sum(len(b(x)) for x in MS_IFACE) + 2 * (9 + 6), "bytes (header says 97)")

dfu = [0x09, 0x21, 0x0B, 0xFF, 0x00, 0x40, 0x00, 0x10, 0x01]   # USBView's "HID" fields, re-read
a = dfu[2]
print(f"DFU: canDnload={a & 1} canUpload={a >> 1 & 1} manifTolerant={a >> 2 & 1} willDetach={a >> 3 & 1}"
      f" detach={dfu[3] | dfu[4] << 8}ms xfer={dfu[5] | dfu[6] << 8}B bcdDFU=0x{dfu[7] | dfu[8] << 8:04X}")
print("config:", 9 * 6 + 97, "bytes (wTotalLength says 151)")
```

## Appendix B: `midi_wire_demo.py` (what a logic analyser sees)

```python
BAUD, FS = 31250, 1_000_000
SPB = FS // BAUD                                  # 32 samples per bit
msg = [0x90, 0x3C, 0x64]                          # Note On, ch 1, C4, velocity 100
line = [1] * (SPB * 4)                            # idle high
for byte in msg:                                  # start 0, 8 data bits LSB first, stop 1
    for bit in [0] + [(byte >> i) & 1 for i in range(8)] + [1]:
        line += [bit] * SPB
line += [1] * (SPB * 4)

decoded, i = [], 1
while i < len(line):
    if line[i - 1] == 1 and line[i] == 0:         # falling edge = start bit
        mid = i + SPB // 2                        # sample in the middle of each bit
        if line[mid] == 0:
            val = sum(line[mid + (k + 1) * SPB] << k for k in range(8))
            decoded.append((val, line[mid + 9 * SPB] == 1, i / FS * 1e6))
            i = mid + 9 * SPB
    i += 1
for val, stop_ok, t in decoded:
    print(f"t={t:7.1f} us byte=0x{val:02X} {'STATUS' if val & 0x80 else 'data'} stop ok={stop_ok}")
print("USB-MIDI packet:", " ".join(f"{x:02X}" for x in [(0 << 4) | (msg[0] >> 4)] + msg))
```

## Appendix C: `firmware_entropy_demo.py` (toy binwalk)

```python
import gzip, math, random, struct
random.seed(13)
WORDS = [b"note", b"velocity", b"curve", b"pad", b"fader", b"encoder", b"octave", b"chord",
         b"scale", b"arp", b"hold", b"transport", b"screen", b"led", b"bank", b"preset"]
text = b" ".join(random.choice(WORDS) + str(random.randrange(128)).encode() for _ in range(12000))
gz = gzip.compress(text, mtime=0)
rnd = bytes(random.getrandbits(8) for _ in range(8192))       # stands in for an encrypted blob
pad = b"\xFF" * 8192                                           # erased flash
cfg = b"device=toy-synth\nversion=1.5.0\nmidi_channel=1\n" * 60
hdr = (b"TOYF" + struct.pack("<IIII", 1, len(gz), len(rnd), len(cfg))).ljust(64, b"\x00")
image = hdr + gz + rnd + pad + cfg

SIGS = {b"TOYF": "toy header", b"\x1f\x8b\x08": "gzip", b"hsqs": "squashfs LE",
        b"\x7fELF": "ELF", b"\x27\x05\x19\x56": "U-Boot uImage", b"UBI#": "UBI"}
for magic, name in SIGS.items():
    pos = image.find(magic)
    while pos != -1:
        print(f"0x{pos:06X} {name}")
        pos = image.find(magic, pos + 1)

def entropy(block):
    n = len(block)
    counts = [block.count(bytes([v])) for v in range(256)]
    return max(0.0, -sum(c / n * math.log2(c / n) for c in counts if c))

for off in range(0, len(image), 4096):
    e = entropy(image[off:off + 4096])
    print(f"0x{off:06X} {e:4.2f} {'#' * round(e * 4)}")
```

(The scratchpad versions that produced HW-E4, HW-E10 and HW-E11 are slightly longer, with comments and
extra printing. These appendix versions keep the same logic.)
