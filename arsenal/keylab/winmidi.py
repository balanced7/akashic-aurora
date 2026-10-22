"""WinMM MIDI output (and a light input monitor) via ctypes -- no external MIDI dependency.

Same approach as arsenal.midiports (which enumerates WinMM read-only); this adds the send side:
  midiOutShortMsg  -- notes/CC (3-byte messages)
  midiOutLongMsg   -- SysEx (the pad-colour / screen / handshake commands)

Windows only. Ports are opened by NAME SUBSTRING (case-insensitive); the mk3 exposes several ports and which
one accepts the DAW SysEx is a bench question, so the caller can pass an explicit --port substring.
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from typing import List, Optional, Tuple

MMSYSERR_NOERROR = 0
CALLBACK_NULL = 0
CALLBACK_FUNCTION = 0x00030000
MHDR_DONE = 0x00000001
MIM_DATA = 0x3C3


def _winmm():
    if sys.platform != "win32":
        raise RuntimeError("KeyLab MIDI I/O is Windows-only (WinMM).")
    return ctypes.WinDLL("winmm")


class _OutCaps(ctypes.Structure):
    _fields_ = [("wMid", wintypes.WORD), ("wPid", wintypes.WORD), ("vDriverVersion", wintypes.UINT),
                ("szPname", wintypes.WCHAR * 32), ("wTechnology", wintypes.WORD), ("wVoices", wintypes.WORD),
                ("wNotes", wintypes.WORD), ("wChannelMask", wintypes.WORD), ("dwSupport", wintypes.DWORD)]


class _InCaps(ctypes.Structure):
    _fields_ = [("wMid", wintypes.WORD), ("wPid", wintypes.WORD), ("vDriverVersion", wintypes.UINT),
                ("szPname", wintypes.WCHAR * 32), ("dwSupport", wintypes.DWORD)]


class MIDIHDR(ctypes.Structure):
    _fields_ = [("lpData", ctypes.c_char_p), ("dwBufferLength", wintypes.DWORD),
                ("dwBytesRecorded", wintypes.DWORD), ("dwUser", ctypes.c_void_p), ("dwFlags", wintypes.DWORD),
                ("lpNext", ctypes.c_void_p), ("reserved", ctypes.c_void_p), ("dwOffset", wintypes.DWORD),
                ("dwReserved", ctypes.c_void_p * 8)]


def outputs() -> List[str]:
    """MIDI output device names in device-id order (index == device id)."""
    mm = _winmm()
    mm.midiOutGetNumDevs.restype = wintypes.UINT
    mm.midiOutGetDevCapsW.argtypes = [ctypes.c_size_t, ctypes.c_void_p, wintypes.UINT]
    mm.midiOutGetDevCapsW.restype = wintypes.UINT
    names = []
    for i in range(mm.midiOutGetNumDevs()):
        caps = _OutCaps()
        if mm.midiOutGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps)) == MMSYSERR_NOERROR:
            names.append(caps.szPname)
    return names


def inputs() -> List[str]:
    mm = _winmm()
    mm.midiInGetNumDevs.restype = wintypes.UINT
    mm.midiInGetDevCapsW.argtypes = [ctypes.c_size_t, ctypes.c_void_p, wintypes.UINT]
    mm.midiInGetDevCapsW.restype = wintypes.UINT
    names = []
    for i in range(mm.midiInGetNumDevs()):
        caps = _InCaps()
        if mm.midiInGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps)) == MMSYSERR_NOERROR:
            names.append(caps.szPname)
    return names


def _match(names: List[str], substr: Optional[str], prefer: Optional[str] = None) -> int:
    """Pick a device index. Explicit substr wins; else a KeyLab port, preferring one whose name holds `prefer`
    (the mk3 exposes '...MIDI' and '...DAW' ports -- LED/screen SysEx wants 'DAW', note triggers want 'MIDI')."""
    if substr:
        for i, n in enumerate(names):
            if substr.lower() in n.lower():
                return i
        return -1
    keylab = [i for i, n in enumerate(names) if "keylab" in n.lower()]
    if prefer:
        for i in keylab:
            if prefer.lower() in names[i].lower():
                return i
    return keylab[0] if keylab else -1


class MidiOut:
    """An open WinMM output. Use as a context manager. send_sysex() blocks until the driver accepts the buffer."""

    def __init__(self, port: Optional[str] = None, prefer: Optional[str] = "daw", governor=None):
        # Every SysEx from every producer sharing this output passes one BurstGovernor (the freeze ceiling as a
        # guarantee). Pass governor=False only for a deliberate limit probe such as `ledbench burst`.
        if governor is None:
            from .governor import BurstGovernor
            governor = BurstGovernor()
        self.governor = governor or None
        self.mm = _winmm()
        self.names = outputs()
        self.index = _match(self.names, port, prefer)
        if self.index < 0:
            where = f"matching {port!r}" if port else "named like 'KeyLab'"
            raise RuntimeError(f"no MIDI output {where}. Available: {self.names or '(none)'}")
        self.name = self.names[self.index]
        self.mm.midiOutOpen.argtypes = [ctypes.POINTER(ctypes.c_void_p), wintypes.UINT,
                                        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD]
        self.mm.midiOutOpen.restype = wintypes.UINT
        for fn in (self.mm.midiOutShortMsg, self.mm.midiOutClose, self.mm.midiOutReset):
            fn.argtypes = [ctypes.c_void_p] + ([wintypes.DWORD] if fn is self.mm.midiOutShortMsg else [])
            fn.restype = wintypes.UINT
        for fn in (self.mm.midiOutPrepareHeader, self.mm.midiOutUnprepareHeader, self.mm.midiOutLongMsg):
            fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(MIDIHDR), wintypes.UINT]
            fn.restype = wintypes.UINT
        self.handle = ctypes.c_void_p()
        rc = self.mm.midiOutOpen(ctypes.byref(self.handle), self.index, 0, 0, CALLBACK_NULL)
        if rc != MMSYSERR_NOERROR:
            raise RuntimeError(f"midiOutOpen({self.name!r}) failed, MMRESULT={rc}")

    def send_short(self, status: int, data1: int, data2: int) -> None:
        msg = (status & 0xFF) | ((data1 & 0xFF) << 8) | ((data2 & 0xFF) << 16)
        rc = self.mm.midiOutShortMsg(self.handle, msg)
        if rc != MMSYSERR_NOERROR:
            raise RuntimeError(f"midiOutShortMsg failed, MMRESULT={rc}")

    def send_sysex(self, data: bytes) -> None:
        if self.governor is not None:
            self.governor.admit()
        buf = ctypes.create_string_buffer(bytes(data), len(data))
        hdr = MIDIHDR()
        hdr.lpData = ctypes.cast(buf, ctypes.c_char_p)
        hdr.dwBufferLength = len(data)
        hdr.dwBytesRecorded = len(data)
        if self.mm.midiOutPrepareHeader(self.handle, ctypes.byref(hdr), ctypes.sizeof(hdr)) != MMSYSERR_NOERROR:
            raise RuntimeError("midiOutPrepareHeader failed")
        try:
            rc = self.mm.midiOutLongMsg(self.handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
            if rc != MMSYSERR_NOERROR:
                raise RuntimeError(f"midiOutLongMsg failed, MMRESULT={rc}")
            deadline = time.perf_counter() + 1.0
            while not (hdr.dwFlags & MHDR_DONE) and time.perf_counter() < deadline:
                time.sleep(0.0002)
        finally:
            self.mm.midiOutUnprepareHeader(self.handle, ctypes.byref(hdr), ctypes.sizeof(hdr))

    def close(self) -> None:
        if self.handle:
            try:
                self.mm.midiOutReset(self.handle)
            finally:
                self.mm.midiOutClose(self.handle)
                self.handle = ctypes.c_void_p()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def monitor(port: Optional[str], seconds: float, on_msg, prefer: Optional[str] = "midi") -> int:
    """Open a MIDI input and call on_msg(status, d1, d2) for each short message for `seconds`. Returns count.

    NOTE: never exercised without the physical keyboard attached -- treat as needs-hardware until confirmed.
    """
    mm = _winmm()
    names = inputs()
    idx = _match(names, port, prefer)
    if idx < 0:
        raise RuntimeError(f"no MIDI input matching {port or 'keylab'!r}. Available: {names or '(none)'}")
    count = [0]
    proc = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

    def _cb(h, msg, inst, p1, p2):
        if msg == MIM_DATA and p1 is not None:
            v = int(p1)
            on_msg(v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF)
            count[0] += 1

    cb = proc(_cb)
    mm.midiInOpen.argtypes = [ctypes.POINTER(ctypes.c_void_p), wintypes.UINT, ctypes.c_void_p,
                              ctypes.c_void_p, wintypes.DWORD]
    mm.midiInOpen.restype = wintypes.UINT
    for fn in (mm.midiInStart, mm.midiInStop, mm.midiInClose):
        fn.argtypes = [ctypes.c_void_p]
        fn.restype = wintypes.UINT
    h = ctypes.c_void_p()
    if mm.midiInOpen(ctypes.byref(h), idx, ctypes.cast(cb, ctypes.c_void_p), 0, CALLBACK_FUNCTION) != MMSYSERR_NOERROR:
        raise RuntimeError(f"midiInOpen({names[idx]!r}) failed")
    try:
        mm.midiInStart(h)
        time.sleep(seconds)
        mm.midiInStop(h)
    finally:
        mm.midiInClose(h)
    return count[0]


# --- input with SysEx capture (handshake probe / FL wire) ----------------------------------------
MIM_DATA = 0x3C3
MIM_LONGDATA = 0x3C4


class MidiIn:
    """A MIDI input that captures short AND SysEx messages into .events = [(t_seconds, bytes, kind)].
    Pre-adds buffers and never calls WinMM from the callback (per MS rules) -- good for short captures.
    NOTE: never exercised without the physical keyboard; treat as needs-hardware until confirmed."""

    def __init__(self, port=None, prefer="daw", nbuf=24, bufsize=512):
        self.mm = mm = _winmm()
        self.names = inputs()
        self.index = _match(self.names, port, prefer)
        if self.index < 0:
            raise RuntimeError(f"no MIDI input matching {port or 'keylab'!r}. Available: {self.names or '(none)'}")
        self.name = self.names[self.index]
        self.events: list = []
        self._t0 = 0.0
        mm.midiInOpen.argtypes = [ctypes.POINTER(ctypes.c_void_p), wintypes.UINT, ctypes.c_void_p,
                                  ctypes.c_void_p, wintypes.DWORD]
        mm.midiInOpen.restype = wintypes.UINT
        for fn in (mm.midiInStart, mm.midiInStop, mm.midiInClose, mm.midiInReset):
            fn.argtypes = [ctypes.c_void_p]
            fn.restype = wintypes.UINT
        for fn in (mm.midiInPrepareHeader, mm.midiInUnprepareHeader, mm.midiInAddBuffer):
            fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(MIDIHDR), wintypes.UINT]
            fn.restype = wintypes.UINT
        proc = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_void_p)
        self._cbref = proc(self._cb)  # keep a reference alive
        self.handle = ctypes.c_void_p()
        if mm.midiInOpen(ctypes.byref(self.handle), self.index, ctypes.cast(self._cbref, ctypes.c_void_p),
                         0, CALLBACK_FUNCTION) != MMSYSERR_NOERROR:
            raise RuntimeError(f"midiInOpen({self.name!r}) failed")
        self._hdrs = []
        self._bufs = []
        for _ in range(nbuf):
            buf = ctypes.create_string_buffer(bufsize)
            hdr = MIDIHDR()
            hdr.lpData = ctypes.cast(buf, ctypes.c_char_p)
            hdr.dwBufferLength = bufsize
            mm.midiInPrepareHeader(self.handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
            mm.midiInAddBuffer(self.handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
            self._bufs.append(buf)
            self._hdrs.append(hdr)

    def _cb(self, h, msg, inst, p1, p2):
        t = time.perf_counter() - self._t0
        if msg == MIM_DATA and p1 is not None:
            v = int(p1)
            self.events.append((t, bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF]), "short"))
        elif msg == MIM_LONGDATA and p1 is not None:
            hdr = ctypes.cast(p1, ctypes.POINTER(MIDIHDR)).contents
            n = hdr.dwBytesRecorded
            if n:
                self.events.append((t, ctypes.string_at(hdr.lpData, n), "sysex"))

    def start(self):
        self._t0 = time.perf_counter()
        self.mm.midiInStart(self.handle)

    def stop(self):
        self.mm.midiInStop(self.handle)

    def close(self):
        if self.handle:
            self.mm.midiInReset(self.handle)
            for hdr in self._hdrs:
                self.mm.midiInUnprepareHeader(self.handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
            self.mm.midiInClose(self.handle)
            self.handle = ctypes.c_void_p()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
