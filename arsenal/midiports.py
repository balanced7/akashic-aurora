"""What Windows can see of MIDI, for the piano page's Rescan hint (GET /api/midi/ports).

Read-only. It lists the MIDI 1.0 (WinMM) input and output ports and reports the state of the Windows MIDI Service
(midisrv). Nothing here opens a port or starts a service.

Why the page needs it: Web MIDI can only report what the browser sees. On 2026-10-07 the KeyLab reconnected while Brave
was running. WinMM listed it, Brave did not, and Rescan re-read Brave's stale list in silence. A fresh Brave saw the
KeyLab at once, under the same names WinMM gives (verified that night). So when this snapshot lists a keyboard the page
cannot see, the stale layer is the browser's own list, and the hint can say so instead of guessing.

Design: docs/library/map/20261007_design-night-roadmap-2026-10-07_fa48f2.md (H1). Tests: tests/test_arsenal_midiports.py.
"""
from __future__ import annotations

import re
import subprocess
import sys
from typing import List

SERVICE = "midisrv"
_STATES = {"1": "stopped", "2": "start_pending", "3": "stop_pending", "4": "running"}


def _winmm_names(kind: str) -> List[str]:
    """The WinMM device names for kind "in" or "out". The API caps each name at 31 characters."""
    import ctypes
    from ctypes import wintypes

    class _InCaps(ctypes.Structure):
        _fields_ = [("wMid", wintypes.WORD), ("wPid", wintypes.WORD), ("vDriverVersion", wintypes.UINT),
                    ("szPname", wintypes.WCHAR * 32), ("dwSupport", wintypes.DWORD)]

    class _OutCaps(ctypes.Structure):
        _fields_ = [("wMid", wintypes.WORD), ("wPid", wintypes.WORD), ("vDriverVersion", wintypes.UINT),
                    ("szPname", wintypes.WCHAR * 32), ("wTechnology", wintypes.WORD), ("wVoices", wintypes.WORD),
                    ("wNotes", wintypes.WORD), ("wChannelMask", wintypes.WORD), ("dwSupport", wintypes.DWORD)]

    winmm = ctypes.WinDLL("winmm")
    if kind == "in":
        count, getcaps, caps_type = winmm.midiInGetNumDevs, winmm.midiInGetDevCapsW, _InCaps
    else:
        count, getcaps, caps_type = winmm.midiOutGetNumDevs, winmm.midiOutGetDevCapsW, _OutCaps
    count.restype = wintypes.UINT
    getcaps.argtypes = [ctypes.c_size_t, ctypes.c_void_p, wintypes.UINT]  # uDeviceID is UINT_PTR
    getcaps.restype = wintypes.UINT
    names = []
    for i in range(count()):
        caps = caps_type()
        if getcaps(i, ctypes.byref(caps), ctypes.sizeof(caps)) == 0:  # MMSYSERR_NOERROR
            names.append(caps.szPname)
    return names


def parse_sc_state(text: str) -> str:
    """The service state in `sc query` output: running, stopped, start_pending, stop_pending, absent or unknown."""
    text = text or ""
    if "FAILED 1060" in text:  # ERROR_SERVICE_DOES_NOT_EXIST
        return "absent"
    match = re.search(r"STATE\s*:\s*(\d+)", text)
    return _STATES.get(match.group(1), "unknown") if match else "unknown"


def service_state(name: str = SERVICE) -> str:
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # the server may run windowless: never flash a console
        out = subprocess.run(["sc.exe", "query", name], capture_output=True, text=True, errors="replace",
                             timeout=3, creationflags=flags)
        return parse_sc_state(out.stdout + out.stderr)
    except Exception:
        return "unknown"


def snapshot() -> dict:
    """Everything the hint asks Windows, as JSON-ready data. Never raises."""
    if sys.platform != "win32":
        return {"ok": False, "reason": "not windows"}
    try:
        return {"ok": True, "inputs": _winmm_names("in"), "outputs": _winmm_names("out"),
                "service": {"name": SERVICE, "state": service_state()}}
    except Exception as exc:
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}
