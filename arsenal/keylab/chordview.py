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

# interval-from-root -> colour: the "harmonic role" of each chord tone
ROLE_COLORS = {0: (255, 255, 255), 1: (255, 0, 120), 2: (150, 0, 255), 3: (255, 150, 0), 4: (255, 200, 0),
               5: (0, 210, 160), 6: (255, 40, 0), 7: (0, 160, 255), 8: (255, 0, 200), 9: (150, 255, 0),
               10: (0, 220, 90), 11: (0, 255, 130)}
# chord quality -> one mood colour
QUALITY_COLORS = {"": (255, 180, 0), "maj7": (255, 150, 40), "maj9": (255, 150, 40), "6": (255, 200, 0),
                  "m": (0, 90, 255), "m7": (0, 120, 220), "m9": (0, 120, 220), "m6": (0, 140, 200),
                  "madd9": (0, 120, 220), "m7b5": (90, 0, 220), "dim": (150, 0, 200), "dim7": (120, 0, 210),
                  "aug": (255, 40, 0), "7": (0, 200, 80), "9": (0, 200, 80), "7sus4": (0, 200, 120),
                  "sus2": (0, 200, 180), "sus4": (0, 200, 180), "add9": (255, 120, 0), "5": (200, 200, 200)}


# Physical pad grid, 3 across x 4 down, as printed on the unit. Confirmed 2026-10-22 from Daniel's photo of the
# 12-colour test (pad n lit COLORS[n-1]: left column came up blue/purple/magenta/pink = pads 9-12, right column
# red/orange/amber/yellow = pads 1-4):
#     9  5  1
#    10  6  2
#    11  7  3
#    12  8  4
GRID = [[9, 5, 1], [10, 6, 2], [11, 7, 3], [12, 8, 4]]
TOP_ROW = set(GRID[0])                                                    # {9, 5, 1}
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

    down, sustained, pedal = set(), set(), False
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
                status, d1, d2 = data[0] & 0xF0, data[1], data[2]
                if status == 0x90 and d2 > 0:
                    down.add(d1); sustained.discard(d1)
                elif status == 0x80 or (status == 0x90 and d2 == 0):
                    down.discard(d1)
                    if pedal:
                        sustained.add(d1)             # sustain pedal holds the note past key release
                elif status == 0xB0 and d1 == 64:     # CC 64 = sustain pedal
                    pedal = d2 >= 64
                    if not pedal:
                        sustained.clear()             # pedal up -> release the sustained notes
            sounding = down | sustained
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
