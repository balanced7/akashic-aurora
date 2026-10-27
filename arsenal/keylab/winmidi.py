"""WinMM MIDI output (and input with SysEx capture) via ctypes -- no external MIDI dependency.

Same approach as arsenal.midiports (which enumerates WinMM read-only); this adds the send side:
  midiOutShortMsg  -- notes/CC (3-byte messages)
  midiOutLongMsg   -- SysEx (the pad-colour / screen / handshake commands)

Windows only. Ports are opened by NAME SUBSTRING (case-insensitive); the mk3 exposes several ports and which
one accepts the DAW SysEx is a bench question, so the caller can pass an explicit --port substring.

Every WinMM result code is checked: a failing call raises WinMMError (a RuntimeError naming the function, the port
and the MMRESULT), and MidiOut keeps the codes and timing of its last 256 sends in `.sends` for a watchdog to read.
Memory the driver may still own (a SysEx buffer it has not handed back, an input callback after a failed close) is
never freed: it is parked, and reclaimed only once the driver lets go. The rules followed are Microsoft's (Learn:
midiOutLongMsg, midiOutUnprepareHeader, midiInAddBuffer, MidiInProc) and the Windows MIDI Services issues cited in
research/reviewed/keylab-liberation-2026-10-22/keylab-dev-guidance-and-hang-guide-2026-10-27.md, section 4.1.
"""
from __future__ import annotations

import ctypes
import queue
import sys
import threading
import time
from collections import deque
from ctypes import wintypes
from typing import Deque, Dict, List, Optional

MMSYSERR_NOERROR = 0
MMSYSERR_ERROR = 1           # Windows MIDI Services: the send to the device waited more than 1 s (MidiXProc)
MMSYSERR_NODRIVER = 6        # the device left (and maybe came back): close, wait 2-3 s, reopen by name
MMSYSERR_INVALPARAM = 11
MIDIERR_UNPREPARED = 64
MIDIERR_STILLPLAYING = 65    # the driver still owns a buffer
CALLBACK_NULL = 0
CALLBACK_FUNCTION = 0x00030000
MHDR_DONE = 0x00000001
MHDR_PREPARED = 0x00000002
MHDR_INQUEUE = 0x00000004
MIM_DATA = 0x3C3
MIM_LONGDATA = 0x3C4
MIM_ERROR = 0x3C5
MIM_LONGERROR = 0x3C6

_RC_NAMES = {MMSYSERR_ERROR: "MMSYSERR_ERROR", 2: "MMSYSERR_BADDEVICEID", 4: "MMSYSERR_ALLOCATED",
             5: "MMSYSERR_INVALHANDLE", MMSYSERR_NODRIVER: "MMSYSERR_NODRIVER", 7: "MMSYSERR_NOMEM",
             MMSYSERR_INVALPARAM: "MMSYSERR_INVALPARAM", MIDIERR_UNPREPARED: "MIDIERR_UNPREPARED",
             MIDIERR_STILLPLAYING: "MIDIERR_STILLPLAYING", 67: "MIDIERR_NOTREADY"}

_FUNCTYPE = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)   # CFUNCTYPE only so tests import it off Windows
_MIDIINPROC = _FUNCTYPE(None, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

# Objects the driver may still touch after we gave up on them (a callback it may still call, buffers it has not
# handed back): kept alive for the life of the process rather than freed under it. An output header goes in the
# moment it is parked, so it outlives its MidiOut even when a caller drops that MidiOut without close(); it comes
# out again only once the driver has handed it back and it has been unprepared.
_KEPT_ALIVE: list = []
_KEPT_LOCK = threading.Lock()


def _keep(entry) -> None:
    with _KEPT_LOCK:
        _KEPT_ALIVE.append(entry)


def _release(entry) -> None:
    with _KEPT_LOCK:
        for i in range(len(_KEPT_ALIVE) - 1, -1, -1):
            if _KEPT_ALIVE[i] is entry:
                del _KEPT_ALIVE[i]
                return


def rc_name(rc: int) -> str:
    return _RC_NAMES.get(rc, "MMRESULT")


class WinMMError(RuntimeError):
    """A WinMM call returned an error. `.fn`, `.rc` and `.port` say which; `.codes` holds every step of a close."""

    def __init__(self, fn: str, rc: int, port: Optional[str] = None, note: str = "",
                 codes: Optional[Dict[str, int]] = None):
        self.fn, self.rc, self.port, self.codes = fn, rc, port, dict(codes or {})
        where = f"({port!r})" if port else ""
        tail = f": {note}" if note else ""
        super().__init__(f"{fn}{where} failed, MMRESULT={rc} ({rc_name(rc)}){tail}")


class SysexTimeout(RuntimeError):
    """midiOutLongMsg took the buffer and the driver did not hand it back (done flag) in time. The buffer is kept,
    not freed, and reclaimed once the driver lets go."""


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
    # lpData is a plain pointer: c_char_p would read a buffer only up to its first 00 byte, and every Arturia
    # SysEx carries 00 (the maker ID is 00 20 6B), so a captured identity reply came back cut and padded with junk.
    _fields_ = [("lpData", ctypes.c_void_p), ("dwBufferLength", wintypes.DWORD),
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


def _report(what: str, codes: Dict[str, int]) -> Dict[str, int]:
    """One stderr line for a close that did not go cleanly (callers often swallow the exception), and the failures."""
    failed = {k: v for k, v in codes.items() if v}
    if failed:
        print(f"winmidi: {what}: " + ", ".join(f"{k}={v} ({rc_name(v)})" for k, v in failed.items()), file=sys.stderr)
    return failed


class MidiOut:
    """An open WinMM output. Use as a context manager. send_sysex() blocks until the driver hands the buffer back.

    Every SysEx passes the port's governor (governor.PortGovernor: at most 12 midiOutLongMsg calls in any 100 ms on
    this port, counted across every process on the machine and checked around the call itself). Pass governor=False
    only for a deliberate limit probe such as `ledbench burst`. `done_timeout` bounds the wait for the driver to hand
    a sent buffer back. Close it when done: a buffer the driver has not handed back is kept for the life of the
    process either way, but only close() gives the port handle back."""

    DONE_TIMEOUT_S = 1.0
    SEND_LOG = 256

    def __init__(self, port: Optional[str] = None, prefer: Optional[str] = "daw", governor=None,
                 done_timeout: Optional[float] = None):
        self.mm = _winmm()
        self.names = outputs()
        self.index = _match(self.names, port, prefer)
        if self.index < 0:
            where = f"matching {port!r}" if port else "named like 'KeyLab'"
            raise RuntimeError(f"no MIDI output {where}. Available: {self.names or '(none)'}")
        self.name = self.names[self.index]
        self.done_timeout = self.DONE_TIMEOUT_S if done_timeout is None else float(done_timeout)
        self.sends: Deque[dict] = deque(maxlen=self.SEND_LOG)   # the codes and timing of each recent send
        self.close_codes: Dict[str, int] = {}
        self._parked: list = []                                 # (header, buffer) the driver has not handed back
        self._io = threading.Lock()
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
            raise WinMMError("midiOutOpen", rc, self.name)
        # One budget per PORT, shared with every other process sending to it (built once the port is known).
        if governor is None:
            from .governor import PortGovernor
            governor = PortGovernor(self.name)
        self.governor = governor or None

    @property
    def parked(self) -> int:
        """Sent buffers the driver has not handed back yet (kept alive, never freed under it)."""
        return len(self._parked)

    def send_short(self, status: int, data1: int, data2: int) -> None:
        msg = (status & 0xFF) | ((data1 & 0xFF) << 8) | ((data2 & 0xFF) << 16)
        rc = self.mm.midiOutShortMsg(self.handle, msg)
        if rc != MMSYSERR_NOERROR:
            raise WinMMError("midiOutShortMsg", rc, self.name)

    def send_sysex(self, data: bytes) -> dict:
        """Send one SysEx and return its record: {t, n, prepare, send, unprepare, done, wait_s} (the MMRESULT of each
        step; None for a step not reached). Raises WinMMError on any failing step and SysexTimeout when the driver
        does not hand the buffer back within done_timeout; the record is in .sends either way.

        The governor acts twice: admit() first, before anything touches the driver (the port's next free slot), then
        gate() around the midiOutLongMsg call itself, which is what holds the ceiling where the device is: a send
        whose Python ran late after its slot still waits its turn there."""
        if self.governor is not None:          # first: nothing touches the driver before the ceiling admits it
            self.governor.admit()
        gate = getattr(self.governor, "gate", None) if self.governor is not None else None
        payload = bytes(data)
        with self._io:
            self._reclaim()
            buf = ctypes.create_string_buffer(payload, len(payload))
            hdr = MIDIHDR()
            hdr.lpData = ctypes.cast(buf, ctypes.c_void_p)
            hdr.dwBufferLength = len(payload)
            hdr.dwBytesRecorded = len(payload)
            t0 = time.perf_counter()
            rec = {"t": t0, "n": len(payload), "prepare": None, "send": None, "unprepare": None, "done": None,
                   "wait_s": None}
            self.sends.append(rec)
            size = ctypes.sizeof(hdr)
            rec["prepare"] = rc = self.mm.midiOutPrepareHeader(self.handle, ctypes.byref(hdr), size)
            if rc != MMSYSERR_NOERROR:
                raise WinMMError("midiOutPrepareHeader", rc, self.name)

            def long_msg() -> int:
                rec["send"] = code = self.mm.midiOutLongMsg(self.handle, ctypes.byref(hdr), size)
                return code

            try:
                rc = gate(long_msg) if gate is not None else long_msg()
                # On today's Windows MIDI Services the call is synchronous and the done flag is already set here; a
                # legacy or vendor driver may still be sending, and then the buffer is still the driver's.
                deadline = t0 + self.done_timeout
                while rc == MMSYSERR_NOERROR and not (hdr.dwFlags & MHDR_DONE) and time.perf_counter() < deadline:
                    time.sleep(0.0002)
            except BaseException:
                self._give_back(hdr, buf, rec)  # interrupted between the prepare and the done flag (Ctrl-C included)
                raise
            if rc != MMSYSERR_NOERROR:
                self._give_back(hdr, buf, rec)  # not queued: the header is ours again
                raise WinMMError("midiOutLongMsg", rc, self.name)
            rec["done"] = bool(hdr.dwFlags & MHDR_DONE)
            rec["wait_s"] = time.perf_counter() - t0
            if not rec["done"]:
                self._park(hdr, buf)
                raise SysexTimeout(f"midiOutLongMsg({self.name!r}): the driver has not handed the buffer back after "
                                   f"{self.done_timeout:g} s (kept, not freed; {len(self._parked)} parked)")
            rec["unprepare"] = rc = self.mm.midiOutUnprepareHeader(self.handle, ctypes.byref(hdr), size)
            if rc != MMSYSERR_NOERROR:
                self._park(hdr, buf)
                raise WinMMError("midiOutUnprepareHeader", rc, self.name)
            return rec

    def _park(self, hdr, buf) -> None:
        """The driver may still own this header: keep it, and its buffer, for the life of the process from this
        moment (module-level _KEPT_ALIVE), so dropping this MidiOut without close() cannot free them under the
        driver. _reclaim() lets go once the driver has handed it back and it has been unprepared."""
        entry = (hdr, buf)
        self._parked.append(entry)
        _keep(entry)

    def _give_back(self, hdr, buf, rec: dict) -> None:
        """A prepared header that did not finish a normal send. If the driver took it (the send returned 0) it is
        parked as it is; otherwise it is unprepared now, and parked if even that fails (a driver that still owns
        it refuses the unprepare with MIDIERR_STILLPLAYING, so a send cut off before its code was stored is safe)."""
        if rec.get("send") == MMSYSERR_NOERROR:
            self._park(hdr, buf)
            return
        rec["unprepare"] = urc = self.mm.midiOutUnprepareHeader(self.handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
        if urc != MMSYSERR_NOERROR:
            self._park(hdr, buf)

    def _reclaim(self) -> List[int]:
        """Unprepare parked headers the driver has handed back since. Returns the failing codes (still parked)."""
        still, bad = [], []
        for entry in self._parked:
            hdr = entry[0]
            if hdr.dwFlags & MHDR_DONE:
                rc = self.mm.midiOutUnprepareHeader(self.handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
                if rc == MMSYSERR_NOERROR:
                    _release(entry)
                    continue
                bad.append(rc)
            still.append(entry)
        self._parked = still
        return bad

    def close(self, strict: bool = False) -> Dict[str, int]:
        """Reset (the driver hands back every queued buffer), unprepare what came back, close. Returns each step's
        code (also in .close_codes); a failing step prints one line on stderr, and raises WinMMError if `strict`.
        Whatever the driver may still own is kept alive for the life of the process."""
        if not self.handle:
            return {}
        codes: Dict[str, int] = {}
        with self._io:
            codes["midiOutReset"] = self.mm.midiOutReset(self.handle)
            bad = self._reclaim()
            for hdr, _buf in self._parked:                  # not even marked done after the reset
                bad.append(MIDIERR_STILLPLAYING)
            codes["midiOutUnprepareHeader"] = bad[0] if bad else MMSYSERR_NOERROR
            codes["midiOutClose"] = self.mm.midiOutClose(self.handle)
            if self._parked or codes["midiOutClose"] != MMSYSERR_NOERROR:
                _keep((self.handle.value, list(self._parked)))   # the parked headers are already kept, each
            self._parked = []
            self.handle = ctypes.c_void_p()
        gov_close = getattr(self.governor, "close", None)
        if gov_close is not None:
            gov_close()
        self.close_codes = codes
        failed = _report(f"closing output {self.name!r}", codes)
        if failed and strict:
            fn, rc = next(iter(failed.items()))
            raise WinMMError(fn, rc, self.name, codes=codes)
        return codes

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

    def _cb(h, msg, inst, p1, p2):
        if msg == MIM_DATA and p1 is not None:
            v = int(p1)
            on_msg(v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF)
            count[0] += 1

    cb = _MIDIINPROC(_cb)
    mm.midiInOpen.argtypes = [ctypes.POINTER(ctypes.c_void_p), wintypes.UINT, ctypes.c_void_p,
                              ctypes.c_void_p, wintypes.DWORD]
    mm.midiInOpen.restype = wintypes.UINT
    for fn in (mm.midiInStart, mm.midiInStop, mm.midiInClose):
        fn.argtypes = [ctypes.c_void_p]
        fn.restype = wintypes.UINT
    h = ctypes.c_void_p()
    rc = mm.midiInOpen(ctypes.byref(h), idx, ctypes.cast(cb, ctypes.c_void_p), 0, CALLBACK_FUNCTION)
    if rc != MMSYSERR_NOERROR:
        raise WinMMError("midiInOpen", rc, names[idx])
    try:
        mm.midiInStart(h)
        time.sleep(seconds)
        mm.midiInStop(h)
    finally:
        if mm.midiInClose(h) != MMSYSERR_NOERROR:
            _keep((h.value, cb))
    return count[0]


# --- input with SysEx capture (handshake probe / FL wire / long-lived listeners) -----------------------------------

class MidiIn:
    """A MIDI input that captures short AND SysEx messages into .events = [(t_seconds, bytes, kind)].

    Long-lived: each SysEx buffer the driver hands back is queued again (midiInAddBuffer) from a small re-queue
    thread, never from the callback (Microsoft, MidiInProc: calling multimedia functions there "can cause a
    deadlock"), so a listener that runs for days never runs out of buffers and never reports a false silence.
    start() waits `settle_s` (20 ms) after midiInStart, because Windows MIDI Services drops messages stamped before
    the start (microsoft/MIDI #1263): a probe sent at once can lose its reply. close() stops, resets, unprepares and
    closes, in that order, and checks every code (raises WinMMError if `strict`).

    Subclasses replace `_cb(h, msg, inst, p1, p2)` to handle messages their own way (vj.LiveIn pushes them); the
    buffer bookkeeping lives in `_dispatch` and runs either way. A SysEx longer than `bufsize` arrives in pieces.

    Tested without hardware against a fake winmm (tests/test_keylab_winmidi.py: whole replies, 30 replies through 4
    buffers, no WinMM call on the callback thread, close order and codes). Still to confirm on the device: that
    Windows MIDI Services hands buffers back the same way, on its own thread, under a long session."""

    SETTLE_S = 0.02

    def __init__(self, port=None, prefer="daw", nbuf=24, bufsize=512, settle_s: Optional[float] = None):
        self.mm = mm = _winmm()
        self.names = inputs()
        self.index = _match(self.names, port, prefer)
        if self.index < 0:
            raise RuntimeError(f"no MIDI input matching {port or 'keylab'!r}. Available: {self.names or '(none)'}")
        self.name = self.names[self.index]
        self.settle_s = self.SETTLE_S if settle_s is None else max(0.0, float(settle_s))
        self.events: list = []
        self._t0 = 0.0
        self.requeued = 0                      # buffers handed back and queued again
        self.requeue_errors: List[int] = []    # MMRESULTs of failed re-queues (the input would go deaf to SysEx)
        self.long_errors = 0                   # MIM_LONGERROR: an invalid or cut SysEx came back
        self.close_codes: Dict[str, int] = {}
        self.last_stop_rc: Optional[int] = None
        self._closing = False
        self._returned: "queue.SimpleQueue[Optional[int]]" = queue.SimpleQueue()
        self._io = threading.Lock()
        self._hdrs: list = []
        self._bufs: list = []
        self._by_addr: Dict[int, MIDIHDR] = {}
        mm.midiInOpen.argtypes = [ctypes.POINTER(ctypes.c_void_p), wintypes.UINT, ctypes.c_void_p,
                                  ctypes.c_void_p, wintypes.DWORD]
        mm.midiInOpen.restype = wintypes.UINT
        for fn in (mm.midiInStart, mm.midiInStop, mm.midiInClose, mm.midiInReset):
            fn.argtypes = [ctypes.c_void_p]
            fn.restype = wintypes.UINT
        for fn in (mm.midiInPrepareHeader, mm.midiInUnprepareHeader, mm.midiInAddBuffer):
            fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(MIDIHDR), wintypes.UINT]
            fn.restype = wintypes.UINT
        self._cbref = _MIDIINPROC(self._dispatch)  # keep a reference alive
        self.handle = ctypes.c_void_p()
        rc = mm.midiInOpen(ctypes.byref(self.handle), self.index, ctypes.cast(self._cbref, ctypes.c_void_p),
                           0, CALLBACK_FUNCTION)
        if rc != MMSYSERR_NOERROR:
            raise WinMMError("midiInOpen", rc, self.name)
        try:
            for _ in range(nbuf):
                buf = ctypes.create_string_buffer(bufsize)
                hdr = MIDIHDR()
                hdr.lpData = ctypes.cast(buf, ctypes.c_void_p)
                hdr.dwBufferLength = bufsize
                self._bufs.append(buf)
                self._hdrs.append(hdr)
                self._by_addr[ctypes.addressof(hdr)] = hdr
                rc = mm.midiInPrepareHeader(self.handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
                if rc != MMSYSERR_NOERROR:
                    raise WinMMError("midiInPrepareHeader", rc, self.name)
                rc = mm.midiInAddBuffer(self.handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
                if rc != MMSYSERR_NOERROR:
                    raise WinMMError("midiInAddBuffer", rc, self.name)
        except Exception:
            self.close(strict=False)
            raise
        self._requeuer = threading.Thread(target=self._requeue_loop, name=f"midiin-requeue {self.name}",
                                          daemon=True)
        self._requeuer.start()

    # --- the driver's thread: no WinMM calls here ------------------------------------------------------------------
    def _dispatch(self, h, msg, inst, p1, p2):
        try:
            self._cb(h, msg, inst, p1, p2)
        finally:
            if msg in (MIM_LONGDATA, MIM_LONGERROR) and p1:
                if msg == MIM_LONGERROR:
                    self.long_errors += 1
                if not self._closing:
                    self._returned.put(int(p1))      # the re-queue thread gives it back to the driver

    def _cb(self, h, msg, inst, p1, p2):
        t = time.perf_counter() - self._t0
        if msg == MIM_DATA and p1 is not None:
            v = int(p1)
            self.events.append((t, bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF]), "short"))
        elif msg == MIM_LONGDATA and p1:
            hdr = ctypes.cast(p1, ctypes.POINTER(MIDIHDR)).contents
            n = hdr.dwBytesRecorded
            if n and hdr.lpData:
                self.events.append((t, ctypes.string_at(hdr.lpData, n), "sysex"))   # copied before it is re-queued

    # --- the re-queue thread ---------------------------------------------------------------------------------------
    def _requeue_loop(self):
        while True:
            addr = self._returned.get()
            if addr is None:
                return
            hdr = self._by_addr.get(addr)
            if hdr is None:
                continue
            with self._io:
                if self._closing or not self.handle:
                    continue
                hdr.dwBytesRecorded = 0
                rc = self.mm.midiInAddBuffer(self.handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
            if rc == MMSYSERR_NOERROR:
                self.requeued += 1
            else:
                self.requeue_errors.append(rc)

    @property
    def buffers_queued(self) -> int:
        """Buffers the driver holds right now, by the INQUEUE flag (diagnostic; depends on the driver setting it)."""
        return sum(1 for h in self._hdrs if h.dwFlags & MHDR_INQUEUE)

    def start(self):
        self._t0 = time.perf_counter()
        rc = self.mm.midiInStart(self.handle)
        if rc != MMSYSERR_NOERROR:
            raise WinMMError("midiInStart", rc, self.name)
        if self.settle_s:
            time.sleep(self.settle_s)          # replies stamped before the start settles are dropped (MIDI #1263)

    def stop(self) -> int:
        """midiInStop. Returns its code instead of raising, so `m.stop(); m.close()` always reaches close()."""
        self.last_stop_rc = rc = self.mm.midiInStop(self.handle) if self.handle else MMSYSERR_NOERROR
        return rc

    def close(self, strict: bool = True) -> Dict[str, int]:
        """Stop, reset (the driver hands back every queued buffer), unprepare, close, checking every code. Returns
        the codes (also in .close_codes). A failing step prints one line on stderr and, if `strict`, raises
        WinMMError after every step has been tried. Whatever the driver may still own (after a power cycle the
        handle can leak: microsoft/MIDI #1157) is kept alive for the life of the process, never freed."""
        if not self.handle:
            return {}
        with self._io:
            self._closing = True               # from here, buffers handed back stay with us
        self._returned.put(None)
        requeuer = getattr(self, "_requeuer", None)
        if requeuer is not None and requeuer is not threading.current_thread():
            requeuer.join(timeout=2.0)
        codes: Dict[str, int] = {}
        codes["midiInStop"] = self.mm.midiInStop(self.handle)
        codes["midiInReset"] = self.mm.midiInReset(self.handle)
        unprep = [self.mm.midiInUnprepareHeader(self.handle, ctypes.byref(h), ctypes.sizeof(h)) for h in self._hdrs]
        bad = [rc for rc in unprep if rc != MMSYSERR_NOERROR]
        codes["midiInUnprepareHeader"] = bad[0] if bad else MMSYSERR_NOERROR
        codes["midiInClose"] = self.mm.midiInClose(self.handle)
        if bad or codes["midiInClose"] != MMSYSERR_NOERROR:
            _keep((self.handle.value, self._cbref, self._hdrs, self._bufs))
        self.handle = ctypes.c_void_p()
        self.close_codes = codes
        failed = _report(f"closing input {self.name!r}", codes)
        if failed and strict:
            fn, rc = next(iter(failed.items()))
            raise WinMMError(fn, rc, self.name, note="; ".join(f"{k}={v}" for k, v in failed.items()), codes=codes)
        return codes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *a):
        self.close(strict=exc_type is None)
