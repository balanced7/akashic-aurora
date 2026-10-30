"""arsenal.keylab.nowplaying -- Windows' now-playing (SMTC) from ONE long-lived session manager per process.

Why (measured 2026-10-29): the play tracker asked GlobalSystemMediaTransportControlsSessionManager.request_async()
for a NEW manager every 2 s and enumerated every session each time, and beatsync.now_playing() asked for one per call
under the VJ engine's 2 s track thread. Windows' NPSMSvc ran at 322-404 % of one core; suspending the tracker alone
dropped it to 0 %.

How: one daemon thread with its own asyncio event loop owns every WinRT object. It asks for the manager once,
subscribes to the manager's sessions_changed and current_session_changed and, on each session it follows, to
media_properties_changed and playback_info_changed (never timeline_properties_changed: that one fires every second
while playing). A WinRT event arrives on a WinRT thread and only marks what went stale and wakes the owner thread,
which lets a burst land (coalesce_s) and re-reads just that. A slow safety poll (SAFETY_POLL_S) re-picks the sessions
and re-reads them in case an event went missing; nothing enumerates sessions per read. A reader gets the last record
from memory, so read() costs Windows nothing however often it is called.

What it follows: a pick per caller. CURRENT is Windows' current session (what beatsync has always read); any other
pick is matched, case-blind, inside the session's AppUserModelId (the play tracker follows "spotify", so a browser
video never passes for a song). A record is {"app", "title", "artist", "status"}: the session's AppUserModelId, its
media properties as Windows gives them, and its playback status as an int (PLAYING = 4, 5 = paused).

Fallback: no winrt package (or no SMTC on this Windows) -> read() is None, as the old per-call read returned on any
failure, and the thread ends instead of retrying an import that cannot succeed. A failing manager (NPSMSvc restarted)
is dropped and a new one asked for RETRY_S later; a session that fails to read is None and re-picked soon after.

Standard library only and no package imports, on purpose: the play tracker, outside this repo, keeps a byte-identical
copy next to it (tests/test_keylab_nowplaying.py says when the two drift). Run as a script:
  py arsenal/keylab/nowplaying.py watch [--pick spotify] [--seconds 60]   print each change, then the watcher's counts
  py arsenal/keylab/nowplaying.py measure [--seconds 60] [--pick spotify] NPSMSvc's CPU (GetProcessTimes on the
      svchost hosting NPSMSvc_*) over three phases: nothing polling, the pre-fix read every 2 s, this watcher read
      every 2 s; JSON out
"""
from __future__ import annotations

import asyncio
import atexit
import threading
import time
from typing import Callable, Dict, Optional, Sequence

CURRENT = "current"           # the pick for Windows' current session
PLAYING = 4                   # GlobalSystemMediaTransportControlsSessionPlaybackStatus.Playing (5 = Paused)
SAFETY_POLL_S = 15.0          # re-pick and re-read this often even when no event came
RETRY_S = 5.0                 # a failed manager is replaced this much later
CALL_TIMEOUT_S = 5.0          # an awaited WinRT call that takes longer than this has failed
READY_WAIT_S = 2.0            # a pick's first read() waits at most this long for its first answer
REPICK_SOON_S = 1.0           # a session that failed is re-picked this soon (doubling while it keeps failing)
COALESCE_S = 0.05             # after an event, wait this long for the rest of its burst, then read once


def _manager_class():
    """pywinrt's session manager class; ImportError when the winrt package (or its media.control part) is missing."""
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
    return GlobalSystemMediaTransportControlsSessionManager


def _matches(pick: str, session) -> bool:
    try:
        return pick.casefold() in (session.source_app_user_model_id or "").casefold()
    except Exception:
        return False


def _remove(obj, tokens) -> None:
    for name, token in tokens:
        try:
            getattr(obj, name)(token)
        except Exception:
            pass


class _Follow:
    """One pick: the session it follows, that session's event registrations, and the last record read."""
    __slots__ = ("pick", "session", "tokens", "record", "ready")

    def __init__(self, pick: str):
        self.pick = pick
        self.session = None
        self.tokens: list = []
        self.record: Optional[dict] = None
        self.ready = threading.Event()        # set once the pick has had its first answer (a record or None)


class Watcher:
    """Windows' now-playing kept current by one session manager on one thread. start(), then read(pick)."""

    def __init__(self, safety_poll_s: float = SAFETY_POLL_S, retry_s: float = RETRY_S,
                 coalesce_s: float = COALESCE_S, manager_class=None):
        self.safety_poll_s = max(float(safety_poll_s), 0.05)     # floors: a zero would spin the owner thread
        self.retry_s = max(float(retry_s), 0.01)
        self.coalesce_s = max(float(coalesce_s), 0.0)
        self._manager_class = manager_class
        self._lock = threading.Lock()
        self._follows: Dict[str, _Follow] = {}
        self._pending: set = set()
        self._stop = threading.Event()
        self._ended = False
        self._loop = None
        self._wake = None
        self._thread: Optional[threading.Thread] = None
        self.available = True                 # False once winrt proved missing
        self.error: Optional[str] = None
        self.stats = {"managers": 0, "repicks": 0, "enumerations": 0, "reads": 0, "events": 0, "errors": 0}

    # --- the readers' side (any thread) --------------------------------------------------------------------------------
    def start(self) -> "Watcher":
        with self._lock:
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="smtc-watcher", daemon=True)
                self._thread.start()
        return self

    @property
    def alive(self) -> bool:
        with self._lock:
            return self._thread is not None and not self._ended and not self._stop.is_set()

    def watch(self, pick: str = CURRENT) -> _Follow:
        """Follow `pick` from now on (the first read() does this)."""
        self.start()
        with self._lock:
            f = self._follows.get(pick)
            if f is not None:
                return f
            f = self._follows[pick] = _Follow(pick)
            self._pending.add("sessions")
            if self._ended or self._stop.is_set():
                f.ready.set()                 # nothing will ever answer it
        self._wake_up()
        return f

    def read(self, pick: str = CURRENT, wait_s: float = READY_WAIT_S) -> Optional[dict]:
        """The last record for `pick` (a copy), or None: no such session, no properties yet, no winrt, stopped. A
        memory read; only a pick's first read waits (up to wait_s) for the watcher's first answer."""
        f = self.watch(pick)
        if wait_s and not f.ready.is_set():
            f.ready.wait(wait_s)
        with self._lock:
            if self._ended or self._stop.is_set() or f.record is None:
                return None
            return dict(f.record)

    def status(self) -> dict:
        with self._lock:
            return {"alive": self._thread is not None and not self._ended and not self._stop.is_set(),
                    "available": self.available, "error": self.error, "picks": sorted(self._follows),
                    "stats": dict(self.stats)}

    def stop(self, timeout: float = 5.0) -> None:
        """Unsubscribe everything, let the manager go and end the thread."""
        self._stop.set()
        self._wake_up()
        t = self._thread
        if t is not None and t is not threading.current_thread():
            t.join(timeout)

    # --- WinRT's threads -------------------------------------------------------------------------------------------------
    def _event(self, what) -> None:
        """A WinRT event: mark what went stale and wake the owner thread. Nothing else runs on WinRT's thread."""
        with self._lock:
            self._pending.add(what)
            self.stats["events"] += 1
        self._wake_up()

    def _wake_up(self) -> None:
        loop, wake = self._loop, self._wake
        if loop is not None and wake is not None:
            try:
                loop.call_soon_threadsafe(wake.set)
            except RuntimeError:              # the loop has closed
                pass

    # --- the owner thread ------------------------------------------------------------------------------------------------
    def _count(self, name: str, n: int = 1) -> None:
        with self._lock:
            self.stats[name] += n

    def _run(self) -> None:
        try:
            asyncio.run(self._main())
        except BaseException as exc:          # the thread never ends without saying why
            self.error = repr(exc)
        finally:
            with self._lock:
                self._ended = True
                follows = list(self._follows.values())
                for f in follows:
                    f.record = None
            for f in follows:
                f.ready.set()

    async def _main(self) -> None:
        self._wake = asyncio.Event()
        self._loop = asyncio.get_running_loop()
        try:
            MM = self._manager_class or _manager_class()
        except Exception as exc:
            self.available = False
            self.error = f"no Windows now-playing here: {exc!r}"
            return
        while not self._stop.is_set():
            mgr, tokens = None, []
            try:
                mgr = await asyncio.wait_for(MM.request_async(), CALL_TIMEOUT_S)
                self._count("managers")
                tokens.append(("remove_sessions_changed", mgr.add_sessions_changed(lambda *_: self._event("sessions"))))
                tokens.append(("remove_current_session_changed",
                               mgr.add_current_session_changed(lambda *_: self._event("sessions"))))
                self.error = None
                await self._serve(mgr)
            except Exception as exc:
                self._count("errors")
                self.error = repr(exc)
            finally:
                self._drop(mgr, tokens)
            if not self._stop.is_set():
                await self._wait(self.retry_s)

    async def _serve(self, mgr) -> None:
        """The manager's life: re-pick on a sessions event or the safety poll, re-read what an event marked stale."""
        repick_at = 0.0                       # monotonic; the first pass picks
        soon = REPICK_SOON_S
        while not self._stop.is_set():
            self._wake.clear()
            with self._lock:
                pending, self._pending = self._pending, set()
                follows = list(self._follows.values())
            if "sessions" in pending or time.monotonic() >= repick_at:
                failed = self._repick(mgr, follows)
                repick_at = time.monotonic() + self.safety_poll_s
                stale = props = {f.pick for f in follows}
            else:
                failed = False
                marks = [m for m in pending if isinstance(m, tuple)]
                props = {p for kind, p in marks if kind == "props"}
                stale = props | {p for kind, p in marks if kind == "info"}
            if await self._refresh(follows, stale, props):
                failed = True
            if failed:
                repick_at = min(repick_at, time.monotonic() + soon)
                soon = min(soon * 2, self.safety_poll_s)
            else:
                soon = REPICK_SOON_S
            if await self._wait(max(0.0, repick_at - time.monotonic())) and not self._stop.is_set():
                await asyncio.sleep(self.coalesce_s)

    def _repick(self, mgr, follows) -> bool:
        """Each pick's session, from one get_current_session() and at most one get_sessions(); True if a session's
        events could not be subscribed. A failing manager call raises (the manager is replaced)."""
        self._count("repicks")
        sessions = None
        failed = False
        for f in follows:
            if f.pick == CURRENT:
                s = mgr.get_current_session()
            else:
                if sessions is None:
                    sessions = list(mgr.get_sessions())
                    self._count("enumerations")
                s = next((x for x in sessions if _matches(f.pick, x)), None)
            if not self._bind(f, s):
                failed = True
        return failed

    def _bind(self, f: _Follow, s) -> bool:
        self._unbind(f)
        f.session = s
        if s is None:
            return True
        pick = f.pick
        try:
            f.tokens.append(("remove_media_properties_changed",
                             s.add_media_properties_changed(lambda *_: self._event(("props", pick)))))
            f.tokens.append(("remove_playback_info_changed",
                             s.add_playback_info_changed(lambda *_: self._event(("info", pick)))))
            return True
        except Exception:
            return False

    @staticmethod
    def _unbind(f: _Follow) -> None:
        if f.session is not None:
            _remove(f.session, f.tokens)
        f.session, f.tokens = None, []

    async def _refresh(self, follows, stale, props) -> bool:
        """Re-read the stale picks (media properties only where they changed or were never read; the playback status
        always, it is not awaited) and publish; True if a session failed to read."""
        failed = False
        for f in follows:
            if f.pick not in stale:
                continue
            rec, s = None, f.session
            if s is not None:
                try:
                    with self._lock:
                        old = f.record
                    if f.pick in props or old is None:
                        mp = await asyncio.wait_for(s.try_get_media_properties_async(), CALL_TIMEOUT_S)
                        self._count("reads")
                        base = None if mp is None else (mp.title, mp.artist)
                    else:
                        base = (old["title"], old["artist"])
                    if base is not None:
                        info = s.get_playback_info()
                        rec = {"app": s.source_app_user_model_id, "title": base[0], "artist": base[1],
                               "status": int(info.playback_status)}
                except Exception:
                    rec, failed = None, True
            with self._lock:
                f.record = rec
            f.ready.set()
        return failed

    def _drop(self, mgr, tokens) -> None:
        with self._lock:
            follows = list(self._follows.values())
        for f in follows:
            self._unbind(f)
        if mgr is not None:
            _remove(mgr, tokens)
        with self._lock:
            for f in follows:
                f.record = None
        for f in follows:
            f.ready.set()

    async def _wait(self, timeout: float) -> bool:
        """Sleep until woken or `timeout` s; True if woken."""
        if self._stop.is_set():
            return False
        try:
            await asyncio.wait_for(self._wake.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            return False


# --- the process's one watcher -------------------------------------------------------------------------------------------
_PROCESS_LOCK = threading.Lock()
_PROCESS: Optional[Watcher] = None


def watcher() -> Watcher:
    """The process-wide watcher, started on first use (one session manager per process, whoever reads)."""
    global _PROCESS
    with _PROCESS_LOCK:
        if _PROCESS is None:
            _PROCESS = Watcher().start()
        return _PROCESS


def read(pick: str = CURRENT, wait_s: float = READY_WAIT_S) -> Optional[dict]:
    """The process watcher's last record for `pick`, or None (never raises)."""
    try:
        return watcher().read(pick, wait_s)
    except Exception:
        return None


def shutdown(timeout: float = 2.0) -> None:
    """Stop the process watcher (it unsubscribes from Windows' events first); the next read() starts a new one."""
    global _PROCESS
    with _PROCESS_LOCK:
        w, _PROCESS = _PROCESS, None
    if w is not None:
        w.stop(timeout)


atexit.register(shutdown)                     # unsubscribe before the interpreter goes, not during


# --- the live check: NPSMSvc's CPU ---------------------------------------------------------------------------------------
def old_read(pick: str = CURRENT) -> Optional[dict]:
    """The pre-2026-10-29 read, kept only for `measure` to compare against: a NEW manager, an enumeration (or the
    current session) and both reads, every call."""
    try:
        MM = _manager_class()

        async def get():
            mgr = await MM.request_async()
            if pick == CURRENT:
                s = mgr.get_current_session()
            else:
                s = next((x for x in mgr.get_sessions() if _matches(pick, x)), None)
            if not s:
                return None
            props = await s.try_get_media_properties_async()
            info = s.get_playback_info()
            return {"app": s.source_app_user_model_id, "title": props.title, "artist": props.artist,
                    "status": int(info.playback_status)}
        return asyncio.run(get())
    except Exception:
        return None


def npsmsvc_pid(tasklist_csv: Optional[str] = None) -> Optional[int]:
    """The PID of the svchost hosting NPSMSvc_* (Now Playing Session Manager, a per-user service), from
    `tasklist /svc /fo csv /nh`."""
    import csv
    if tasklist_csv is None:
        import subprocess
        tasklist_csv = subprocess.run(["tasklist", "/svc", "/fo", "csv", "/nh"], capture_output=True, text=True,
                                      timeout=60).stdout
    for row in csv.reader(tasklist_csv.splitlines()):
        if len(row) >= 3 and any(s.strip().casefold().startswith("npsmsvc") for s in row[2].split(",")):
            try:
                return int(row[1])
            except ValueError:
                continue
    return None


def process_cpu_s(pid: int) -> float:
    """Kernel + user CPU seconds a process has used so far (GetProcessTimes)."""
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    h = k32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        times = [wintypes.FILETIME() for _ in range(4)]   # creation, exit, kernel, user
        if not k32.GetProcessTimes(h, *(ctypes.byref(t) for t in times)):
            raise ctypes.WinError(ctypes.get_last_error())
        return sum((t.dwHighDateTime << 32 | t.dwLowDateTime) for t in times[2:]) / 1e7
    finally:
        k32.CloseHandle(h)


def measure(seconds: float = 60.0, pick: str = "spotify", poll_s: float = 2.0,
            phases: Sequence[str] = ("baseline", "old", "new"), pid: Optional[int] = None,
            cpu: Callable[[int], float] = process_cpu_s, clock: Callable[[], float] = time.monotonic,
            sleep: Callable[[float], None] = time.sleep) -> dict:
    """NPSMSvc's CPU, as % of one core, over `seconds` per phase: baseline (nothing read here), old (old_read every
    poll_s, what the tracker did), new (a Watcher read every poll_s). Each phase says how many reads it made and how
    many session managers Windows handed out for them."""
    unknown = [p for p in phases if p not in ("baseline", "old", "new")]
    if unknown:
        raise ValueError(f"unknown phase(s) {unknown}: want baseline, old, new")
    pid = pid or npsmsvc_pid()
    if pid is None:
        return {"error": "no svchost hosting NPSMSvc_* was found"}
    out = {"npsmsvc_pid": pid, "seconds": seconds, "poll_s": poll_s, "pick": pick, "phases": {}}
    for phase in phases:
        w = Watcher().start() if phase == "new" else None
        managers = [0]
        if phase == "new":
            reader = lambda: w.read(pick)
        elif phase == "old":
            def reader():
                managers[0] += 1
                return old_read(pick)
        else:
            reader = None
        reads, last = 0, None
        c0, t0 = cpu(pid), clock()
        while clock() - t0 < seconds:
            if reader is not None:
                last = reader()
                reads += 1
            sleep(poll_s)
        c1, t1 = cpu(pid), clock()
        rec = {"npsmsvc_pct_of_one_core": round((c1 - c0) / max(t1 - t0, 1e-9) * 100.0, 2), "reads": reads,
               "managers": managers[0], "last": last}
        if w is not None:
            st = w.status()
            rec.update(managers=st["stats"]["managers"], watcher=st)
            w.stop()
        out["phases"][phase] = rec
    return out


def _cli(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(prog="nowplaying", description="Windows' now-playing from one SMTC session manager")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("watch", help="print each change of a pick's record")
    w.add_argument("--pick", default=CURRENT)
    w.add_argument("--seconds", type=float, default=60.0)
    m = sub.add_parser("measure", help="NPSMSvc's CPU: nothing / the pre-fix read / this watcher, JSON out")
    m.add_argument("--seconds", type=float, default=60.0)
    m.add_argument("--pick", default="spotify")
    m.add_argument("--poll", type=float, default=2.0)
    m.add_argument("--phases", default="baseline,old,new")
    a = ap.parse_args(argv)
    if a.cmd == "watch":
        wt = Watcher().start()
        last, end = object(), time.monotonic() + a.seconds
        while time.monotonic() < end:
            rec = wt.read(a.pick)
            if rec != last:
                print(json.dumps(rec), flush=True)
                last = rec
            time.sleep(0.5)
        print(json.dumps(wt.status()))
        wt.stop()
        return 0
    print(json.dumps(measure(a.seconds, a.pick, a.poll, [p.strip() for p in a.phases.split(",") if p.strip()]),
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
