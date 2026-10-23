"""Live chord viewer on the KeyLab itself: play the keys -> the chord name shows on the LCD and its notes
light up on the pads. Reads the keybed MIDI (the 'MIDI' input port), names the chord, draws the screen + pads.

Everything converges here: winmidi.MidiIn (read keys) + theory.name_chord + protocol screen + ledframe PadRenderer.
"""
from __future__ import annotations

import time
from typing import Optional

from . import protocol as P
from . import winmidi as W
from .theory import name_chord, analyze

PAD_PC = {pad: P.PAD_NOTE[pad] % 12 for pad in range(1, 13)}  # the pitch-class each pad represents

# Colours live OUTSIDE the wash zone. On this device warm low-saturation colours (amber, yellow, orange, lime) come
# out close to white (README "Confirmed facts"), and the root is white, so a gold third was indistinguishable from
# the root. Every non-white colour below has a hue outside 15-100 degrees (pinned in tests/test_keylab_w0.py).
# The LED gamut probe (A16 W0 d) will replace these hand-picked values with a measured LED-safe table.
#
# interval-from-root -> colour: the "harmonic role" of each chord tone
ROLE_COLORS = {0: (255, 255, 255),   # root: white
               1: (255, 0, 120),     # b9: pink
               2: (150, 0, 255),     # 9: purple
               3: (255, 0, 255),     # minor 3rd: magenta
               4: (255, 0, 0),       # major 3rd: red
               5: (0, 210, 160),     # 4th / 11: teal
               6: (255, 40, 0),      # tritone: red-orange
               7: (0, 120, 255),     # 5th: blue
               8: (255, 0, 170),     # #5 / b6: rose
               9: (0, 255, 255),     # 6th / 13: cyan
               10: (0, 220, 90),     # minor 7th: green
               11: (0, 255, 130)}    # major 7th: spring green
# chord quality -> one mood colour (the major family is red/rose now; it was amber, which washed to white)
QUALITY_COLORS = {"": (255, 0, 0), "maj7": (255, 0, 80), "maj9": (255, 0, 80), "6": (255, 0, 40),
                  "add9": (255, 0, 60),
                  "m": (0, 90, 255), "m7": (0, 120, 220), "m9": (0, 120, 220), "m6": (0, 140, 200),
                  "madd9": (0, 120, 220), "m7b5": (90, 0, 220), "dim": (150, 0, 200), "dim7": (120, 0, 210),
                  "aug": (255, 0, 255), "7": (0, 200, 80), "9": (0, 200, 80), "7sus4": (0, 200, 120),
                  "sus2": (0, 200, 180), "sus4": (0, 200, 180), "5": (0, 255, 255)}


# Physical pad grid, 4 across x 3 down in reading order (the one copy lives in protocol.GRID; Daniel at the device,
# 2026-10-23, correcting the sideways 2026-10-22 reading):
#     1  2  3  4      top row, farthest from the player
#     5  6  7  8
#     9 10 11 12      bottom row, nearest the player
GRID = P.GRID
TOP_ROW = set(GRID[0])                                                    # {1, 2, 3, 4}
BORDER = set(GRID[0]) | set(GRID[-1]) | {r[0] for r in GRID} | {r[-1] for r in GRID}   # all but pads 6, 7


def pad_colors(sounding, root, quality, scheme, base):
    """12 pad colours for the sounding notes under a scheme: notes | roles | quality | split | frame."""
    pcs = {n % 12 for n in sounding}
    qcol = QUALITY_COLORS.get(quality or "", (255, 255, 255)) if root is not None else (40, 40, 40)

    def note(pad, roles):
        pc = PAD_PC[pad]
        if pc not in pcs:
            return (0, 0, 0)
        if pc == root:
            return (255, 255, 255)                       # root always white
        if roles and root is not None:
            return ROLE_COLORS.get((pc - root) % 12, (120, 120, 120))
        return base

    out = []
    for pad in range(1, 13):
        if scheme == "roles":
            out.append(note(pad, True))
        elif scheme == "quality":
            pc = PAD_PC[pad]
            out.append((0, 0, 0) if pc not in pcs else ((255, 255, 255) if pc == root else qcol))
        elif scheme == "split":
            out.append(qcol if pad in TOP_ROW else note(pad, True))
        elif scheme == "frame":
            out.append(qcol if pad in BORDER else note(pad, True))
        else:  # notes
            out.append(note(pad, False))
    return out


class Voicing:
    """Which notes are sounding: held keys plus notes the sustain pedal (CC 64) is holding. Pure, so it is pinned
    without hardware (tests/test_keylab_w0.py)."""

    def __init__(self):
        self.down, self.sustained, self.pedal = set(), set(), False

    def feed(self, status: int, d1: int, d2: int) -> None:
        kind = status & 0xF0
        if kind == 0x90 and d2 > 0:
            self.down.add(d1); self.sustained.discard(d1)
        elif kind == 0x80 or (kind == 0x90 and d2 == 0):
            self.down.discard(d1)
            if self.pedal:
                self.sustained.add(d1)             # the pedal holds the note past key release
        elif kind == 0xB0 and d1 == 64:            # CC 64 = sustain pedal
            self.pedal = d2 >= 64
            if not self.pedal:
                self.sustained.clear()             # pedal up -> release the sustained notes

    @property
    def sounding(self) -> set:
        return self.down | self.sustained


def run(secs: Optional[float] = None, keys_port: Optional[str] = None, led_port: Optional[str] = None,
        chord_color=(0, 200, 160), scheme: str = "roles", sound: bool = False) -> int:
    from .ledframe import PadRenderer

    listener = W.MidiIn(port=keys_port, prefer="midi")   # the keybed sends notes on the MIDI port
    out = W.MidiOut(led_port, prefer="daw")              # LEDs + screen live on the DAW port
    out.send_sysex(P.daw_connect(True)); time.sleep(0.2)
    render = PadRenderer(out, bank="DAW")
    synth = None
    if sound:
        try:
            synth = W.MidiOut(port="wavetable")          # Microsoft GS Wavetable Synth -> you hear what you play
            print("sound: forwarding your notes to the Windows GS Wavetable synth")
        except Exception as exc:
            print(f"(no synth available: {exc})")

    voicing = Voicing()
    last = object()  # sentinel so the first state always draws
    out.send_sysex(P.screen_full2("CHORD", "play...", color1=chord_color, color2=(160, 160, 160)))
    listener.start()
    print(f"chordview on {listener.name} -- play the keys (Ctrl-C or --secs to stop)")
    try:
        end = (time.perf_counter() + secs) if secs else None
        while end is None or time.perf_counter() < end:
            while listener.events:
                _t, data, kind = listener.events.pop(0)
                if kind != "short" or len(data) < 3:
                    continue
                if synth is not None:
                    synth.send_short(data[0], data[1], data[2])   # play it so you hear it
                voicing.feed(data[0], data[1], data[2])
            sounding = voicing.sounding
            name, root, qual = analyze(sorted(sounding)) if sounding else (None, None, None)
            if name != last:
                last = name
                if name:
                    out.send_sysex(P.screen_full2("CHORD", name, color1=chord_color, color2=(255, 255, 255)))
                    render.set_frame(pad_colors(sounding, root, qual, scheme, chord_color))
                    print(f"  {name}")
                else:
                    out.send_sysex(P.screen_full2("CHORD", "play...", color1=chord_color, color2=(160, 160, 160)))
                    render.clear()
            time.sleep(0.015)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            render.clear()
            out.send_sysex(P.daw_connect(False))
        except Exception:
            pass
        listener.close(); out.close()
        if synth is not None:
            synth.close()
    print("chordview done")
    return 0
