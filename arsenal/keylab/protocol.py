"""The KeyLab mk3 DAW-integration wire format -- pure byte builders, no I/O.

PROVENANCE (not reverse-engineered from scratch -- read from Arturia's own shipping code):
  C:/Users/L5/Documents/Image-Line/FL Studio/Settings/Hardware/Arturia KeyLab mk3/
    KL3Dispatch.py:66    the SysEx envelope: midiOutSysex(F0 00 20 6B 7F 42 <payload> F7)
    KL3Connexion.py      the DAW-mode handshake (eConnection)
    KL3Return.py:208     live per-pad RGB:  [req, eDaw, eSetLed, padLedId, R, G, B, 0x00]
    LedId.py             the LED/pad id map (buttons 0-33, pads 34-93 across banks A/B/C/D/Daw)
    ParamId.py           eParamId enum        IntegrationPatchId.py  eIntegrationPatchId enum
  Cross-checked: device JSON KeyLab3 88.json (protocol "arturia_v4", productId 42) and firmware
  KeyLab3_FW_*.kl3 (same F0 00 20 6B 7F 42 header parsed inbound for the screen).

Everything here is bytes math. It is correct or not independently of any keyboard being plugged in,
so selftest() can prove it offline.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

# --- the SysEx envelope ---------------------------------------------------------------------------
HEADER = bytes([0xF0, 0x00, 0x20, 0x6B, 0x7F, 0x42])  # F0 | Arturia 00 20 6B | device 7F 42
EOX = 0xF7


class Ctx:            # eIntegrationPatchId  (IntegrationPatchId.py)
    ARTURIA = 1
    DAW = 2
    VCOL = 13


class Param:          # eParamId  (ParamId.py)
    PROPERTIES = 0
    VALUE = 1
    STRING = 2
    SET_LED = 3
    DISPLAY = 4
    CONNECTION = 5
    BANK = 6
    PROGRAM = 7
    SOFT_CONNECTION = 8


# The first payload byte. CONFIRMED ON HARDWARE 2026-10-22: 0x00 renders real RGB on the DAW-bank pads
# (matches the FL init() which lights every pad/button with 0x00); 0x02 lit pads but came out WHITE
# (colour ignored). So LED colour commands use 0x00. REQ_LED (0x02) is kept only for bench probing.
REQ_CTRL = 0x00   # control/handshake AND the working LED-colour request byte
REQ_LED = 0x02    # the KL3Return.py:209 variant -- showed white on hardware; probe-only

# --- LED / pad ids  (LedId.py, eLedId) -----------------------------------------------------------
BUTTONS = {
    "hold": 0, "chord": 1, "scale": 2, "arp": 3, "tap": 4, "record": 5, "play": 6, "stop": 7,
    "repeat": 8, "backward": 9, "forward": 10, "metronome": 11, "redo": 12, "undo": 13,
    "quantize": 14, "save": 15, "bankp": 16, "bankm": 17, "settings": 18, "prog": 19, "midi": 20,
    "ctx1": 21, "ctx2": 22, "ctx3": 23, "ctx4": 24, "ctx5": 25, "ctx6": 26, "ctx7": 27, "ctx8": 28,
    "back": 29, "transm": 30, "transp": 31, "octm": 32, "octp": 33,
}
_PAD_BANK_BASE = {"A": 34, "B": 46, "C": 58, "D": 70, "DAW": 82}  # 12 pads each


def pad_led(n: int, bank: str = "A") -> int:
    """LED id of pad n (1..12) in a bank. ePad1BankA == 34."""
    bank = bank.upper()
    if bank not in _PAD_BANK_BASE:
        raise ValueError(f"bank must be one of {list(_PAD_BANK_BASE)}, got {bank!r}")
    if not 1 <= n <= 12:
        raise ValueError(f"pad must be 1..12, got {n}")
    return _PAD_BANK_BASE[bank] + (n - 1)


def led_id(target: str) -> int:
    """Resolve a target to an LED id: a button name ('play'), a pad ('A1'..'D12'), or a raw int."""
    t = target.strip().lower()
    if t.isdigit():
        return int(t)
    if t in BUTTONS:
        return BUTTONS[t]
    if len(t) >= 2 and t[0] in "abcd" and t[1:].isdigit():
        return pad_led(int(t[1:]), t[0].upper())
    raise ValueError(f"unknown LED target {target!r} (try A1..D12, a button like 'play', or an id 0..93)")


# --- pad MIDI notes  (Default.keylab388, MPC layout, channel 10) ---------------------------------
PAD_CHANNEL = 10
# bank A default notes: pads 1-4 = 44-47, 5-8 = 40-43, 9-12 = 36-39
PAD_NOTE = {1: 44, 2: 45, 3: 46, 4: 47, 5: 40, 6: 41, 7: 42, 8: 43, 9: 36, 10: 37, 11: 38, 12: 39}
_NOTE_PAD = {note: pad for pad, note in PAD_NOTE.items()}

# The physical grid: 4 across x 3 down, numbered in reading order, rows listed top (farthest from the player) to
# bottom (nearest). The ONE copy: chordview imports it, and the page's mirror (arsenal/web/lib/keylab-client.js
# PAD_GRID) is pinned equal to it by tests/test_keylab_w0.py.
#     1  2  3  4
#     5  6  7  8
#     9 10 11 12
# Daniel, 2026-10-23, at the device: "your pad representation shows pad 1 on the right when its actually the top left
# most pad, and itr goes to 4, then row 2 is 5-8 and bottom row is 9-12 ^__^!"
# The grid recorded on 2026-10-22 ([[9, 5, 1], [10, 6, 2], [11, 7, 3], [12, 8, 4]], "3 across x 4 down", from his
# photo of the 12-colour test) was this layout rotated 90 degrees: the photo was read sideways, its rows taken as
# columns. Pad numbers, LED ids and notes were never affected; only where a pad sits was.
# It agrees with PAD_NOTE's MPC rows: each row's notes ascend left to right, each row sits 4 semitones above the one
# below it, and the bottom-left pad (9) plays the lowest note, 36.
GRID = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]


def pad_for_pitchclass(pc: int) -> int:
    """Which pad (1..12) plays pitch-class pc (0=C..11=B), per the default note map. 36..47 covers all 12."""
    for note, pad in _NOTE_PAD.items():
        if note % 12 == pc % 12:
            return pad
    raise ValueError(pc)  # unreachable: 36..47 spans a full octave


# --- colour ---------------------------------------------------------------------------------------
NAMED = {
    "off": (0, 0, 0), "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
    "green": (0, 255, 0), "blue": (0, 0, 255), "yellow": (255, 230, 0), "orange": (255, 90, 0),
    "cyan": (0, 255, 255), "magenta": (255, 0, 255), "purple": (150, 0, 255), "pink": (255, 40, 120),
    "lime": (160, 255, 0), "teal": (0, 200, 160), "amber": (255, 160, 0), "dim": (26, 26, 26),
}


def to7(v: int) -> int:
    """8-bit (0..255) colour channel to MIDI 7-bit (0..127), rounded."""
    v = max(0, min(255, int(v)))
    return (v * 127 + 127) // 255


def parse_color(s) -> Tuple[int, int, int]:
    """'red' | '#ff0040' | 'ff0040' | '255,0,64' | '255 0 64'  ->  (r,g,b) in 0..255."""
    if isinstance(s, (tuple, list)) and len(s) == 3:
        return tuple(int(x) for x in s)  # type: ignore
    t = str(s).strip().lower()
    if t in NAMED:
        return NAMED[t]
    if t.startswith("#"):
        t = t[1:]
    if len(t) == 6 and all(c in "0123456789abcdef" for c in t):
        return (int(t[0:2], 16), int(t[2:4], 16), int(t[4:6], 16))
    parts = t.replace(",", " ").split()
    if len(parts) == 3:
        return tuple(max(0, min(255, int(p))) for p in parts)  # type: ignore
    raise ValueError(f"cannot parse colour {s!r} (try a name, #rrggbb, or 'r,g,b')")


def hue(i: int, n: int) -> Tuple[int, int, int]:
    """8-bit RGB for the i-th of n evenly spaced hues (for rainbow sweeps). No external deps."""
    h = (i % n) / float(n) * 6.0
    x = int(255 * (1 - abs(h % 2 - 1)))
    c = 255
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][int(h) % 6]
    return (r, g, b)


# --- chords  (name or note list -> pitch classes) ------------------------------------------------
_PC = {"c": 0, "c#": 1, "db": 1, "d": 2, "d#": 3, "eb": 3, "e": 4, "f": 5, "f#": 6, "gb": 6,
       "g": 7, "g#": 8, "ab": 8, "a": 9, "a#": 10, "bb": 10, "b": 11}
_QUAL = {  # intervals from the root
    "": (0, 4, 7), "maj": (0, 4, 7), "major": (0, 4, 7), "m": (0, 3, 7), "min": (0, 3, 7),
    "minor": (0, 3, 7), "dim": (0, 3, 6), "aug": (0, 4, 8), "sus2": (0, 2, 7), "sus4": (0, 5, 7),
    "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10), "min7": (0, 3, 7, 10),
    "dim7": (0, 3, 6, 9), "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9), "9": (0, 4, 7, 10, 14),
    "add9": (0, 4, 7, 14),
}


def chord_pitchclasses(spec: str) -> Tuple[List[int], int]:
    """'Cmaj7' / 'F#m' / 'C E G' / '60 64 67'  ->  (sorted unique pitch-classes, root pc). root=-1 if a bare list."""
    spec = spec.strip()
    toks = spec.replace(",", " ").split()
    if len(toks) > 1 or (toks and (toks[0].isdigit() or toks[0].lower() not in _PC and _root_split(toks[0]) is None)):
        pcs = []
        for tok in toks:
            if tok.isdigit():
                pcs.append(int(tok) % 12)
            elif tok.lower() in _PC:
                pcs.append(_PC[tok.lower()])
            else:
                raise ValueError(f"not a note: {tok!r}")
        return sorted(set(pcs)), (pcs[0] if pcs else -1)
    split = _root_split(spec)
    if split is None:
        raise ValueError(f"cannot parse chord {spec!r}")
    root, qual = split
    if qual not in _QUAL:
        raise ValueError(f"unknown chord quality {qual!r} (have: {', '.join(k for k in _QUAL if k)})")
    root_pc = _PC[root]
    pcs = sorted({(root_pc + iv) % 12 for iv in _QUAL[qual]})
    return pcs, root_pc


def _root_split(s: str):
    """Split 'C#maj7' -> ('c#','maj7'); returns None if the head is not a note name."""
    s = s.strip()
    for root_len in (2, 1):
        head = s[:root_len].lower()
        if head in _PC:
            return head, s[root_len:].lower()
    return None


# --- message builders ----------------------------------------------------------------------------
def sysex(payload: Iterable[int]) -> bytes:
    """Wrap a payload in the KeyLab envelope. Payload bytes must be 0..127 (SysEx data range)."""
    body = bytes(payload)
    for b in body:
        if not 0 <= b <= 127:
            raise ValueError(f"SysEx payload byte out of range 0..127: {b}")
    return HEADER + body + bytes([EOX])


def daw_connect(on: bool = True, ctx: int = Ctx.DAW) -> bytes:
    """Arm (or drop) DAW-integration mode -- the gate that makes LED/screen commands land."""
    return sysex([REQ_CTRL, ctx, Param.CONNECTION, 1 if on else 0])


def set_led(target, color, req: int = REQ_CTRL, ctx: int = Ctx.DAW) -> bytes:
    """Light one LED/pad. target: id|'A1'|'play'. color: name|#hex|(r,g,b) in 8-bit (converted to 7-bit)."""
    lid = target if isinstance(target, int) else led_id(str(target))
    r, g, b = parse_color(color)
    return sysex([req, ctx, Param.SET_LED, lid, to7(r), to7(g), to7(b), 0x00])


def note(n: int, velocity: int = 100, channel: int = PAD_CHANNEL, on: bool = True) -> Tuple[int, int, int]:
    """A Note On/Off as a (status, data1, data2) short message. velocity 0 or on=False -> Note Off."""
    status = (0x90 if (on and velocity > 0) else 0x80) | ((channel - 1) & 0x0F)
    return (status, n & 0x7F, (velocity if on else 0) & 0x7F)


# Screen text is EXPERIMENTAL: the device parses an inbound "SysEx42 Display" (firmware-confirmed) but the
# exact payload grammar is not yet mapped. This is a plausible first attempt to capture/iterate on the bench.
def display_text(text: str, screen_id: int = 23, req: int = REQ_CTRL, ctx: int = Ctx.DAW) -> bytes:
    """EXPERIMENTAL screen push. screen_id 23 == eScreenPopup1L. Grammar unconfirmed -- for bench probing only."""
    data = [req, ctx, Param.DISPLAY, screen_id & 0x7F]
    for ch in text:
        data.append(ord(ch) & 0x7F)  # ASCII only, 7-bit
    data.append(0x00)
    return sysex(data)


# --- screen / LCD (eDisplay) -- grammar read verbatim from the FL script KL3Display.py ------------
# Base = [0x00, Ctx.DAW(2), Param.DISPLAY(4)] then a screenId byte, then tagged null-terminated fields:
#   line  = [tag] + ascii(<=32 chars, 32..126) + [0x00]
#   ctype = [tag] + [colortype] + [0x00]           (colortype 1 = use the custom RGB that follows)
#   color = [tag] + [r, g, b] (0..127) + [0x00]
# NOTE (2026-10-23): the builders below differ from the script in two ways -- a line over 32 characters is cut to
# 29 + "..." here (the script: 28 + "..."), and line 2 is NOT upper-cased here (the script upper-cases it). They are
# kept as they are because chordview and probe rely on them (a chord name on line 2 stays "Am", not "AM").
# arsenal/keylab/screen.py is the byte-identical encoder, pinned against Arturia's own classes.
class Screen:
    PROPERTIES = 0
    F1L = 10       # one line, full screen
    F2L = 12       # two lines, full screen
    POPUP1L = 23   # one-line popup (simplest)
    POPUP2L = 24   # two-line popup
    POPUP3L = 25   # three-line popup
    KNOB = 28      # knob graphic with a 0-127 bar (probe P15: unconfirmed on the hardware)
    FADER = 29     # fader graphic with a 0-127 bar (probe P15: unconfirmed on the hardware)


def _ascii32(text) -> list:
    s = "".join(c if 32 <= ord(c) < 127 else "?" for c in str(text))
    if len(s) > 32:
        s = s[:29] + "..."
    return list(s.encode("ascii", "replace"))


def _screen(screen_id: int) -> list:
    return [0x00, Ctx.DAW, Param.DISPLAY, screen_id]


def screen_popup1(text) -> bytes:
    """One-line popup on the LCD (the simplest screen write). screenId 23."""
    return sysex(_screen(Screen.POPUP1L) + [0x00] + _ascii32(text) + [0x00])


def _two_line(screen_id, line1, line2, color1, color2) -> bytes:
    d = _screen(screen_id)
    d += [0x00] + _ascii32(line1) + [0x00]
    d += [0x01, 1, 0x00] + [0x02, to7(color1[0]), to7(color1[1]), to7(color1[2]), 0x00]
    d += [0x03] + _ascii32(line2) + [0x00]
    d += [0x04, 1, 0x00] + [0x05, to7(color2[0]), to7(color2[1]), to7(color2[2]), 0x00]
    return sysex(d)


def screen_popup2(line1, line2, color1=(255, 255, 255), color2=(0, 200, 160)) -> bytes:
    """Two-line popup with per-line colour (8-bit RGB in). screenId 24."""
    return _two_line(Screen.POPUP2L, line1, line2, color1, color2)


def screen_full2(line1, line2, color1=(0, 200, 160), color2=(255, 255, 255)) -> bytes:
    """Two-line FULL-SCREEN view (not a popup). screenId 12."""
    return _two_line(Screen.F2L, line1, line2, color1, color2)


def screen_param(screen_id: int, name, value_text, level: int, color=(0, 200, 160)) -> bytes:
    """Knob (28) or fader (29) screen: a parameter's name, its value text and a 0-127 bar. The field tags are the
    facts read from KL3Display's knob and fader screens (tag 0 = the value line, 1 = the name line, 2 = the bar
    level, 3 = colour type, 4 = RGB). Unconfirmed on the hardware until probe P15 says it draws."""
    d = _screen(screen_id)
    d += [0x00] + _ascii32(value_text) + [0x00]
    d += [0x01] + _ascii32(name) + [0x00]
    d += [0x02, max(0, min(127, int(level))), 0x00]
    d += [0x03, 1, 0x00]
    d += [0x04, to7(color[0]), to7(color[1]), to7(color[2]), 0x00]
    return sysex(d)


def selftest() -> List[str]:
    """Prove the wire format offline against the bytes read from Arturia's own code. Returns failures ([] == pass)."""
    fails = []

    def check(name, got: bytes, want_hex: str):
        want = bytes.fromhex(want_hex.replace(" ", ""))
        if got != want:
            fails.append(f"{name}: got {got.hex(' ')}  want {want.hex(' ')}")

    # pad 1 bank A, full green, req 0x00 (the confirmed-live colour byte); ePad1BankA = 34 = 0x22
    check("pad1A green", set_led("A1", "green"), "F0 00 20 6B 7F 42 00 02 03 22 00 7F 00 00 F7")
    # pad 1 DAW bank -- the bank that renders live colour on hardware (confirmed 2026-10-22); ePad1BankDaw = 82 = 0x52
    check("pad1 DAW green", set_led(pad_led(1, "DAW"), "green"), "F0 00 20 6B 7F 42 00 02 03 52 00 7F 00 00 F7")
    # DAW connect -> KL3Connexion.DAWConnexion
    check("daw connect", daw_connect(True), "F0 00 20 6B 7F 42 00 02 05 01 F7")
    check("daw drop", daw_connect(False), "F0 00 20 6B 7F 42 00 02 05 00 F7")
    # back LED dim white (KL3Return.py:108 used eBack=29=0x1d with 0x0d,0x0d,0x0d) via req 0x00
    check("back dim", set_led("back", (26, 26, 26), req=REQ_CTRL), "F0 00 20 6B 7F 42 00 02 03 1D 0D 0D 0D 00 F7")
    # id map spot checks
    if pad_led(12, "A") != 45:
        fails.append(f"pad_led(12,A)={pad_led(12,'A')} want 45")
    if pad_led(1, "DAW") != 82:
        fails.append(f"pad_led(1,DAW)={pad_led(1,'DAW')} want 82")
    if led_id("play") != 6 or led_id("D12") != 81:
        fails.append("led_id resolution wrong")
    # chord + pitchclass->pad
    pcs, root = chord_pitchclasses("Cmaj7")
    if pcs != [0, 4, 7, 11] or root != 0:
        fails.append(f"Cmaj7 pcs={pcs} root={root}")
    if pad_for_pitchclass(0) != 9:  # C == note 36 == pad 9
        fails.append(f"pad_for_pitchclass(C)={pad_for_pitchclass(0)} want 9")
    # colour conversion endpoints
    if to7(255) != 127 or to7(0) != 0:
        fails.append("to7 endpoints wrong")
    return fails
