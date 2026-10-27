"""arsenal.keylab.governor -- the burst ceiling as a guarantee, not a habit.

A tight burst of SysEx froze this unit once (2026-10-22: black screen, buttons dead, power cycle). 12 packets per
100 ms has been safe on it (README "Confirmed facts"). The "~36 freezes" figure is inherited from saxofonbrian's
notes, not measured here, and Arturia's own FL script sends about 48 back to back when FL starts, so what sets a
freeze off is not only the count (research/reviewed/keylab-liberation-2026-10-22/
keylab-dev-guidance-and-hang-guide-2026-10-27.md, section 3.2).

Pacing that lives in each producer is not a ceiling: two producers that each stay polite can still add up. So the
governor sits on the PORT: at most `limit` packets in any sliding `window` seconds, and a caller that would break the
ceiling waits; nothing is dropped. A sender meets it twice (winmidi.MidiOut.send_sysex does both):

  admit()      before anything touches the driver. Reserves the port's next free SLOT, first come, first served,
               and sleeps until it. This spreads the senders out, and a flood cannot starve anyone.
  gate(call)   around the driver call itself (midiOutLongMsg). A slot alone does not hold the ceiling where the
               device is: a sender whose Python is busy (pure-Python threads such as the VJ engine's analysis) reached
               the driver 146-277 ms after its slot, and the driver saw 13 calls in 100 ms while the slots held 12
               [S:local, 2026-10-27, fake driver, 6 of 6 runs]. So the gate counts the calls: a call is registered as
               in flight just before it starts and gets its end time just after it returns, and a new call may start
               only while fewer than `limit` calls are in flight or ended less than `window` ago. However late each
               call runs, no `window` then holds more than `limit` of them: of any set that close together, the one
               registered last saw every other one in flight or recently ended. On Windows MIDI Services the call
               returns only after the device write [S: the hang guide, Windows MIDI Services lane, section 2], so the
               writes themselves keep the ceiling [I].

  BurstGovernor  counts within one process (thread-safe). The building block, and what ScreenWriter falls back to
                 for a sink that has no governor of its own.
  PortGovernor   counts across every process on this machine that sends to the same port: the screen service, the
                 VJ engine, every CLI call and every probe share one budget. winmidi.MidiOut builds one by default,
                 keyed by the port it opened. The shared state is a small file per port under
                 state/arsenal/keylab/governor/ of the MAIN checkout (a git worktree resolves to it, so a tool run
                 from a worktree still counts against the services run from the main tree), mapped into memory and
                 guarded by an OS byte-range lock that the OS releases if its holder dies. Times come from
                 time.perf_counter, which on Windows is QueryPerformanceCounter: one clock for every process.

What it does not cover: FL Studio's own scripts (ours and Arturia's) send from inside FL, outside this bucket.

The default window is 0.1 s. PadRenderer has been sending up to ~150 packets/s without a freeze, so 12 per 100 ms
(120/s) sits inside behaviour already seen on the hardware. It is a conservative starting value, and probe P24 (the
sustained burst window, added by the A16 design docs) re-measures it.

The clock and sleep are injectable, so the property tests run on a fake clock and cannot flake.
"""
from __future__ import annotations

import itertools
import json
import mmap
import os
import re
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable, Deque, Dict, Iterable, List, NamedTuple, Optional, Tuple, TypeVar

T = TypeVar("T")

SAFE_BURST = 12      # packets: the ceiling that has been safe on this unit
WINDOW_S = 0.1       # seconds: the sliding window the ceiling applies to
FLIGHT_STALE_S = 5.0  # a call in flight longer than this died with its process or is stuck in the driver: it stops
                      # counting (Windows MIDI Services gives up on a send after 1 s, 4 s with its staged fix)
GATE_POLL_S = 0.001  # how often a gate held back only by calls still in flight looks again

GOVERNOR_DIR_ENV = "AKASHIC_KEYLAB_GOVERNOR_DIR"   # overrides where the per-port buckets live (tests, other trees)
_STATE_BYTES = 16384         # the bucket file's fixed size: JSON padded with spaces, mapped and rewritten in place
_LOCK_OFFSET = 1 << 20       # the locked byte sits past the data, so a reader never trips over the lock
_KEEP_S = 1.0                # slot times kept in the bucket (each process counts only its own window of them)
_KEEP_MAX = 64
_LIMIT_MAX = 128             # the most slot times one bucket file holds with room to spare
_LOCK_TIMEOUT_S = 2.0        # the lock is held for microseconds; past this, its holder is frozen
_HORIZON_S = 10.0            # a time further ahead than this is from another boot, not a reservation

_TOKENS = itertools.count(1)  # ids of calls in flight, unique within the process (the pid makes them unique across)


def _gate_check(flight: Iterable[Tuple[int, float]], ends: Iterable[float], now: float, limit: int, window: float,
                horizon: float) -> Tuple[List[Tuple[int, float]], List[float], float]:
    """The gate's rule, shared by both governors. `flight` holds (id, start) of calls in flight, `ends` the end
    times of finished calls. Returns the calls in flight that still count, the ends still inside the window (sorted),
    and how long to wait: 0 means a call may start now."""
    flight = [(tok, s) for tok, s in flight if now - FLIGHT_STALE_S < s <= now + horizon]
    ends = sorted(e for e in ends if now - e < window and e <= now + horizon)
    busy = len(flight) + len(ends)
    if busy < limit:
        return flight, ends, 0.0
    need = busy - limit + 1          # this many must leave first, and only finished calls leave the window
    wait = ends[need - 1] + window - now if need <= len(ends) else GATE_POLL_S
    return flight, ends, max(wait, 1e-6)


class BurstGovernor:
    def __init__(self, limit: int = SAFE_BURST, window: float = WINDOW_S,
                 clock: Callable[[], float] = time.perf_counter, sleep: Callable[[float], None] = time.sleep):
        if limit < 1 or window <= 0:
            raise ValueError("limit must be >= 1 and window > 0")
        self.limit, self.window = limit, window
        self._clock, self._sleep = clock, sleep
        self._lock = threading.Lock()
        self._recent: Deque[float] = deque()   # admit times still inside the window
        self.admitted = 0                      # lifetime packets let through
        self.waited_s = 0.0                    # lifetime time spent holding callers back at admit()
        self.log: List[float] = []             # every admit time, kept only when record=True
        self.record = False
        self._gate_lock = threading.Lock()
        self._flight: Dict[int, float] = {}    # calls in flight: id -> start
        self._ends: List[float] = []           # end times of finished calls still inside the window
        self.gated = 0                         # lifetime driver calls made through gate()
        self.gate_waited_s = 0.0               # lifetime time calls waited at the gate (late senders bunching up)

    def admit(self) -> float:
        """Block until one more packet fits under the ceiling, then count it. Returns the admit time."""
        with self._lock:
            while True:
                now = self._clock()
                while self._recent and now - self._recent[0] >= self.window:
                    self._recent.popleft()
                if len(self._recent) < self.limit:
                    self._recent.append(now)
                    return self._count(now)
                wait = self.window - (now - self._recent[0])
                self.waited_s += wait
                self._sleep(wait)

    def _count(self, now: float) -> float:
        self.admitted += 1
        if self.record:
            self.log.append(now)
        return now

    def gate(self, call: Callable[[], T]) -> T:
        """Make the driver call `call()` only while it keeps the ceiling at the driver (fewer than `limit` calls in
        flight or ended within `window`), waiting until it does. Returns what call() returns."""
        token, waited = self._gate_enter()
        try:
            return call()
        finally:
            self._gate_exit(token, waited)

    def _gate_enter(self) -> Tuple[Optional[int], float]:
        """Wait for room, then register a call as in flight. Returns (its id, seconds waited)."""
        waited = 0.0
        while True:
            with self._gate_lock:
                now = self._clock()
                flight, self._ends, wait = _gate_check(self._flight.items(), self._ends, now, self.limit,
                                                       self.window, _HORIZON_S)
                self._flight = dict(flight)
                if wait <= 0:
                    token = next(_TOKENS)
                    self._flight[token] = now
                    return token, waited
            self._sleep(wait)
            waited += wait

    def _gate_exit(self, token: Optional[int], waited: float) -> None:
        with self._gate_lock:
            self._flight.pop(token, None)
            self._ends.append(self._clock())
            self.gated += 1
            self.gate_waited_s += waited

    def close(self) -> None:
        """Nothing to release in process; PortGovernor closes its bucket file."""


# --- the port-wide bucket ------------------------------------------------------------------------------------------

def port_key(port: str) -> str:
    """One bucket per physical port. Windows can rename a re-plugged port '2- KeyLab 88 mk3 DAW' (Bitwig's KeyLab
    extension strips the same prefix), so the 'N- ' prefix is dropped and the rest made file-safe."""
    name = re.sub(r"^\s*\d+\s*-\s*", "", port or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", name).strip("-") or "port"


def _main_checkout(repo: Path) -> Path:
    """The main checkout behind a git worktree (whose .git is a file naming <main>/.git/worktrees/<name>), else repo."""
    git = repo / ".git"
    try:
        if git.is_file():
            text = git.read_text(encoding="utf-8", errors="replace").strip()
            if text.startswith("gitdir:"):
                gitdir = Path(text[len("gitdir:"):].strip())
                if not gitdir.is_absolute():
                    gitdir = (repo / gitdir).resolve()
                if gitdir.parent.name == "worktrees" and gitdir.parent.parent.name == ".git":
                    return gitdir.parent.parent.parent
    except OSError:
        pass
    return repo


def default_state_dir() -> Path:
    env = os.environ.get(GOVERNOR_DIR_ENV)
    if env:
        return Path(env)
    repo = Path(__file__).resolve().parents[2]
    return _main_checkout(repo) / "state" / "arsenal" / "keylab" / "governor"


if sys.platform == "win32":
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class _OVERLAPPED(ctypes.Structure):
        _fields_ = [("Internal", ctypes.c_void_p), ("InternalHigh", ctypes.c_void_p), ("Offset", wintypes.DWORD),
                    ("OffsetHigh", wintypes.DWORD), ("hEvent", wintypes.HANDLE)]

    _LOCKFILE_FAIL_IMMEDIATELY, _LOCKFILE_EXCLUSIVE_LOCK = 0x1, 0x2
    # Taking and leaving the lock must not give up the GIL: a thread that waits for the GIL while it holds the lock
    # (behind the process's busy threads) holds every other process's sends with it. The calls never block
    # (FAIL_IMMEDIATELY), so they can keep the GIL: PYFUNCTYPE, safe on x64, which has one calling convention.
    # 32-bit Python (stdcall) keeps WINFUNCTYPE, which gives the GIL up around the call.
    _PROTO = ctypes.PYFUNCTYPE if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.WINFUNCTYPE
    _k32 = ctypes.WinDLL("kernel32")
    _LockFileEx = _PROTO(wintypes.BOOL, wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                         wintypes.DWORD, ctypes.POINTER(_OVERLAPPED))(("LockFileEx", _k32))
    _UnlockFileEx = _PROTO(wintypes.BOOL, wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                           ctypes.POINTER(_OVERLAPPED))(("UnlockFileEx", _k32))

    def _span() -> "_OVERLAPPED":
        ov = _OVERLAPPED()
        ov.Offset, ov.OffsetHigh = _LOCK_OFFSET & 0xFFFFFFFF, _LOCK_OFFSET >> 32
        return ov

    def _lock_fd(fd: int) -> None:
        """Take the bucket's lock without waiting (OSError if another handle holds it). Windows releases it when the
        holding process exits."""
        if not _LockFileEx(msvcrt.get_osfhandle(fd), _LOCKFILE_EXCLUSIVE_LOCK | _LOCKFILE_FAIL_IMMEDIATELY, 0, 1, 0,
                           ctypes.byref(_span())):
            raise OSError("the port bucket is locked by another handle")

    def _unlock_fd(fd: int) -> None:
        _UnlockFileEx(msvcrt.get_osfhandle(fd), 0, 1, 0, ctypes.byref(_span()))
else:
    import fcntl

    def _lock_fd(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock_fd(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


class _State(NamedTuple):
    times: List[float]                  # reserved slots, in order
    total: int                          # lifetime admits on the port
    flight: List[Tuple[int, float]]     # calls in flight: (id, start)
    ends: List[float]                   # end times of finished calls


class PortGovernor(BurstGovernor):
    """The same ceiling and the same API as BurstGovernor, counted across every process that sends to `port`.

    The bucket holds the slot times of the last second, in order, including SLOTS reserved for callers still
    waiting, and the gate's calls in flight and recently ended. admit() takes the bucket's OS lock, drops times that
    have left the window (and any from another boot, far in the future), and reserves the earliest slot that keeps
    every window at or under the limit and comes after every slot already reserved; then it leaves the lock and
    sleeps until its slot. Reserving in lock order makes the bucket first come, first served: a producer flooding
    the port cannot starve the screen service, which gets the next free slot after the flood's current one. A
    waiting slot is placed `guard` seconds later than the bare minimum, so a sleep that overshoots by up to that much
    rarely has to wait again at the gate. gate() takes the lock twice, to register the call before it and to record
    its end after it, and never across the driver call (on Windows MIDI Services a send can wait 1 s; an older driver
    path has no time limit at all).

    Inside the lock no thread gives up the GIL: the state is a memory-mapped file and the lock calls keep the GIL,
    so a process with busy Python threads holds the lock for microseconds. Before that, a read() or write() inside
    the lock handed the GIL to the busy threads and held the port for a median 63 ms per admit (2 spinning threads,
    [S:local, 2026-10-27]).

    The bucket is a file, not anonymous shared memory, so a process that sent 12 packets and exited a moment ago
    still counts against the next one. Fail-safe both ways: unreadable state counts as a full window (one window's
    wait, then it is rewritten), a lock held past `lock_timeout` (a frozen holder) costs one window's wait and is
    counted in `fallbacks`, a call left in flight by a process that died stops counting after FLIGHT_STALE_S, and a
    bucket that cannot be opened at all leaves this governor counting in process (`shared` False, one line on
    stderr)."""

    GUARD_S = 0.002          # the margin a waiting slot keeps for a late wake-up
    HORIZON_S = _HORIZON_S

    def __init__(self, port: str, limit: int = SAFE_BURST, window: float = WINDOW_S,
                 state_dir: Optional[os.PathLike] = None, clock: Callable[[], float] = time.perf_counter,
                 sleep: Callable[[float], None] = time.sleep, lock_timeout: float = _LOCK_TIMEOUT_S,
                 guard: float = GUARD_S):
        if limit > _LIMIT_MAX:
            raise ValueError(f"a port bucket holds at most {_LIMIT_MAX} admit times; limit={limit}")
        super().__init__(limit, window, clock, sleep)
        self.port = port
        self.key = port_key(port)
        folder = Path(state_dir) if state_dir is not None else default_state_dir()
        self.path = str(folder / f"{self.key}.json")
        self.lock_timeout = lock_timeout
        self.guard = max(0.0, float(guard))
        self.shared = False
        self.fallbacks = 0          # admits and calls made without the lock (holder frozen past lock_timeout)
        self.healed = 0             # times the bucket was unreadable and rewritten
        self._fd: Optional[int] = None
        self._mm: Optional[mmap.mmap] = None
        try:
            folder.mkdir(parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o644)
            try:
                if sys.platform != "win32" and os.fstat(fd).st_size < _STATE_BYTES:
                    os.ftruncate(fd, _STATE_BYTES)          # Windows extends a shorter file when it maps it
                self._mm = mmap.mmap(fd, _STATE_BYTES, access=mmap.ACCESS_WRITE)
            except BaseException:
                os.close(fd)
                raise
            self._fd = fd
            self.shared = True
        except (OSError, ValueError) as exc:
            print(f"keylab governor: cannot open the port bucket {self.path} ({exc}); counting in this process only",
                  file=sys.stderr)

    def admit(self) -> float:
        """Block until this packet's slot under the port's ceiling, then count it. Returns the slot's time."""
        if not self.shared:
            return super().admit()
        with self._lock:                                     # this instance's file handle, one thread at a time
            got = self._acquire()
            if got:
                try:
                    now = self._clock()
                    st = self._read(now)
                    live = sorted(t for t in st.times if now - self.window < t <= now + self.HORIZON_S)
                    slot = max(now, live[-1]) if live else now          # never ahead of a reserved slot
                    if len(live) >= self.limit:                         # the limit-th newest must have left
                        slot = max(slot, live[-self.limit] + self.window + self.guard)
                    live.append(slot)
                    self._write(st._replace(times=live, total=st.total + 1), now)
                finally:
                    _unlock_fd(self._fd)
        if not got:                                          # a frozen holder: be slow rather than stuck
            self._sleep(self.window)
            with self._lock:
                self.fallbacks += 1
                self.waited_s += self.window
                return self._count(self._clock())
        wait = slot - now
        if wait > 0:
            self._sleep(wait)
        with self._lock:
            self.waited_s += max(0.0, wait)
            return self._count(slot)

    def _gate_enter(self) -> Tuple[Optional[int], float]:
        if not self.shared:
            return super()._gate_enter()
        waited = 0.0
        while True:
            with self._lock:
                got = self._acquire()
                if got:
                    try:
                        now = self._clock()
                        st = self._read(now)
                        flight, ends, wait = _gate_check(st.flight, st.ends, now, self.limit, self.window,
                                                         self.HORIZON_S)
                        if wait <= 0:
                            token = (os.getpid() << 32) | (next(_TOKENS) & 0xFFFFFFFF)
                            flight.append((token, now))
                            self._write(st._replace(flight=flight, ends=ends), now)
                            return token, waited
                    finally:
                        _unlock_fd(self._fd)
            if not got:                                      # a frozen holder: be slow rather than stuck
                self._sleep(self.window)
                with self._lock:
                    self.fallbacks += 1
                return None, waited + self.window
            self._sleep(wait)
            waited += wait

    def _gate_exit(self, token: Optional[int], waited: float) -> None:
        if not self.shared:
            return super()._gate_exit(token, waited)
        with self._lock:
            self.gated += 1
            self.gate_waited_s += waited
            if token is None or not self._acquire():         # unregistered, or a frozen holder: it goes stale
                return
            try:
                now = self._clock()
                st = self._read(now)
                self._write(st._replace(flight=[f for f in st.flight if f[0] != token], ends=st.ends + [now]), now)
            finally:
                _unlock_fd(self._fd)

    def _acquire(self) -> bool:
        if self._fd is None or self._mm is None:
            return False
        deadline = time.perf_counter() + self.lock_timeout
        while True:
            try:
                _lock_fd(self._fd)
                return True
            except OSError:
                if time.perf_counter() >= deadline:
                    return False
                time.sleep(0.0002)

    def _read(self, now: float) -> _State:
        raw = self._mm[:_STATE_BYTES].rstrip(b" \x00")
        if not raw:
            return _State([], 0, [], [])                     # a new bucket
        try:
            state = json.loads(raw)
            return _State([float(t) for t in state["times"]], int(state.get("admits", 0)),
                          [(int(tok), float(s)) for tok, s in state.get("flight", [])],
                          [float(e) for e in state.get("ends", [])])
        except (ValueError, KeyError, TypeError, AttributeError):
            # A writer killed mid-write, or someone else's bytes: assume the window is full as of now. Callers wait
            # one window, then the bucket is whole again.
            self.healed += 1
            st = _State([now] * self.limit, 0, [], [now] * self.limit)
            self._write(st, now)
            return st

    def _write(self, st: _State, now: float) -> None:
        cap = max(_KEEP_MAX, self.limit)
        keep = max(self.window, _KEEP_S)
        times = sorted(t for t in st.times if now - keep < t <= now + self.HORIZON_S)[-cap:]
        flight = sorted(((tok, s) for tok, s in st.flight if now - FLIGHT_STALE_S < s <= now + self.HORIZON_S),
                        key=lambda f: f[1])[-cap:]
        ends = sorted(e for e in st.ends if now - e < self.window and e <= now + self.HORIZON_S)[-cap:]
        state = {"port": self.port, "times": times, "admits": st.total, "flight": [list(f) for f in flight],
                 "ends": ends, "pid": os.getpid(), "limit": self.limit, "window": self.window,
                 "clock": "time.perf_counter (QueryPerformanceCounter)"}
        data = json.dumps(state).encode("utf-8")
        while len(data) > _STATE_BYTES and len(times) > self.limit:   # only times no window can still need
            times = times[-max(self.limit, len(times) * 3 // 4):]
            state["times"] = times
            data = json.dumps(state).encode("utf-8")
        if len(data) > _STATE_BYTES:      # not reachable at _LIMIT_MAX; keep the newest `limit` of each, never fail
            state["flight"], state["ends"] = state["flight"][-self.limit:], ends[-self.limit:]
            data = json.dumps(state).encode("utf-8")[:_STATE_BYTES]
        self._mm[:_STATE_BYTES] = data.ljust(_STATE_BYTES)

    def close(self) -> None:
        with self._lock:
            mm, self._mm = self._mm, None
            fd, self._fd = self._fd, None
            self.shared = False
        if mm is not None:
            try:
                mm.close()
            except (BufferError, OSError, ValueError):
                pass
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def max_in_window(times, window: float) -> int:
    """The most admits that fall inside any half-open window of length `window` (the property the pin checks)."""
    ts = sorted(times)
    best, lo = 0, 0
    for hi, t in enumerate(ts):
        while t - ts[lo] >= window:
            lo += 1
        best = max(best, hi - lo + 1)
    return best
