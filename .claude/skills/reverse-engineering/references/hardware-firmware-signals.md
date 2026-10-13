# Hardware, firmware and signals — the operator's guide

The MIDI and USB devices we own, logic analysers and sigrok, firmware images (in a VM), software-defined
radio basics, and the legal limits. Distilled from
`research/reviewed/reverse-engineering-2026-10-13/hardware-firmware-signals.md` (the full report, with
the real KeyLab/Scarlett worked examples, the appendix scripts, and every source). **Not legal
advice**; the legal note is below, the full map in `method-legal-cleanroom.md`. Receive-only on radio,
never transmit; every driver install below is **Daniel's decision**.

**Never on the host:** "An untrusted sample (any file under study that the house did not build or record itself, unless Daniel has ruled that kind of file trusted) is never run, parsed, decoded or extracted on this machine: it is handled only inside a disposable VM or sandbox that is reverted afterwards, and it is kept outside the repo."

## The one-page version

1. **Hardware reverse engineering is mostly reading what the device already tells you.** A USB device
   hands the computer a full self-description on plug-in. A MIDI instrument answers a standard "who are
   you?". Vendors ship editor files and DAW scripts in readable form. **Read those first; sniff second;
   open firmware last, and only in a disposable VM.**
2. **A tool's label is an inference, not an observation.** Microsoft's USBView mislabelled the KeyLab's
   DFU firmware-update descriptor as "HID" (type `0x21` is reused across classes) and walked past the
   descriptor's end; re-reading the raw bytes against the DFU spec fixed it. Re-decode raw bytes.
3. **Two vendor files can disagree.** The KeyLab's FL script and Arturia's editor JSON disagree on how
   the device identifies itself over MIDI. Record both as an unknown; name the single harmless
   observation (one Identity Request, FL closed, Daniel's go) that settles it. Don't pick the newer one.
4. **The firmware file tells you things without being opened** (the USB revision `0x1500` lines up with
   the downloaded `1_5_0`; the `.confirm` "checksum" is a plain MD5 — integrity, not authenticity). A
   key-like vendor parameter next to the updater is exactly where an understanding playbook **stops**.
5. **Host safety is the binding constraint.** Untrusted firmware and captures are analysed only in a
   disposable Linux VM (networking off, no shared folders) — not the default WSL distro (it mounts C:/E:
   and launches Windows programs), not Docker Desktop (it hosts `akashic-redis`). Neither a VM nor
   Windows Sandbox is enabled today; **Daniel's decision:** enabling one.
6. **Legal shape in one breath:** understanding and interoperating with things we own is broadly
   protected (Sega, Connectix; EU arts. 5(3)/6/8; UK CDPA s.50B; Canada s.41.12). Breaking a technical
   lock is a separate question (DMCA §1201). Radio is its own world: receive your own devices, never
   intercept private traffic, never transmit without a licence.

## The layer cake (ask each tool only about the layer it can see)

```
meaning     "Daniel pressed middle C fairly hard"        <- docs, vendor files, judgement
messages    Note On, ch 1, note 60, velocity 100         <- MIDI monitor, sigrok 'midi' decoder
bytes       90 3C 64                                      <- MIDI monitor raw, USB capture payload
framing     UART 8N1 at 31,250 baud | USB-MIDI 4-byte pkt <- logic analyser + decoder | USB capture
electricity DIN current loop | USB D+/D- pair             <- logic analyser / oscilloscope
radio       a modulated carrier at some frequency         <- SDR
```

A logic analyser is a die photo of *time* on one wire; a MIDI monitor is a disassembler for the message
stream. Most mistakes come from asking a tool about a layer it cannot see.

## MIDI (the facts that matter)

Status bytes (top bit 1) then data bytes (0–127); channel messages carry the channel in the low nibble
(`9n` Note On, `Bn` Control Change…); real-time bytes (`F8` clock…) can appear anywhere (interrupts);
**running status** omits a repeated status byte (a parser that forgets this misreads note runs);
**SysEx** is the vendor's private channel (`F0`, a 1- or 3-byte manufacturer ID, 7-bit data, `F7`).
Universal **Identity Request** `F0 7E <device> 06 01 F7` → reply `F0 7E <device> 06 02 <mfr id>
<family 2B> <member 2B> <revision 4B> F7` (the CPUID of MIDI). **Seven-bit packing** (vendors split
8-bit data; Roland splits a byte into two nibbles) and **checksums** (one knob changing two bytes is
often a checksum) appear in any bulk dump. The wire is 31,250 baud, 8N1, LSB-first (a 3-byte note =
~0.96 ms). For our own experiments use SysEx ID `7D` (private, non-public); anything we release needs a
proper ID. Web MIDI treats SysEx as a stronger permission; the piano page asks `sysex: false`.

## USB (the facts that matter)

**Descriptors are the device's spec sheet,** handed over on plug-in: one device descriptor (VID, PID,
release `bcdDevice`, class), configurations, interfaces, endpoints, strings, class-specific descriptors.
Class `0x00` = per-interface; interfaces then say Audio (`0x01`), HID (`0x03`), DFU (`0xFE`), vendor
(`0xFF`). **USB-MIDI** is an Audio subclass with a MIDIStreaming interface whose jacks (embedded = USB
side, external = DIN) and 4-byte event packets (a cable number + a Code Index Number + up to 3 MIDI
bytes) describe the ports; cable numbers are how one pipe carries several "ports". Software sniffers
(USBPcap, usbmon) see requests (URBs), not bus handshakes (USBPcap installs a capture driver on the
host: **Daniel's decision**) — enough for protocol work; **start the
capture before plugging in** to catch enumeration, and filter to the target (a shared root hub leaks
keystrokes, i.e. passwords). **HID report descriptors** are the lawful map of every button and axis a
controller has (relevant to the future game). **DFU** (Device Firmware Upgrade) is the standard
firmware-update protocol; its functional descriptor is type `0x21` — the same type code as HID, which
is the trap in point 2 above.

## Logic analysers and sigrok

A logic analyser samples wires above/below a threshold at each tick (a 1-bit ADC per pin). **Sample at
least 4× the fastest digital rate** (Saleae's guidance; MIDI's 31.25 kbaud is trivial, but 12 Mbit/s
full-speed USB needs ~48 MHz, beyond common 24 MHz FX2 boards — so USB is a software-capture job).
**sigrok** (GPL-3.0): `sigrok-cli`/PulseView plus 131 stacking protocol decoders (`uart` → `midi`;
`usb_signalling` → `usb_packet` → `usb_request`; I2C, SPI, CAN, JTAG, SWD…). **fx2lafw** is open
firmware for cheap FX2 boards (buy one sold under its own name, not a clone shipping someone else's
software). Know the logic level and connect ground first; a 5-pin MIDI cable is a current loop, so probe
a logic-level point, not the DIN pins. On a board you own the usual finds are a UART console, an SPI
flash chip (`flashrom`, after a backup), and debug ports (JTAG/SWD); defeating read-out protection is
circumvention, out of scope.

## Firmware images (VM only)

A firmware image is nested boxes (header, compressed blobs, filesystems, bootloaders, sometimes
encrypted/signed sections, padding). **Signatures** mark formats (gzip `1F 8B 08`, ELF `7F 45 4C 46`,
U-Boot `27 05 19 56`, squashfs `hsqs`). **Entropy** (0–8 bits/byte): padding ~0, text/code ~4–6,
**compressed and encrypted both ~8 — entropy alone cannot tell them apart; a recognised header can.**
**binwalk 3** (MIT, Rust): `-E` entropy graph, `-e` extract, `-M` recurse, `-l` JSON log. **unblob**
(MIT, ONEKEY): chunk-accurate start/end, recursive extract, reports unknown chunks. Heavier tools
(EMBA, FACT) *emulate* — they run untrusted code and need a dedicated VM. **The extractor is attack
surface** (binwalk CVE-2022-4510 ran code on extraction), which is why this work is VM-only. **Stop at
encryption or signatures** — record "encrypted: contents unknown" as an honest finding; do not hunt for
keys. REA's firmware route (`inspect_firmware_regions`, `extract_firmware`) wraps caller-supplied
binwalk 3.1.x / unblob 26.6.x on Linux, enforces limits and records hashes/lineage with no execution —
a good fit *inside* the future VM.

## Software-defined radio (receive only)

An SDR digitises a slice of spectrum; software does the rest. **IQ samples** are complex pairs (N
samples/s shows N Hz of spectrum, centred on the tuned frequency); the **DC spike** at centre is the
receiver's own oscillator — tune slightly off. **RTL-SDR** (~$30, ~24–1766 MHz, receive only; it needs
a WinUSB driver via Zadig on the *right* device — a driver install, so **Daniel's decision**). Software: **SDR++** (look/record), **GNU Radio** (flowgraphs),
**inspectrum** (measure symbols), **Universal Radio Hacker** (demodulate, infer fields), **rtl_433**
(386 ISM sensor protocols, receive-only, `-r file.cu8` offline). Recordings need metadata (**SigMF**:
data type, sample rate, centre frequency). The lawful primary source for a US radio product is its
**FCC ID record** (frequency, power, test reports, internal photos). **Never transmit** (URH/HackRF can
"replay" — that is transmitting).

## The method (every playbook is a specialisation)

1. Write the question down and the evidence that answers it.
2. Inventory without touching (Plug-and-Play listing, device properties, installed vendor software,
   files already on disk; hash anything that might change).
3. Read what ships in readable form (manual + MIDI implementation chart, vendor DAW scripts, editor
   resource JSON, Linux drivers for the same family, public interoperability projects) — **this step
   alone answers most questions.**
4. Ask the device the standard questions (USB descriptors, passive; one MIDI Identity Request, with
   Daniel's go and nothing running).
5. Observe passively (a MIDI monitor while you press things; a USB capture only if needed).
6. Change one thing and diff (move one knob in the vendor editor, capture, compare; expect checksums
   and 7-bit packing).
7. Corroborate (two independent evidence types agree, or it stays an inference).
8. Ledger (O/I/U, evidence IDs, search boundaries); keep raw captures out of the repo.

## Routing table (hardware/firmware/signals)

| Artifact or question | First tool | Evidence | What it cannot tell you |
|---|---|---|---|
| "What's plugged in, which driver?" | `Get-PnpDevice` / `Get-PnpDeviceProperty` | VID, PID, revision, compatible IDs, driver | Interfaces a vendor driver hides; message formats |
| "What does this USB device say it is?" | USBView `/q /f /saveall:` (installed) or UsbTreeView | Device/config/interface/endpoint descriptors, strings | Runtime behaviour; which connectors exist; re-decode viewer labels |
| "How many MIDI ports, how wired?" | USBView + a USB-MIDI descriptor decode | Jack topology, cable→jack map, endpoint sizes | Port names unless string descriptors read; each port's protocol |
| "What messages when I touch it?" | MIDI monitor (Windows MIDI Services, MIDI-OX, ReceiveMIDI) | Timestamped messages, SysEx bytes | What another app sends *to* it; USB control traffic |
| "Who is this device / which firmware?" | Identity Request `F0 7E 7F 06 01 F7` (Daniel's go) | Manufacturer ID, family, member, revision | Vendor-specific behaviour; silent devices |
| "What does the vendor editor/script send?" | Read the vendor's shipped files first | Message wrappers, parameter IDs, auto-detect patterns | Whether the device behaves as the file claims; files can disagree |
| "Both directions of USB / vendor control" | USBPcap + Wireshark (driver and tool installs: **Daniel's decision**), or usbmon in a VM | URBs with payloads, enumeration, timing | Bus-level handshakes; payload meaning without diffing |
| "What's on this wire/header/pad?" | Multimeter, then logic analyser + sigrok | Edges, timing, decoded bytes | Analogue faults; anything faster than ~1/4 sample rate |
| "What's inside this firmware?" (VM) | binwalk / binwalk `-E`, then unblob | Signatures with offsets, entropy map, extracted tree with hashes | Encrypted/signed contents; behaviour (needs emulation) |
| "What changed between firmware versions?" (VM) | Hash+size diff, then unblob both and diff; FACT at scale | Changed files, strings, components | Why; anything inside encrypted parts |
| "Compressed or encrypted?" (trusted on host; untrusted → VM) | Signature scan **and** entropy together | Header → unpackable; no header + ~8 bits/byte → unknown | Entropy alone never answers it |
| "What is this radio device sending?" | Label/FCC ID, then SDR++ waterfall, `rtl_433`, inspectrum/URH | Frequency, modulation, symbol timing, decoded fields | Encrypted payloads; whether you may keep/decode others' traffic |
| "Can I legally do this?" | `method-legal-cleanroom.md`, then a lawyer beyond our own devices | Orientation by jurisdiction | Legal advice |

## Lessons (trigger-phrased)

- Use when any hardware behaviour is in question, before sniffing or capturing: read what the vendor
  ships in readable form (manuals, MIDI charts, DAW scripts, editor JSON) — it usually answers it.
  Don't when the shipped files disagree; then they are the question, and a runtime observation settles
  it.
- Use when a descriptor viewer or decoder labels a structure, before building on the label: re-decode
  the raw bytes against the class spec (`0x21` is both HID and DFU). Don't when no raw bytes are
  available — record the label as the tool's inference.
- Use when two sources disagree on an ID/version/format, before choosing either: log both as unknown
  and name the single observation that decides it. Don't when that observation would touch a device in
  use — schedule it.
- Use when you need both directions of USB or a vendor's control requests, before buying or wiring a
  logic analyser: capture at the USB stack (12 Mbit/s outruns 24 MHz analysers). Don't when a MIDI
  monitor already shows what you need.
- Use when a firmware region measures near 8 bits/byte, before calling it encrypted: look for a
  compression header. Don't when there is no header and a key-like vendor parameter sits nearby — stop,
  that is the circumvention boundary.
- Use before running binwalk/unblob/EMBA or any extractor on outside firmware or captures: move the
  sample into a disposable Linux VM with networking off and no shared folders (CVE-2022-4510). Don't
  when the only "sandbox" is the default WSL distro or Docker Desktop.
- Use when choosing a logic-analyser sample rate, before capturing: at least 4× the fastest digital
  rate (10× bandwidth for analogue), and measure the voltage and ground first. Don't when the target is
  mains-powered or its voltage is unknown.
- Use when receiving radio, before recording/decoding: keep to our own devices and public broadcasts,
  never cellular/cordless/encrypted/anything not meant for general reception, never transmit. Don't
  when a tool offers "replay" — that is transmitting.
- Use when a WinUSB driver swap with Zadig is proposed, before anything else: it is a driver install,
  so it is **Daniel's decision**; once he has ruled, confirm the VID and PID before clicking Install
  (replacing the KeyLab's or Scarlett's driver breaks it). Don't when the device already works with its
  vendor driver.
- Use when sending anything to an instrument, before sending more than an Identity Request: store a
  settings backup in the vendor editor, never send DFU/firmware messages, keep test SysEx on ID `7D`.
  Don't when another app is using the device or Daniel has not said go.
- Use when saving a USB/MIDI/radio capture, before it leaves the scratchpad/VM: filter it to the target
  and strip anything personal (same-hub keyboards leak keystrokes); never commit raw captures. Don't
  when it is a synthetic or public-domain teaching sample.

## Gaps (build proposals)

An analysis VM (the blocking gap; **Daniel's decision**); a `usb-descriptors` verb wrapping the installed
USBView and decoding USB-MIDI/DFU/HID/Audio, flagging where the viewer's label and the re-decode
disagree, serials redacted; a `midi-probe` verb (Identity Request + logged SysEx, an allow-list of
read-only queries); a device ledger file (ours-only, KeyLab 88 mk3 first); entry hardware (a
sigrok-supported logic analyser sold under its own name, an RTL-SDR); a USB-passthrough-to-VM capture
path; a recorded jurisdiction; a Saleae-MCP watch item.

## Legal note (not legal advice; US, EU and UK orientation, dated 2026-10-13)

In the **US**, studying a program to reach its unprotected ideas can be fair use (*Sega v.
Accolade*, 9th Cir. 1992; *Sony v. Connectix*, 9th Cir. 2000), but a EULA or terms of service can
forbid reverse engineering and be enforced (*Bowers v. Baystate*, Fed. Cir. 2003; *Davidson v.
Jung*, 8th Cir. 2005), and DMCA §1201 separately bans circumventing access controls; its exemptions
(§1201(f), (g), (j); 37 C.F.R. §201.40) excuse only the act, under their stated conditions, never
tools. In the **EU and UK**, a lawful user may observe, study and test a program (Directive
2009/24/EC art. 5(3); CDPA s.50BA) and decompile for interoperability within art. 6's limits (CDPA
s.50B), and contract terms against those rights are void (art. 8; CDPA s.296A). In **both**,
trade-secret law allows reverse engineering a lawfully obtained product unless a valid contract
forbids it (18 U.S.C. 1839(6)(B); Directive 2016/943 art. 3(1)(b)), and ideas, methods and observed
facts are free, while code, art, audio and text are protected and a distinctive look may be protected
(*Tetris Holding v. Xio*, D.N.J. 2012, including as trade dress; republishing a whole extracted table
is a separate question in
the EU, where a database right can apply). **For this domain:** signatures, encryption and read-out
protection on firmware are technological measures, so stop at them; sending a device anything beyond
a standard query needs Daniel's go. Radio is its own law: receive publicly accessible transmissions
from our own devices only, never intercept private, cellular or encrypted traffic (18 U.S.C. 2511;
UK Wireless Telegraphy Act 2006 s.48), and never transmit without a licence or outside a device's
certification. The full map with its caveats is `method-legal-cleanroom.md`; anything we ship that
leans on someone else's product goes past a lawyer first.

## Sources

Full report: `research/reviewed/reverse-engineering-2026-10-13/hardware-firmware-signals.md` (the
KeyLab/Scarlett worked examples HW-E1–E15, Appendices A–C, all sources). Specs and tools: USB-MIDI 1.0
and DFU 1.1 (usb.org), the MIDI Association message/ID tables, sigrok, fx2lafw, USBView (Microsoft),
UsbTreeView (Uwe Sieber), USBPcap (Tomasz Moń), binwalk (ReFirmLabs), unblob (ONEKEY), EMBA, FACT, RTL-SDR,
SDR++, GNU Radio, inspectrum, URH, rtl_433, SigMF, and the Geoffrey D. Bennett Scarlett precedent (the
Linux kernel's `mixer_scarlett2.c`). Discipline credited to **morluto/rea** (whose own firmware,
packet, pcap and signal-decoder routes are the clean fit if that Linux machinery is adopted in the VM).
