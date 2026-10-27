"""A stand-in for winmm.dll, so arsenal/keylab/winmidi.py can be tested with no keyboard and no MIDI port.

Swap it in with `monkeypatch.setattr(W, "_winmm", lambda: fake)`. It keeps the driver's half of the WinMM contract
as Microsoft documents it (Learn: midiInAddBuffer, midiOutLongMsg, midiOutUnprepareHeader, MidiInProc):

  - a header must be prepared before it is queued (MIDIERR_UNPREPARED, 64, otherwise);
  - a queued header the driver has not handed back cannot be unprepared: the call returns MIDIERR_STILLPLAYING (65)
    and lands in `refused_unprepares` (an app that then drops the buffer frees memory the driver may still write);
  - an input buffer comes back to the app through the callback, MIM_LONGDATA with the header's address, on the
    driver's own thread; midiInReset hands every queued buffer back the same way, with 0 bytes recorded;
  - a SysEx that starts while no input buffer is queued is dropped (`dropped`), as Windows MIDI Services does;
  - any WinMM call made from inside the callback is recorded in `violations` (MidiInProc: "can cause a deadlock").

`rc[name] = code` makes one function return that code and do nothing else, for the error paths. Every call lands in
`calls` as (name, perf_counter time), in order. SysEx bytes are written into the buffer's memory at the address the
header holds, whatever ctypes type winmidi declares `lpData` as, and read back the same way.
"""
from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes
from typing import Dict, List, Optional, Tuple

MMSYSERR_NOERROR = 0
MMSYSERR_ERROR = 1
MMSYSERR_NODRIVER = 6
MMSYSERR_INVALPARAM = 11
MIDIERR_UNPREPARED = 64
MIDIERR_STILLPLAYING = 65
MHDR_DONE, MHDR_PREPARED, MHDR_INQUEUE = 0x1, 0x2, 0x4
MIM_DATA, MIM_LONGDATA = 0x3C3, 0x3C4

_FUNCTYPE = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
MIDIINPROC = _FUNCTYPE(None, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

OUT_HANDLE, IN_HANDLE = 0x0D0, 0x1D0


def _obj(arg):
    """The ctypes object behind a byref() argument (or the argument itself)."""
    return getattr(arg, "_obj", arg)


def buffer_address(hdr) -> Optional[int]:
    """The header's lpData as an address, whatever ctypes type the field is declared with."""
    return ctypes.c_void_p.from_buffer(hdr, type(hdr).lpData.offset).value


class FakeWinMM:
    FUNCS = ("midiOutGetNumDevs", "midiOutGetDevCapsW", "midiInGetNumDevs", "midiInGetDevCapsW",
             "midiOutOpen", "midiOutShortMsg", "midiOutPrepareHeader", "midiOutLongMsg", "midiOutUnprepareHeader",
             "midiOutReset", "midiOutClose",
             "midiInOpen", "midiInPrepareHeader", "midiInUnprepareHeader", "midiInAddBuffer", "midiInStart",
             "midiInStop", "midiInReset", "midiInClose")

    def __init__(self, outs=("KeyLab 88 mk3 MIDI", "KeyLab 88 mk3 DAW"),
                 ins=("KeyLab 88 mk3 MIDI", "KeyLab 88 mk3 DAW"), out_done_on_send: bool = True):
        self.out_names, self.in_names = list(outs), list(ins)
        self.out_done_on_send = out_done_on_send
        self.calls: List[Tuple[str, float]] = []
        self.rc: Dict[str, int] = {}
        self.violations: List[str] = []                    # WinMM calls made from inside the input callback
        self.refused_unprepares: List[str] = []            # unprepare tried on a header the driver still owns
        self.long_msgs: List[Tuple[float, bytes]] = []     # every SysEx midiOutLongMsg accepted
        self.out_pending: list = []                        # output headers queued, not yet handed back
        self.out_unprepared: List[int] = []                # addresses of output headers unprepared
        self.in_queue: list = []                           # input headers queued by midiInAddBuffer, FIFO
        self.in_cb = None
        self.in_open = False
        self.out_open = False
        self.started_at: Optional[float] = None
        self.dropped = 0
        self._tl = threading.local()
        self._cv = threading.Condition()
        for name in self.FUNCS:
            impl = getattr(self, "_" + name)

            def fn(*a, _impl=impl, _name=name):
                return self._call(_name, _impl, *a)
            fn.__name__ = name
            setattr(self, name, fn)        # plain function attributes: winmidi sets argtypes/restype on them

    # --- bookkeeping ---------------------------------------------------------------------------------------------
    def _call(self, name, impl, *a):
        self.calls.append((name, time.perf_counter()))
        if getattr(self._tl, "in_cb", False):
            self.violations.append(f"{name} called from inside the MIDI input callback")
        if name in self.rc:
            return self.rc[name]
        return impl(*a)

    def names(self) -> List[str]:
        return [n for n, _t in self.calls]

    def first(self, name: str) -> int:
        return self.names().index(name)

    # --- enumeration ---------------------------------------------------------------------------------------------
    def _midiOutGetNumDevs(self):
        return len(self.out_names)

    def _midiInGetNumDevs(self):
        return len(self.in_names)

    def _midiOutGetDevCapsW(self, i, caps, size):
        _obj(caps).szPname = self.out_names[i]
        return MMSYSERR_NOERROR

    def _midiInGetDevCapsW(self, i, caps, size):
        _obj(caps).szPname = self.in_names[i]
        return MMSYSERR_NOERROR

    # --- output --------------------------------------------------------------------------------------------------
    def _midiOutOpen(self, handle, index, cb, inst, flags):
        _obj(handle).value = OUT_HANDLE
        self.out_open = True
        return MMSYSERR_NOERROR

    def _midiOutShortMsg(self, h, msg):
        return MMSYSERR_NOERROR

    def _midiOutPrepareHeader(self, h, hdr, size):
        _obj(hdr).dwFlags |= MHDR_PREPARED
        return MMSYSERR_NOERROR

    def _midiOutLongMsg(self, h, hdr, size):
        hd = _obj(hdr)
        if not hd.dwFlags & MHDR_PREPARED:
            return MIDIERR_UNPREPARED
        self.long_msgs.append((time.perf_counter(), ctypes.string_at(buffer_address(hd), hd.dwBufferLength)))
        if self.out_done_on_send:
            hd.dwFlags |= MHDR_DONE
        else:
            hd.dwFlags = (hd.dwFlags | MHDR_INQUEUE) & ~MHDR_DONE
            self.out_pending.append(hd)
        return MMSYSERR_NOERROR

    def finish_output(self) -> None:
        """The driver gets round to the queued output buffers and hands them back."""
        for hd in self.out_pending:
            hd.dwFlags = (hd.dwFlags | MHDR_DONE) & ~MHDR_INQUEUE
        self.out_pending.clear()

    def _midiOutUnprepareHeader(self, h, hdr, size):
        hd = _obj(hdr)
        if hd.dwFlags & MHDR_INQUEUE:
            self.refused_unprepares.append("out")
            return MIDIERR_STILLPLAYING
        hd.dwFlags &= ~MHDR_PREPARED
        self.out_unprepared.append(ctypes.addressof(hd))
        return MMSYSERR_NOERROR

    def _midiOutReset(self, h):
        self.finish_output()
        return MMSYSERR_NOERROR

    def _midiOutClose(self, h):
        if self.out_pending:
            return MIDIERR_STILLPLAYING
        self.out_open = False
        return MMSYSERR_NOERROR

    # --- input ---------------------------------------------------------------------------------------------------
    def _midiInOpen(self, handle, index, cb, inst, flags):
        addr = cb.value if isinstance(cb, ctypes.c_void_p) else int(cb)
        self.in_cb = MIDIINPROC(addr)
        _obj(handle).value = IN_HANDLE
        self.in_open = True
        return MMSYSERR_NOERROR

    def _midiInPrepareHeader(self, h, hdr, size):
        _obj(hdr).dwFlags |= MHDR_PREPARED
        return MMSYSERR_NOERROR

    def _midiInUnprepareHeader(self, h, hdr, size):
        hd = _obj(hdr)
        if hd.dwFlags & MHDR_INQUEUE:
            self.refused_unprepares.append("in")
            return MIDIERR_STILLPLAYING
        hd.dwFlags &= ~MHDR_PREPARED
        return MMSYSERR_NOERROR

    def _midiInAddBuffer(self, h, hdr, size):
        hd = _obj(hdr)
        if not hd.dwFlags & MHDR_PREPARED:
            return MIDIERR_UNPREPARED
        with self._cv:
            hd.dwFlags = (hd.dwFlags | MHDR_INQUEUE) & ~MHDR_DONE
            self.in_queue.append(hd)
            self._cv.notify_all()
        return MMSYSERR_NOERROR

    def _midiInStart(self, h):
        self.started_at = time.perf_counter()
        return MMSYSERR_NOERROR

    def _midiInStop(self, h):
        return MMSYSERR_NOERROR

    def _midiInReset(self, h):
        with self._cv:
            back, self.in_queue = list(self.in_queue), []
        for hd in back:                                  # every queued buffer comes back, empty
            hd.dwBytesRecorded = 0
            hd.dwFlags = (hd.dwFlags | MHDR_DONE) & ~MHDR_INQUEUE
            self._fire(MIM_LONGDATA, ctypes.addressof(hd))
        return MMSYSERR_NOERROR

    def _midiInClose(self, h):
        if self.in_queue:
            return MIDIERR_STILLPLAYING
        self.in_open = False
        return MMSYSERR_NOERROR

    # --- the device side -----------------------------------------------------------------------------------------
    def _fire(self, msg, p1) -> None:
        """Call the app's MidiInProc on a driver thread, as Windows does, and wait for it to return."""
        def run():
            self._tl.in_cb = True
            try:
                self.in_cb(IN_HANDLE, msg, 0, p1, 0)
            finally:
                self._tl.in_cb = False
        t = threading.Thread(target=run, name="fake-winmm-driver")
        t.start()
        t.join(timeout=5)

    def queued(self) -> int:
        with self._cv:
            return len(self.in_queue)

    def wait_queued(self, n: int = 1, timeout: float = 1.0) -> bool:
        with self._cv:
            return self._cv.wait_for(lambda: len(self.in_queue) >= n, timeout=timeout)

    def send_short(self, status: int, d1: int, d2: int) -> None:
        self._fire(MIM_DATA, (status & 0xFF) | ((d1 & 0xFF) << 8) | ((d2 & 0xFF) << 16))

    def send_sysex(self, data: bytes, wait: float = 0.5) -> bool:
        """The device sends one SysEx. It lands in the oldest queued buffer, or is dropped if none is queued."""
        if wait:
            self.wait_queued(1, timeout=wait)
        with self._cv:
            hd = self.in_queue.pop(0) if self.in_queue else None
        if hd is None:
            self.dropped += 1
            return False
        data = bytes(data)
        ctypes.memmove(buffer_address(hd), data, len(data))
        hd.dwBytesRecorded = len(data)
        hd.dwFlags = (hd.dwFlags | MHDR_DONE) & ~MHDR_INQUEUE
        self._fire(MIM_LONGDATA, ctypes.addressof(hd))
        return True
