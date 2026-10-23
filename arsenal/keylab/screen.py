"""arsenal.keylab.screen -- realtime output to the KeyLab mk3's own screen: chord, BPM and the VJ scene, live.

Three layers, each usable alone:

1. THE ENCODER, byte-for-byte the construction in Arturia's FL Studio script (read in place, read-only:
   C:/Users/L5/Documents/Image-Line/FL Studio/Settings/Hardware/Arturia KeyLab mk3/). Line numbers are that
   file set as installed on 2026-10-23:
     KL3Dispatch.py:64-66    send_to_device: F0 00 20 6B 7F 42 + data + F7
     KL3Display.py:22        the display prefix [0x00, eDaw=2, eDisplay=4]; the screen id byte follows
     KL3Display.py:26-56     the line rule: ASCII only, else the whole line becomes ".Undefined text."; a line over 32
                             characters becomes its first 28 + "..." (31 in all); line 2 and line 3 are UPPER-CASED
     KL3Display.py:91-376    each screen's tagged fields: [tag] + value + [0x00], one function per screen below
     KL3Display.py:70-87     screen-button labels and their clean message; the label body is
     KL3Buttons.py:62-90     CTXButton.ButtonSysEx: [slot+1] + present fields only (a None field is left out)
     ScreenId.py             the screen ids; images_sub_enums.py the icon numbers
   tests/test_keylab_screen.py pins it two ways: hand-written hex for several strings and layouts, and (when the
   script is on this machine) by running Arturia's own Display/CTXButton classes against stub FL modules and
   comparing every byte. One deliberate difference: a NUL inside a text field is refused here (the script would send
   it and end the field early).

2. THE GATE (ScreenWriter): the only door from this module to the DAW output. It refuses anything that is not a
   display frame (so it cannot send the DAW connect/disconnect or an LED colour: GUEST mode by construction), refuses
   the never-send screens 38 boot, 43 pedal calibration, 44 bootloader, sends a frame only when it differs from the
   last one sent, at most one per `min_interval` (default 0.1 s, newest frame wins), and every packet passes a
   governor.BurstGovernor (the MidiOut's own, or one of its own when the sink has none).

3. THE LIVE READOUT: chord, BPM and scene from the VJ engine's SSE feed (127.0.0.1:8794/api/events: hello, beat,
   chord, ...), or the chord straight from the keys (`--source keys`, the chordview reading), drawn on the
   two-line full screen 12 (the one CONFIRMED to stay up with no flicker, 2026-10-22). Chord, roman numeral and key
   on line 1, "Gbmaj7  IVmaj7  in Db" (line 2 is upper-cased by the script's rule, which would turn "Am" into "AM",
   "vi" into "VI" and "Db" into "DB"; the numeral and the key come from `vj --chords sense`, chordsense);
   "128 BPM | SCENE" on line 2.

Sharing the screen with FL Studio (honest, from reading device_KL3.py and KL3Return.py): FL's script repaints its own
screen (screen 13 or 11) and all eight button labels from OnRefresh whenever FL's refresh flags are anything other than
exactly 4 or 4096 -- a window focus change, a channel or track selection, a transport start or stop, a colour or name
change. It also repaints a popup (24) on every idle tick while Rewind / Fast-forward is held, and draws knob / fader
popups when a control is moved. This readout redraws only when its own content changes, so after an FL repaint FL's
screen stays until the next chord, BPM or scene change. `--reassert SECS` re-sends the current frame every SECS
seconds (one packet each time) if that is wanted. The clean answers are FL closed (then `--connect`, which refuses
while FL runs) or our own FL script with a VJ hand-off mode (design D8).

The scene name: the VJ engine contract has no scene event yet, so `--scene NAME` sets it, and a future
{"t": "scene", "name": "...", "color": "#rrggbb"} event on the same feed is honoured (a proposed addition).
"""
from __future__ import annotations

import heapq
import json
import math
import os
import queue
import subprocess
import threading
import time
import urllib.request
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from . import protocol as P
from .governor import BurstGovernor

# =====================================================================================================================
# 1. the encoder -- byte-identical to KL3Display.py / KL3Buttons.py
# =====================================================================================================================
DISPLAY = bytes([0x00, P.Ctx.DAW, P.Param.DISPLAY])     # KL3Display.py:22  _data_string
LINE_LEN = 32                                            # every _get_line_bytes(..., 32) call in KL3Display.py
UNDEFINED = ".Undefined text."                           # KL3Display.py:42


class ScreenId:      # ScreenId.py (eScreenId), verbatim numbers
    PROPERTIES = 0
    BUTTON5, BUTTON6, BUTTON7, BUTTON8, BUTTON1, BUTTON2, BUTTON3, BUTTON4 = 1, 2, 3, 4, 5, 6, 7, 8
    BUTTONS_CLEAR = 9
    F1L, F1L_INV, F2L, F2L_INV, F2L_BIG = 10, 11, 12, 13, 14
    LI_1L, LI_2L, TWO_LI_2L = 15, 16, 17
    TYPE_CAROUSEL, INSTRUMENT_CAROUSEL = 18, 19
    LIST_SETUP, LIST_APPEND, LIST_PREPEND = 20, 21, 22
    POPUP_1L, POPUP_2L, POPUP_3L, POPUP_LI_1L, POPUP_LI_2L = 23, 24, 25, 26, 27
    KNOB, FADER, PAD, POPUP_FULL = 28, 29, 30, 31
    RENAME, CURVE_EDITOR, PITCH_WHEEL, PARAM_GAUGE, ICON_2_SIDES, WELCOME = 32, 33, 34, 35, 36, 37
    BOOT = 38
    COLOR_PICKER, BROWSER, LINE_KEYBOARD_POPUP, LINE_KEYBOARD = 39, 40, 41, 42
    PEDAL_CALIBRATION, BOOTLOADER = 43, 44
    THREE_L, TWO_L_SMALL = 45, 46


# Device procedures, never written by anything in this repo (surface map row Y9).
NEVER_SEND = frozenset({ScreenId.BOOT, ScreenId.PEDAL_CALIBRATION, ScreenId.BOOTLOADER})


class Icon:          # images_sub_enums.py, the ones a VJ readout is likely to want (the full list is 86 + 22)
    ARTURIA_LOGO = 0
    TYPE_PAD = 8
    TYPE_SEQUENCE = 10
    TYPE_SOUND_EFFECTS = 11
    ICON_CHORD = 65
    ICON_CONTROLS = 67
    ICON_FL_STUDIO = 71
    ICON_METRONOME = 74
    ICON_MIDI = 75
    ICON_PADS = 76
    ICON_PROGRESSION = 78
    ICON_SCALE = 80


class SmallIcon:     # images_sub_enums.py eSmallIcon (button-label pictograms)
    ARROW_LEFT, ARROW_RIGHT = 3, 4
    MUTE, SOLO = 10, 13
    HEART, HEART_LIKED = 17, 18
    MIXER = 19


class ScreenRefused(ValueError):
    """A frame this module will not build or send (a never-send screen, a non-display message, a bad byte)."""


def line_src(line: str, length: int = LINE_LEN, upper: bool = False) -> str:
    """The text the script would put on the wire for one line (KL3Display.py:26-47, _get_line_src)."""
    if not isinstance(line, str):
        raise TypeError(f"a screen line must be str, got {type(line).__name__}")   # the script iterates it too
    if all(ord(ch) < 128 for ch in line):
        src = line[:length - 4] + "..." if len(line) > length else line
    else:
        src = UNDEFINED
    return src.upper() if upper else src


def line_bytes(line: str, length: int = LINE_LEN, upper: bool = False) -> bytes:
    """KL3Display.py:49-56 (_get_line_bytes): the line rule, as ASCII bytes."""
    data = line_src(line, length, upper).encode("ascii")
    if 0 in data:
        raise ScreenRefused("a NUL inside a text field would end the field early (the script does not check this)")
    return data


def _field(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + bytes(value) + b"\x00"


def _byte(v, what: str) -> bytes:
    v = int(v)
    if not 0 <= v <= 127:
        raise ScreenRefused(f"{what} must be 0..127, got {v}")
    return bytes([v])


def _col(color, what: str = "colour") -> bytes:
    """A colour exactly as the script passes it: three channels, each 0..127 (bytes(color) in KL3Display)."""
    c = list(color)
    if len(c) != 3:
        raise ScreenRefused(f"{what} must be three 0..127 channels, got {color!r}")
    return b"".join(_byte(x, what) for x in c)


def frame(screen_id: int, body: bytes = b"") -> bytes:
    """One screen message: F0 00 20 6B 7F 42 | 00 02 04 | <screen id> | <tagged fields> | F7."""
    sid = int(screen_id)
    if sid in NEVER_SEND:
        raise ScreenRefused(f"screen {sid} is a device procedure (38 boot, 43 pedal calibration, 44 bootloader); "
                            "it is never sent")
    if not 0 <= sid <= 127:
        raise ScreenRefused(f"screen id must be 0..127, got {sid}")
    payload = DISPLAY + bytes([sid]) + bytes(body)
    bad = [b for b in payload if b > 0x7F]
    if bad:
        raise ScreenRefused(f"SysEx data byte above 0x7F: {bad[0]:#04x}")
    return P.HEADER + payload + bytes([P.EOX])


# --- the screens (one per KL3Display method) -------------------------------------------------------------------------
def screen_prop(color1) -> bytes:
    """Screen_Prop, KL3Display.py:91-99. Screen 0, one colour."""
    return frame(ScreenId.PROPERTIES, _field(0x00, _col(color1)))


def _one_line(sid: int, line1, colortype1, color1) -> bytes:
    return frame(sid, _field(0x00, line_bytes(line1)) + _field(0x01, _byte(colortype1, "colortype"))
                 + _field(0x02, _col(color1)))


def f1l(line1, colortype1, color1) -> bytes:
    """Screen_F1L, KL3Display.py:102-112. One line, full screen (10)."""
    return _one_line(ScreenId.F1L, line1, colortype1, color1)


def f1l_inv(line1, colortype1, color1) -> bytes:
    """Screen_F1LInv, KL3Display.py:116-126. One line, inverted (11)."""
    return _one_line(ScreenId.F1L_INV, line1, colortype1, color1)


def _two_lines(line1, colortype1, color1, line2, colortype2, color2) -> bytes:
    return (_field(0x00, line_bytes(line1)) + _field(0x01, _byte(colortype1, "colortype")) + _field(0x02, _col(color1))
            + _field(0x03, line_bytes(line2, upper=True)) + _field(0x04, _byte(colortype2, "colortype"))
            + _field(0x05, _col(color2)))


def f2l(line1, colortype1, color1, line2, colortype2, color2) -> bytes:
    """Screen_F2L, KL3Display.py:130-144. Two lines, full screen (12); stays up (CONFIRMED 2026-10-22)."""
    return frame(ScreenId.F2L, _two_lines(line1, colortype1, color1, line2, colortype2, color2))


def f2l_inv(line1, colortype1, color1, line2, colortype2, color2) -> bytes:
    """Screen_F2LInv, KL3Display.py:148-162. Two lines, inverted (13): FL's channel-rack screen."""
    return frame(ScreenId.F2L_INV, _two_lines(line1, colortype1, color1, line2, colortype2, color2))


def fb2l(line1, colortype1, color1, line2, colortype2, color2) -> bytes:
    """Screen_FB2L, KL3Display.py:166-180. Two lines, big (14)."""
    return frame(ScreenId.F2L_BIG, _two_lines(line1, colortype1, color1, line2, colortype2, color2))


def li1l(line1, icon: Optional[int] = None) -> bytes:
    """Screen_LI1L, KL3Display.py:184-196. Icon + one line (15). The script takes a colour and never uses it."""
    body = _field(0x00, line_bytes(line1))
    if icon is not None:
        body += _field(0x01, _byte(icon, "icon"))
    return frame(ScreenId.LI_1L, body)


def li2l(line1, line2, icon: Optional[int] = None) -> bytes:
    """Screen_LI2L, KL3Display.py:200-213. Icon + two lines (16); line 2 upper-cased, no colours."""
    body = _field(0x00, line_bytes(line1)) + _field(0x01, line_bytes(line2, upper=True))
    if icon is not None:
        body += _field(0x02, _byte(icon, "icon"))
    return frame(ScreenId.LI_2L, body)


def p1l(line1) -> bytes:
    """Screen_P1L, KL3Display.py:217-225. One-line popup (23); the script takes a colour and never sends it."""
    return frame(ScreenId.POPUP_1L, _field(0x00, line_bytes(line1)))


def p2l(line1, colortype1, color1, line2, colortype2, color2) -> bytes:
    """Screen_P2L, KL3Display.py:229-243. Two-line popup (24)."""
    return frame(ScreenId.POPUP_2L, _two_lines(line1, colortype1, color1, line2, colortype2, color2))


def p3l(line1, colortype1, color1, line2, colortype2, color2, line3, colortype3, color3) -> bytes:
    """Screen_P3L, KL3Display.py:247-265. Three-line popup (25); lines 2 and 3 upper-cased."""
    body = _two_lines(line1, colortype1, color1, line2, colortype2, color2)
    body += (_field(0x06, line_bytes(line3, upper=True)) + _field(0x07, _byte(colortype3, "colortype"))
             + _field(0x08, _col(color3)))
    return frame(ScreenId.POPUP_3L, body)


def pli1l(line1, icon: Optional[int] = None) -> bytes:
    """Screen_PLI1L, KL3Display.py:269-281. Icon + one line popup (26)."""
    body = _field(0x00, line_bytes(line1))
    if icon is not None:
        body += _field(0x01, _byte(icon, "icon"))
    return frame(ScreenId.POPUP_LI_1L, body)


def pli2l(line1, colortype1, color1, line2, colortype2, color2, icon: Optional[int] = None) -> bytes:
    """Screen_PLI2L, KL3Display.py:285-304. Icon + two lines popup (27): FL's Metronome / Tap Tempo card."""
    body = _two_lines(line1, colortype1, color1, line2, colortype2, color2)
    if icon is not None:
        body += _field(0x06, _byte(icon, "icon"))
    return frame(ScreenId.POPUP_LI_2L, body)


def _param(sid: int, line1, line2, hw_value, colortype, color, pad_order: bool = False) -> bytes:
    # The script sends line 2 (the value) first: "Line 1 and 2 inverted to respect the order in popup".
    first = _field(0x00, line_bytes(line2)) + _field(0x01, line_bytes(line1))
    hw = _field(0x02, _byte(hw_value, "hw_value"))
    look = _field(0x03, _byte(colortype, "colortype")) + _field(0x04, _col(color))
    return frame(sid, first + (look + hw if pad_order else hw + look))


def knob(line1, line2, hw_value, colortype, color) -> bytes:
    """Screen_K, KL3Display.py:308-320. Knob (28): line1 = name, line2 = value text, hw_value = the 0..127 bar."""
    return _param(ScreenId.KNOB, line1, line2, hw_value, colortype, color)


def fader(line1, line2, hw_value, colortype, color) -> bytes:
    """Screen_F, KL3Display.py:324-336. Fader (29), same fields as the knob."""
    return _param(ScreenId.FADER, line1, line2, hw_value, colortype, color)


def pad(line1, line2, hw_value, colortype, color) -> bytes:
    """Screen_P, KL3Display.py:341-353. Pad (30): same tags, but the script sends colour BEFORE the bar."""
    return _param(ScreenId.PAD, line1, line2, hw_value, colortype, color, pad_order=True)


def ti2lfix(line1, colortype1, color1, line2, colortype2, color2, icon: Optional[int] = None) -> bytes:
    """Screen_TI2LFIX, KL3Display.py:357-376. Full popup with icon (31): FL's "Connected" title card."""
    body = _two_lines(line1, colortype1, color1, line2, colortype2, color2)
    if icon is not None:
        body += _field(0x06, _byte(icon, "icon"))
    return frame(ScreenId.POPUP_FULL, body)


# --- screen-button labels (KL3Buttons.ButtonSysEx + KL3Display.CTXButtonScreen) --------------------------------------
# Label slot (the script's ID 0..7) -> the physical screen button it sits on: eButton5 = 1 is slot 0 (screen id =
# slot + 1), so slots 0-3 are buttons 5-8 and slots 4-7 are buttons 1-4 (KL3Return.py:313-345 comments agree).
SLOT_FOR_BUTTON = {5: 0, 6: 1, 7: 2, 8: 3, 1: 4, 2: 5, 3: 6, 4: 7}

# Label `type` values the script uses (KL3Return.py:314-435). Meanings INFERRED from where FL uses them, never seen:
LABEL_EMPTY, LABEL_TEXT, LABEL_TEXT_ACTIVE, LABEL_ICON, LABEL_ICON_ACTIVE = 0, 4, 6, 10, 11


def _label_text(line, what: str) -> bytes:
    # KL3Buttons.py:53-54: bytearray(line, 'ascii') -- no length rule, no case change, non-ASCII is an error there too
    try:
        data = str(line).encode("ascii")
    except UnicodeEncodeError:
        raise ScreenRefused(f"{what} must be ASCII (the script raises on anything else): {line!r}") from None
    if 0 in data:
        raise ScreenRefused(f"{what}: a NUL would end the field early")
    return data


def button_label(slot: int, type: Optional[int] = 0, line_number: Optional[int] = 0, color_type: Optional[int] = 0,
                 icon: Optional[int] = 0, custom_color=(0, 0, 0), line1: Optional[str] = "",
                 line2: Optional[str] = "") -> bytes:
    """One screen-button label (KL3Buttons.py:62-90 inside KL3Display.py:70-77). `slot` is the script's ID 0..7
    (see SLOT_FOR_BUTTON); the frame's screen id is slot + 1. Arguments mirror PagedDisplay.SetButton; a None argument
    leaves its field out, exactly as ButtonSysEx does. Defaults are CTXButton.__init__'s."""
    s = int(slot)
    if not 0 <= s <= 7:
        raise ScreenRefused(f"label slot must be 0..7, got {s}")
    body = b""
    if type is not None:
        body += _field(0x00, _byte(type, "type"))
    if line_number is not None:
        body += _field(0x01, _byte(line_number, "line_number"))
    if color_type is not None:
        body += _field(0x02, _byte(color_type, "color_type"))
    if icon is not None:
        body += _field(0x03, _byte(icon, "icon"))
    if custom_color is not None:
        body += _field(0x04, _col(custom_color, "custom_color"))
    if line1 is not None:
        body += _field(0x05, _label_text(line1, "line1"))
    if line2 is not None:
        body += _field(0x06, _label_text(line2, "line2"))
    return frame(s + 1, body)


def clean_button(script_id: int) -> bytes:
    """CleanCTXButtonScreen, KL3Display.py:80-87: [ID] + [0, 0, 0]. Faithful, including what looks like an
    off-by-one in the script: it uses screen id = ID (not ID + 1), so ID 0 lands on screen 0 (properties)."""
    return frame(int(script_id), b"\x00\x00\x00")


# --- colour helpers --------------------------------------------------------------------------------------------------
def rgb7(color) -> Tuple[int, int, int]:
    """An 8-bit colour (name | #rrggbb | 'r,g,b' | (r, g, b) 0..255) as the 7-bit triple the screen takes, by the
    script's own rule: each channel // 2 (KL3Return.py:485-499 get_channel_color / get_track_color)."""
    r, g, b = P.parse_color(color)
    return (max(0, min(255, int(r))) // 2, max(0, min(255, int(g))) // 2, max(0, min(255, int(b))) // 2)


WHITE7 = (127, 127, 127)            # the script's WHITE (KL3Navigation.py:31)
ANALOG_LAB_BLUE7 = (0, 108, 122)    # the script's title colour (KL3Navigation.py:30)
GREY7 = (48, 48, 48)
DIM7 = (80, 80, 80)
RED7 = (127, 0, 20)

# Characters a chord or scene name may carry that are not ASCII; anything else non-ASCII becomes "?". Without this the
# script's rule would blank the WHOLE line to ".Undefined text.".
_ASCII_MAP = {"\u266d": "b", "\u266f": "#", "\u266e": "", "\u00b7": "-", "\u2022": "-", "\u2013": "-", "\u2014": "-",
              "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u00b0": "o", "\u00f8": "o", "\u0394": "maj",
              "\u2206": "maj", "\u2026": "..."}


def ascii_clean(text) -> str:
    """Printable ASCII (32..126) for the screen: musical sharps / flats spelled out, control characters to spaces."""
    out = []
    for ch in str(text):
        o = ord(ch)
        if 32 <= o < 127:
            out.append(ch)
        elif ch in _ASCII_MAP:
            out.append(_ASCII_MAP[ch])
        elif o < 32 or o == 127:
            out.append(" ")
        else:
            out.append("?")
    return "".join(out)


# =====================================================================================================================
# 2. the gate
# =====================================================================================================================
_PREFIX = P.HEADER + DISPLAY


def check(data: bytes) -> int:
    """Raise ScreenRefused unless `data` is one display frame for a sendable screen. Returns the screen id."""
    b = bytes(data)
    if len(b) < len(_PREFIX) + 2 or not b.startswith(_PREFIX) or b[-1] != P.EOX:
        raise ScreenRefused("not a screen frame (F0 00 20 6B 7F 42 00 02 04 <id> ... F7); the screen writer sends "
                            "nothing else, so it can never send the DAW connect or an LED")
    sid = b[len(_PREFIX)]
    if sid in NEVER_SEND:
        raise ScreenRefused(f"screen {sid} is never sent (38 boot, 43 pedal calibration, 44 bootloader)")
    if any(x > 0x7F for x in b[len(P.HEADER):-1]):
        raise ScreenRefused("a data byte above 0x7F inside the frame")
    return sid


class ScreenWriter:
    """The one door from this module to the device. Change-only, newest-wins, at most one frame per `min_interval`,
    every packet through a BurstGovernor. `reassert_s` > 0 re-sends the current frame that often (FL repaints)."""

    def __init__(self, out, min_interval: float = 0.1, reassert_s: float = 0.0,
                 governor: Optional[BurstGovernor] = None, clock: Callable[[], float] = time.perf_counter,
                 sleep: Callable[[float], None] = time.sleep, on_send: Optional[Callable[[bytes, bool], None]] = None):
        self.out = out
        self.min_interval, self.reassert_s = max(0.0, float(min_interval)), max(0.0, float(reassert_s or 0.0))
        self.clock, self.sleep, self.on_send = clock, sleep, on_send
        # Exactly one governor per packet: the sink's own (winmidi.MidiOut always has one) or ours.
        self.governor = None if getattr(out, "governor", None) is not None else (governor or BurstGovernor())
        self.last: Optional[bytes] = None
        self.pending: Optional[bytes] = None
        self.t_sent: Optional[float] = None
        self.sent = self.unchanged = self.coalesced = self.reasserted = 0

    def offer(self, data: bytes) -> bool:
        """Ask for this frame to be on the screen. Sends now if allowed, else holds it (newest wins). True if sent."""
        check(data)
        data = bytes(data)
        if data == self.last:
            if self.pending is not None:          # the screen already shows what we now want: drop the stale pending
                self.pending = None
                self.coalesced += 1
            else:
                self.unchanged += 1
            return False
        if data == self.pending:
            return self.pump()
        if self.pending is not None:
            self.coalesced += 1
        self.pending = data
        return self.pump()

    def wait_s(self) -> float:
        """Seconds until the held frame may go (0 = now); inf when nothing is held."""
        if self.pending is None:
            return math.inf
        if self.t_sent is None:
            return 0.0
        return max(0.0, self.min_interval - (self.clock() - self.t_sent))

    def pump(self) -> bool:
        """Send the held frame if its time has come, or re-assert the current one. True if a packet went out."""
        now = self.clock()
        if self.pending is not None:
            if self.t_sent is None or now - self.t_sent >= self.min_interval:
                self._send(self.pending, reassert=False)
                return True
            return False
        if self.reassert_s and self.last is not None and self.t_sent is not None and now - self.t_sent >= self.reassert_s:
            self._send(self.last, reassert=True)
            return True
        return False

    def flush(self) -> bool:
        """Wait out the interval and send the held frame (one-shot writes, shutdown)."""
        if self.pending is None:
            return False
        w = self.wait_s()
        if w > 0:
            self.sleep(w)
        self._send(self.pending, reassert=False)
        return True

    def _send(self, data: bytes, reassert: bool) -> None:
        check(data)
        if self.governor is not None:
            self.governor.admit()
        self.out.send_sysex(data)
        self.t_sent = self.clock()
        self.last, self.pending = data, None
        self.sent += 1
        if reassert:
            self.reasserted += 1
        if self.on_send is not None:
            self.on_send(data, reassert)

    def stats(self) -> Dict[str, int]:
        return {"sent": self.sent, "unchanged": self.unchanged, "coalesced": self.coalesced,
                "reasserted": self.reasserted}


# =====================================================================================================================
# 3. the live readout
# =====================================================================================================================
DEFAULT_ENGINE = "http://127.0.0.1:8794/api/events"
LAYOUTS = {"full": ScreenId.F2L, "inverted": ScreenId.F2L_INV, "big": ScreenId.F2L_BIG}
_TWO_LINE = {ScreenId.F2L: f2l, ScreenId.F2L_INV: f2l_inv, ScreenId.F2L_BIG: fb2l}

BPM_HYSTERESIS = 0.75          # the shown BPM moves only when the tracker moves this far from it (no 127/128 flapping)
LOCK_ON, LOCK_OFF = 0.55, 0.45  # beat confidence: line 2 turns white at LOCK_ON, back to dim below LOCK_OFF


def _quality_color7(quality) -> Tuple[int, int, int]:
    """The chord's mood colour, the same one chordview paints the pads with, as 7-bit."""
    from .chordview import QUALITY_COLORS      # one table for pads and screen
    q = "" if quality in (None, "maj", "major") else str(quality)
    return rgb7(QUALITY_COLORS.get(q, (255, 255, 255)))


def key_short(name) -> Optional[str]:
    """'Db major' -> 'Db', 'Bb minor' -> 'Bbm' (the key on line 1, where the case of 'b' survives)."""
    parts = str(name or "").split()
    if len(parts) != 2 or parts[1] not in ("major", "minor") or not parts[0][:1].isalpha():
        return None
    return parts[0] + ("m" if parts[1] == "minor" else "")


def fit_line(parts: Sequence[str], drop: Sequence[int] = (), length: int = LINE_LEN) -> str:
    """Join the non-empty parts with two spaces, or one when two do not fit in `length`; then leave out the parts at
    the indices in `drop`, in that order, until it fits (the script would cut it to 28 characters and '...')."""
    keep = [True] * len(parts)
    for k in [None, *drop]:
        if k is not None:
            keep[k] = False
        words = [p for p, on in zip(parts, keep) if on and p]
        for sep in ("  ", " "):
            line = sep.join(words)
            if len(line) <= length:
                return line
    return " ".join(p for p, on in zip(parts, keep) if on and p)


class Readout:
    """What the screen should say, from VJ-engine events. Pure (no I/O, the clock is passed in) so it is pinned.

    Line 1 (shown in its own case) carries the chord, its roman numeral and the key -- 'Gbmaj7  IVmaj7  in Db' -- because
    the script upper-cases lines 2 and 3 (vi and VI, Db and DB would be lost there). The key comes from the engine's key
    events (vj --chords sense), else from the chord's own key field; the numeral is shown only while it is read in the
    key shown. An audio 'N' (no chord: drums, noise) shows '--'."""

    def __init__(self, scene: Optional[str] = None, prefer_keys_s: float = 3.0, pulse: bool = False):
        self.connected = False          # the engine has answered at least once
        self.up = False                 # ... and is answering now
        self.chord: Optional[str] = None
        self.quality: Optional[str] = None
        self.chord_src: Optional[str] = None
        self.roman: Optional[str] = None
        self.chord_key: Optional[str] = None     # the key the chord's numeral is read in
        self.key: Optional[str] = None           # the engine's key event
        self.t_keys = -math.inf
        self.prefer_keys_s = prefer_keys_s
        self.bpm_shown: Optional[int] = None
        self.locked = False
        self.scene = ascii_clean(scene).strip() if scene else None
        self.scene_color: Optional[Tuple[int, int, int]] = None
        self.pulse = pulse
        self.beat_n: Optional[int] = None

    def set_bpm(self, bpm) -> None:
        try:
            v = float(bpm)
        except (TypeError, ValueError):
            return
        if not 20.0 <= v <= 400.0:
            return
        if self.bpm_shown is None or abs(v - self.bpm_shown) >= BPM_HYSTERESIS:
            self.bpm_shown = int(round(v))

    def feed(self, evt: dict, now: float) -> None:
        t = evt.get("t")
        if t in ("_up", "hello"):
            if t == "hello":
                self.key = None         # a (re)started engine: its key event follows its hello
            self.connected = self.up = True
        elif t == "_down":
            self.up = False
        elif t == "key":
            if key_short(evt.get("name")):
                self.key = ascii_clean(evt["name"]).strip()
        elif t == "chord":
            name = evt.get("name")
            if not name:
                return
            src = evt.get("src") or "keys"
            if src == "audio" and now - self.t_keys < self.prefer_keys_s:
                return                  # what you play outranks what the song is estimated to play, for a moment
            if src == "keys":
                self.t_keys = now
            none = name == "N" and evt.get("root") is None
            self.chord = None if none else ascii_clean(name).strip()
            self.quality, self.chord_src = evt.get("quality"), src
            roman, key = evt.get("roman"), evt.get("key")
            self.roman = ascii_clean(roman).strip() if isinstance(roman, str) and roman and not none else None
            self.chord_key = ascii_clean(key).strip() if isinstance(key, str) and key_short(key) else None
        elif t == "beat":
            self.set_bpm(evt.get("bpm"))
            conf = evt.get("conf")
            if isinstance(conf, (int, float)):
                if conf >= LOCK_ON:
                    self.locked = True
                elif conf < LOCK_OFF:
                    self.locked = False
            if self.pulse and isinstance(evt.get("n"), int):
                self.beat_n = evt["n"]
        elif t == "scene":
            name = evt.get("name")
            if name:
                self.scene = ascii_clean(name).strip()
            col = evt.get("color")
            if col:
                try:
                    self.scene_color = rgb7(col)
                except ValueError:
                    self.scene_color = None

    def view(self) -> Tuple[str, Tuple[int, int, int], str, Tuple[int, int, int]]:
        """(line 1, its 7-bit colour, line 2, its colour). Line 2 is shown upper-case by the script's rule."""
        if not self.connected:
            return ("Aurora", ANALOG_LAB_BLUE7, "waiting for the VJ engine", DIM7)
        if self.chord:
            line1 = self.line1()
            c1 = _quality_color7(self.quality)
        else:
            line1, c1 = "--", DIM7
        if not self.up:
            return (line1, c1, "VJ engine offline", RED7)
        parts = [f"{self.bpm_shown} BPM" if self.bpm_shown else "--- BPM"]
        if self.pulse and self.beat_n is not None:
            k = self.beat_n % 4
            parts.append("".join("*" if i == k else "." for i in range(4)))
        if self.scene:
            parts.append(self.scene)
        c2 = self.scene_color or (WHITE7 if self.locked else DIM7)
        return (line1, c1, " | ".join(parts), c2)

    def line1(self) -> str:
        """'Gbmaj7  IVmaj7  in Db', '(song)' after an audio chord. When it does not fit the screen's 32 characters,
        '(song)' goes first, then the key."""
        key = self.key or self.chord_key
        roman = self.roman if (self.roman and (self.chord_key is None or key == self.chord_key)) else None
        short = key_short(key)
        return fit_line([self.chord or "--", roman or "", f"in {short}" if short else "",
                         "(song)" if self.chord_src == "audio" else ""], drop=(3, 2))


def render(view, layout: int = ScreenId.F2L) -> bytes:
    """A view as one two-line frame (screen 12 by default; 13 inverted; 14 big). Colour type 1 = the given RGB."""
    line1, c1, line2, c2 = view
    return _TWO_LINE[layout](ascii_clean(line1), 1, c1, ascii_clean(line2), 1, c2)


class SSEParser:
    """Server-Sent Events, one line at a time: 'data:' lines gather until a blank line, then parse as JSON."""

    def __init__(self):
        self._data: List[str] = []

    def feed(self, line: str) -> Optional[dict]:
        line = line.rstrip("\r\n")
        if line == "":
            if not self._data:
                return None
            raw, self._data = "\n".join(self._data), []
            try:
                obj = json.loads(raw)
            except ValueError:
                return None
            return obj if isinstance(obj, dict) else None
        if line.startswith(":"):
            return None                 # comment / heartbeat
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "data":
            self._data.append(value)
        return None


def sse_loop(url: str, q: "queue.Queue", stop: threading.Event, read_timeout: float = 35.0,
             retry_s: Sequence[float] = (1.0, 2.0, 4.0, 5.0)) -> None:
    """Follow the VJ engine's feed into `q` until `stop`; reconnect with backoff. Puts {'t':'_up'} / {'t':'_down'}."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # 127.0.0.1 never goes through a proxy
    k = 0
    while not stop.is_set():
        try:
            req = urllib.request.Request(url, headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"})
            with opener.open(req, timeout=read_timeout) as resp:
                q.put({"t": "_up"})
                k = 0
                parser = SSEParser()
                for raw in resp:
                    if stop.is_set():
                        break
                    evt = parser.feed(raw.decode("utf-8", "replace"))
                    if evt is not None:
                        q.put(evt)
        except Exception:
            pass                        # engine not up yet, or it went away: report down and retry
        if stop.is_set():
            break
        q.put({"t": "_down"})
        stop.wait(retry_s[min(k, len(retry_s) - 1)])
        k += 1


def keys_loop(port: Optional[str], q: "queue.Queue", stop: threading.Event) -> None:
    """The chord straight from the keys (the MIDI input port), the chordview reading, when no VJ engine runs."""
    from . import winmidi as W
    from .chordview import Voicing
    from .theory import analyze
    listener = W.MidiIn(port=port, prefer="midi")
    listener.start()
    q.put({"t": "_up"})
    voicing, last = Voicing(), None
    try:
        while not stop.is_set():
            while listener.events:
                _t, data, kind = listener.events.pop(0)
                if kind == "short" and len(data) >= 3:
                    voicing.feed(data[0], data[1], data[2])
            sounding = voicing.sounding
            if sounding:
                name, root, qual = analyze(sorted(sounding))
                if root is not None and qual != "note" and name != last:
                    last = name
                    q.put({"t": "chord", "src": "keys", "name": name, "quality": "maj" if qual == "" else qual})
            stop.wait(0.015)
    finally:
        listener.close()


def fl_running() -> bool:
    """Is FL Studio running? When it cannot tell, it says yes (the safe answer: no DAW connect)."""
    try:
        res = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10)
    except Exception:
        return True
    if res.returncode != 0:
        return True
    names = res.stdout.lower()
    return any(n in names for n in ('"fl64.exe"', '"fl.exe"', '"fl studio'))


def run_live(out, source: str = "vj", url: str = DEFAULT_ENGINE, scene: Optional[str] = None,
             layout: int = ScreenId.F2L, secs: Optional[float] = None, min_interval: float = 0.1,
             reassert_s: float = 0.0, pulse: bool = False, keys_port: Optional[str] = None,
             bpm: Optional[float] = None, verbose: bool = True, stop: Optional[threading.Event] = None,
             events: Optional["queue.Queue"] = None, tick: float = 0.02, goodbye: bool = True,
             clock: Callable[[], float] = time.perf_counter) -> Dict[str, int]:
    """Keep the screen showing chord, BPM and scene until `secs` pass, `stop` is set or Ctrl-C. Returns writer stats.
    `events` lets a caller (or a test) feed the readout directly; otherwise a feed thread fills it."""
    stop = stop or threading.Event()
    shown: Dict[bytes, Tuple[str, str]] = {}

    def on_send(data: bytes, reassert: bool) -> None:
        if verbose:
            l1, l2 = shown.get(data, ("?", "?"))
            tag = " (re-assert)" if reassert else ""
            print(f"  screen: {l1}  /  {line_src(l2, upper=True)}{tag}", flush=True)

    writer = ScreenWriter(out, min_interval=min_interval, reassert_s=reassert_s, on_send=on_send, clock=clock)
    readout = Readout(scene=scene, pulse=pulse)
    if bpm:
        readout.set_bpm(bpm)
    q = events if events is not None else queue.Queue()
    feeder = None
    if events is None:
        target = keys_loop if source == "keys" else sse_loop
        arg = keys_port if source == "keys" else url
        feeder = threading.Thread(target=target, args=(arg, q, stop), name=f"screen-{source}", daemon=True)
        feeder.start()
    delayed: List[Tuple[float, int, dict]] = []
    seq = 0
    offered: Optional[bytes] = None
    end = (clock() + secs) if secs else None
    try:
        while not stop.is_set() and (end is None or clock() < end):
            now = clock()
            while True:
                try:
                    evt = q.get_nowait()
                except queue.Empty:
                    break
                if not isinstance(evt, dict):
                    continue
                due = evt.get("due_ms") if evt.get("t") == "beat" else None
                if pulse and isinstance(due, (int, float)) and due > 0:
                    seq += 1                     # the engine says the beat lands due_ms from now: draw it then
                    heapq.heappush(delayed, (now + due / 1000.0, seq, evt))
                    continue
                readout.feed(evt, now)
            while delayed and delayed[0][0] <= now:
                readout.feed(heapq.heappop(delayed)[2], now)
            view = readout.view()
            data = render(view, layout)
            if data != offered:                  # only a change is offered; the writer paces and de-duplicates
                offered = data
                shown.clear()
                shown[data] = (view[0], view[2])
                writer.offer(data)
            writer.pump()
            stop.wait(tick)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        if goodbye:
            try:                                 # leave a quiet card, not a stale chord
                card = ("Aurora", ANALOG_LAB_BLUE7, "live readout stopped", DIM7)
                data = render(card, layout)
                shown[data] = (card[0], card[2])
                writer.pending = None
                writer.offer(data)
                writer.flush()
            except Exception:
                pass
    return writer.stats()


def write_frames(out, frames: Iterable[bytes], min_interval: float = 0.1) -> ScreenWriter:
    """Send a short sequence of frames through the gate, each one in turn (nothing coalesced away)."""
    writer = ScreenWriter(out, min_interval=min_interval)
    for data in frames:
        writer.offer(data)
        writer.flush()
    return writer


def default_receipt_path(now: Optional[float] = None) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "state", "arsenal", "keylab", "receipts")
    return os.path.join(root, f"screen-{stamp}.json")


def write_receipt(path: str, record: dict) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1)
    return path
