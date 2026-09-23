"""Screenspace foreground source — WinEventHook tracker (§1.1, the v1 shadow-model spine).

Replaces the GetForegroundControl() placeholder in engine._current_focus(). The
placeholder polls a COM call that returns None from any non-interactive context
(measured 2026-09-23 on DESKTOP-5886HDP: uiautomation imports, GetForegroundControl
returns None). This tracker is EVENT-BASED: EVENT_SYSTEM_FOREGROUND feeds a resident
handler thread that keeps the cached focus warm, so L0 pulse reads it in <1ms (§5's
"L0/L3 <5ms server-side" cache claim).

F2 -> v1 BY CONSTRUCTION. WinEventHook is not a poll replacement — it owns the event
stream, which requires the resident handler thread + in-memory model that IS §1.1's
v1 shadow model. Pre-registered fence note pending claude's ratification (the
spec text already makes the call; this file is the implementation, not the ruling).

§1.2 HANDLER DISCIPLINE, encoded: the WinEvent hook callback runs on a system thread
in WINEVENT_OUTOFCONTEXT mode. It must NEVER re-enter UIA from there — so the callback
only records the HWND and signals a worker; the worker resolves the window name (UIA
GetWindowText / ControlFromHandle) OFF the hook thread, then calls the pure
``on_foreground_change(name)`` delivery. UIA is therefore never called on the hook
callback's thread.

Windows-only + fail-soft: SetWinEventHook is ctypes/windll. On non-Windows, or when
the hook can't be set, ``start()`` returns False and the tracker stays inactive
(focus stays None). The pure seam — ``subscribe`` + ``on_foreground_change`` — is
Windows-free and is what the RED event-wiring pins drive with a synthetic name (no
desktop needed to prove the wiring).
"""

from __future__ import annotations

import ctypes
import threading
from typing import Callable, List, Optional

# WinEvent constants ------------------------------------------------------------------
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002


class ForegroundTracker:
    """Event-based foreground source. Pure delivery is testable without Windows."""

    def __init__(self) -> None:
        self._focus: Optional[str] = None
        self._gen: int = 0
        self._observers: List[Callable[[Optional[str]], None]] = []
        self._hook = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._wake = threading.Event()  # signals the worker a hwnd is pending
        self._pending_hwnd: Optional[int] = None

    # ------------------------------------------------------------------ pure seam
    @property
    def focus(self) -> Optional[str]:
        """The cached foreground window name (None until a real change is delivered)."""
        with self._lock:
            return self._focus

    @property
    def gen(self) -> int:
        """Monotone observation ordinal — advances once per delivered change."""
        with self._lock:
            return self._gen

    def subscribe(self, observer: Callable[[Optional[str]], None]) -> None:
        """Register a callback invoked with the new focus name on each delivery."""
        with self._lock:
            self._observers.append(observer)

    def on_foreground_change(self, name: Optional[str]) -> None:
        """Pure delivery: record the RESOLVED foreground name and notify observers.

        The name arrives PRE-RESOLVED — the worker resolves it off the hook thread
        (§1.2) and hands it here. This method never calls UIA, never blocks.
        """
        with self._lock:
            self._focus = name
            self._gen += 1
            observers = list(self._observers)
        for observer in observers:
            observer(name)

    # ------------------------------------------------------------------ Windows adapter
    def start(self) -> bool:
        """Set EVENT_SYSTEM_FOREGROUND hook + pump a message loop on a dedicated thread.

        Fail-soft: returns False (and stays inactive) on non-Windows or when the hook
        cannot be installed. The hook callback only RECORDS the hwnd and wakes the
        worker; the worker resolves the name off-thread and calls on_foreground_change.
        Returns True once the hook is installed and the worker thread is running.
        """
        if self._thread is not None and self._thread.is_alive():
            return True
        if not hasattr(ctypes, "windll"):
            return False
        user32 = ctypes.windll.user32
        if not hasattr(user32, "SetWinEventHook"):
            return False

        self._stop.clear()

        # The callback type WINEVENTPROC(hWinEventHook, event, hwnd, idObject,
        # idChild, dwEventThread, dwmsEventTime). Out-of-context callback: runs on a
        # system thread — MUST NOT re-enter UIA or block. Only record + wake.
        WINEVENTPROC = ctypes.WINFUNCTYPE(
            None,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,  # hwnd
            ctypes.c_long,
            ctypes.c_long,
            ctypes.c_uint,
            ctypes.c_uint,
        )

        def _hook_callback(_h, _event, hwnd, _idobj, _idchild, _thread, _ms):
            # §1.2: never UIA here. Record + wake the worker.
            with self._lock:
                if self._pending_hwnd == hwnd:
                    return  # no new info
                self._pending_hwnd = hwnd
            self._wake.set()

        self._callback = WINEVENTPROC(_hook_callback)  # keep a strong ref (GC safety)
        self._hook = user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND,
            EVENT_SYSTEM_FOREGROUND,
            0,  # hmodWinEventProc (0 = no module)
            self._callback,
            0,  # idProcess (0 = all)
            0,  # idThread (0 = all)
            WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
        )
        if not self._hook:
            return False

        self._thread = threading.Thread(target=self._run, name="screenspace-foreground", daemon=True)
        self._thread.start()
        return True

    def _resolve_name(self, hwnd: int) -> Optional[str]:
        """Resolve an HWND to a window name via UIA, OFF the hook thread (§1.2)."""
        try:
            import uiautomation as auto  # type: ignore

            control = auto.ControlFromHandle(hwnd)
            return control.Name if control else None
        except Exception:  # noqa: BLE001
            return None  # defer to None rather than throw on the worker

    def _run(self) -> None:
        """Worker thread: pump messages + resolve pending hwnd -> name -> deliver."""
        user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None
        wintypes = None
        if hasattr(ctypes, "wintypes"):
            wintypes = ctypes.wintypes
        else:
            try:
                import ctypes.wintypes as wintypes  # noqa: F811
            except Exception:  # noqa: BLE001
                wintypes = None
        msg = wintypes.MSG() if wintypes is not None else None

        while not self._stop.is_set():
            # Drain pending hwnds -> resolve off-thread -> pure delivery.
            with self._lock:
                pending = self._pending_hwnd
                self._pending_hwnd = None
            if pending is not None:
                self.on_foreground_change(self._resolve_name(pending))

            # Pump the window message queue (WinEventHook out-of-context callbacks
            # are delivered to this thread's queue; without a pump they stall).
            if user32 and msg is not None:
                while user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):  # PM_REMOVE
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))

            self._wake.wait(timeout=0.05)
            self._wake.clear()

    def stop(self) -> None:
        """Unhook + join the worker thread (idempotent)."""
        self._stop.set()
        self._wake.set()
        if self._hook and hasattr(ctypes, "windll"):
            try:
                ctypes.windll.user32.UnhookWinEvent(self._hook)
            except Exception:  # noqa: BLE001
                pass
            self._hook = None
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        self._callback = None
