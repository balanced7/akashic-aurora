"""arsenal.keylab -- talk to the physical Arturia KeyLab 88 mk3: trigger notes, light pads, drive the screen.

Why this exists: the mk3's pads, RGB LEDs and 320x480 screen are reachable over SysEx, but Arturia's own tooling
only exposes them through MCU/HUI DAW modes and a store/recall config dialog -- never "drop a sample on this pad,
paint it this colour, print this chord on the screen." The protocol is not a guess: it was read out of Arturia's
own FL Studio integration script (readable Python at
C:/Users/L5/Documents/Image-Line/FL Studio/Settings/Hardware/Arturia KeyLab mk3/) and cross-checked against the
device JSON + firmware strings. See protocol.py for the full provenance, and README.md for the verbs.

Two modules:
  protocol.py  -- pure byte-builders + enums (no I/O; the testable source of truth for the wire format)
  winmidi.py   -- WinMM output/input via ctypes, same idiom as arsenal.midiports (no external MIDI dependency)

Run it:  py -m arsenal.keylab <verb>     (e.g. ports, connect, led, pad, chord, bench, display)
"""
