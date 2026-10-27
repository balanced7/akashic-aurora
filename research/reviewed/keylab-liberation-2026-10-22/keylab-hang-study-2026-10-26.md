# KeyLab 88 mk3: a USB-MIDI hang caught live, and the liveness probe that detects it (2026-10-26)

Vandor (claude) and Daniel at the device, late evening of 2026-10-26, after Rill (dsh_agent) reported that no pad colour write had
ever appeared (bus note event:events:raw:1793066127333-0). Daniel asked: "can you see if you can render something to the pads so
we can better understand the protocols in play and their troubleshooting", and, once it looked stuck: "I am thinking this would be
good as a diagnostic and debugging test too, to understand hang conditions and recovery paths". Every observation of the device
below is Daniel's eyes, in his words where quoted; every byte is from our own tools (arsenal/keylab, and the scratch probes named).

## The answer for Rill

His writes were correct. The ids (DAW bank 82-93), the packet (`[0x00, 0x02, 0x03, id, R, G, B, 0x00]`, request byte 0x00), the DAW
handshake (`00 02 05 01`), the port ("KeyLab 88 mk3 DAW") and the physical mode (Prog, the middle option, DAW) were all right. **The
KeyLab itself was hung**: it accepted nothing from the computer and sent nothing back, while its screen kept its last frame. A power
cycle cleared it, and the very first single write afterwards landed (pad 1 blue).

## What we saw, in order

| Time | Test | Result |
|---|---|---|
| ~23:15 | `keylab all magenta` (the 2026-10-22 known-good path) | nothing visible |
| 23:20-23:21 | a 7-step test card: off; pad 1 red; a 12-colour grid; the request-byte trap; bank A; a walking dot; all magenta | Daniel: "pads are dark same with screen" |
| 23:22 | Device Inquiry `F0 7E 7F 06 01 F7` out of both ports, both inputs captured 4 s, device untouched | no reply, no events |
| 23:23 | Daniel pressed a key, then pad 1, during a 60 s capture with an inquiry every 5 s | the device woke: "chord still dbadd9 pads all lit white"; the capture recorded **0 events** (not even his key) and no reply |
| 23:24 | `all magenta` while awake | "no magenta" |
| 23:26 | a screen popup from our CLI ("HELLO DANIEL / test 1 of 2"), then Play red, Stop green, Record blue (button LEDs) | "nothing on all of them, prog 2 selected" |
| 23:29 | an A/B of our port handling: pad 1 red with the port held open 3 s; pad 2 green closed WITHOUT `midiOutReset`; pad 3 blue closed the usual way | "pads are still all white still dbadd9" -- none landed |
| ~23:31 | Daniel power-cycled the KeyLab | "now the pads are a gradient from yellow to red" (no host process had written in the previous 40 minutes) |
| 23:33 | ONE DAW connect + `led 82 blue` from one short-lived CLI process | "pad 1 blue, screen backlight lit but screen black" |
| 23:34 | 20 s capture with an inquiry every 5 s; Daniel pressed pad 1 | identity replies at 0, 5, 10 and 15 s (`F0 7E 7F 06 02 ...`); pad 1 arrived as `99 00 7F` (note-on, channel 10, note 0) followed by its pressure sweep (`A0 00 49` ... `A0 00 61` ... `A0 00 56`) |
| ~23:35 | Daniel opened FL and played: "it works!" | -- |

## What it tells us

1. **The hang signature (new; not the 2026-10-22 burst freeze).** The screen holds its last frame and still sleeps and wakes on
   a key press; the pads show their resting white; the device takes NO host SysEx (pads, buttons, screen) and sends NOTHING (no
   notes, no identity reply). The 2026-10-22 burst freeze was different: a black screen that ignored the buttons.
2. **Not our port handling.** Holding the port open and skipping `midiOutReset` changed nothing during the hang, and a plain
   short-lived CLI write worked at once after the power cycle. (`MidiOut.send_sysex`'s silent 1 s done-flag timeout and the
   reset-on-close are still worth hardening: a wait that times out should say so.)
3. **Not sleep alone.** Writes failed while it was awake too. But it does sleep: the screen service re-sent a frame every 2 s and
   the device still went dark, so host SysEx does not count as activity; only a touch wakes it.
4. **Recovery path:** a power cycle. Side effect: the long-lived screen service (`keylab screen --live --pulse --reassert 2`) died
   when its port vanished, so after a KeyLab reboot every long-lived holder of its port must be restarted.
5. **Liveness detector:** a healthy KeyLab answers the Device Inquiry within the capture window, every time we asked; a hung one
   answered none. Ask every few minutes; silence means hung. Our `winmidi.MidiIn` capture is now confirmed on hardware (its
   docstring said "treat as needs-hardware until confirmed").
6. **Open:** what causes the hang (candidates: long uptime with a frame re-sent every 2 s for days, many short-lived writers on
   one port, LED-id sweeps, sleep/wake cycles, the Windows MIDI service in the path); the identity reply's payload printed as zeros
   after `06 02` (a capture detail to check: a healthy reply should carry Arturia's ID `00 20 6B`); and the boot-time yellow-to-red
   pad gradient (the device's own resting state after power-up, not a write).

## After recovery: drawing alongside FL (2026-10-27, 00:36-00:37)

With FL open (started 23:31, its script holding DAW mode) and no DAW connect from us (`--no-connect` on every call):
- **Liveness:** the KeyLab answered the Device Inquiry on both ports.
- **Pads:** a 12-colour grid on ids 82-93 landed exactly. Daniel: "red green blue white, pink, light blue, yellow, orange then a
  gradiant of white". Yellow and orange read as distinct colours this time (the 2026-10-22 note said warm colours came out
  near-white).
- **Screen:** a full-screen two-line message landed and stayed. Daniel: "screen says hellow message".
- **So:** with FL open, draw onto the session FL's script opened, through the toolkit's CLI with `--no-connect`; never send a DAW
  connect or disconnect while FL runs. Daniel's other answers: the KeyLab runs on USB power from the PC (so a cable replug equals a
  power cycle); firmware 1.5.0; he thinks the keys made sound in FL between 21:25 and 21:50 (which would make the hang one-sided:
  the keys port alive while the DAW port was stuck).

## Corrections (2026-10-27, from keylab-dev-guidance-and-hang-guide-2026-10-27.md)

- **The onset was earlier.** The hang began before about 21:18 on 2026-10-26: Rill's 21:18 note already says pad SysEx does not
  land, and the screen showed the same frozen "Dbadd9" frame at about 21:20. So every probe that evening, Rill's and ours, ran on a
  device that was already hung; none of them caused it. The trigger lies earlier: FL had been open without a break from 2026-10-24
  10:05 to about 21:05 on 10-26 while the screen service re-sent frames, and the KeyLab had run about 4 days 15 hours since power-on.
- **Switching programs was tried during the hang** (Prog to Arturia and back to DAW): the pads went to their resting white and the
  hang stayed.
- **The zeros in the identity reply were our capture code's**, not the device's: `winmidi.MIDIHDR.lpData` is a `c_char_p`, which
  stops at the first `00` byte, and Arturia's maker ID begins with `00`. The replies were 17 bytes long, the standard length.
- **The burst governor is per process, not per port** (each `MidiOut` makes its own), so the README's "shared by every producer on
  the port" overstates it.

## Next

- A `keylab doctor` verb: ports, the Windows MIDI service, the Device Inquiry liveness check, the device's recent input, and the
  recovery steps (wake with a key; power-cycle a hang; restart the long-lived port holders afterwards).
- A watchdog option for the long-lived services: probe liveness every few minutes and say "the KeyLab stopped answering" instead of
  painting into the void.
- The scratch probes that produced this: `keylab_testcard.py`, `keylab_liveness.py` (Vandor's session scratchpad).
