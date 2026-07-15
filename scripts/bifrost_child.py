"""bifrost_child -- managed subprocess + daemon singleton lock (T075 M1-delta).

Lightweight child-process supervision for the daemon: one ManagedChild per runtime
tier (runner in delta, wake-listener in gamma). Pure composition of subprocess +
bus._client -- no new primitives, no runner_lock changes.

DaemonLock: a simple singleton guard over bifrost:daemon:<agent> -- nx SET on
acquire, TTL heartbeat, nx-reclaim on outage (F5, runner_lock precedent), token-
match release. NO fencing generation, NO cursor interaction (runner_lock owns
those contracts for the consume path; ruling 1: consume path unmoved). This lock
ONLY prevents twin daemons.

ManagedChild: non-blocking backoff (F2: _next_spawn_at timestamp, no sleeps
outside the main tick), pipe drainer thread with bounded ring buffer (F1: the
T019 shape -- prevents the chatty-child wedge), circuit breaker (3 crashes/300s
= trip), benign-exit-is-handover (N1: exit 0 = deliberate, daemon does not
contest -- docstring says it).
"""
from __future__ import annotations

import collections
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from typing import Any, Callable, Deque, Dict, List, Optional


# ---------------------------------------------------------------- DaemonLock
class DaemonLock:
    """Minimal singleton guard for the daemon process. Key: <ns>:daemon:<agent>.
    Separate from runner_lock (which guards the consume path).

    F5 outage survival (runner_lock precedent): heartbeat on a vanished key
    tries an nx-reclaim of own token before standing down. A Redis restart
    > TTL must not kill an uncontested daemon -- the lock was never stolen,
    it was just scrubbed. Stand down ONLY when nx LOSES (a foreign holder)."""

    def __init__(self, client, ns: str, agent: str, ttl: int = 120):
        self._c = client
        self._key = f"{ns}:daemon:{agent}"
        self._ttl = ttl
        self._token = f"daemon:{agent}:{uuid.uuid4().hex[:12]}"
        self._pid = os.getpid()

    @property
    def token(self) -> str:
        return self._token

    def acquire(self) -> bool:
        """Try to become the daemon for this agent. False = another daemon lives."""
        if self._c is None:
            return True
        try:
            rec = {"token": self._token, "pid": self._pid,
                   "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
            return bool(self._c.set(self._key, json.dumps(rec), nx=True, ex=self._ttl))
        except Exception:
            return True

    def heartbeat(self) -> bool:
        """Refresh the TTL. Returns False only when a LIVE foreign holder exists
        (F5: a vanished key gets one nx-reclaim attempt -- stand down only on
        genuine contested loss)."""
        if self._c is None:
            return True
        try:
            raw = self._c.get(self._key)
            if raw:
                rec = json.loads(raw)
                if rec.get("token") != self._token:
                    return False
                rec["refreshed"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                self._c.set(self._key, json.dumps(rec), ex=self._ttl)
                return True
            # F5: key vanished (outage > TTL, Redis restart). nx-reclaim.
            rec = {"token": self._token, "pid": self._pid,
                   "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "refreshed": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "reclaimed": True}
            return bool(self._c.set(self._key, json.dumps(rec), nx=True, ex=self._ttl))
        except Exception:
            return True

    def release(self) -> bool:
        """Free the daemon lock on clean exit (own token only)."""
        if self._c is None:
            return True
        try:
            raw = self._c.get(self._key)
            if raw and json.loads(raw).get("token") == self._token:
                self._c.delete(self._key)
            return True
        except Exception:
            return True


# ---------------------------------------------------------------- ManagedChild
# F1: bounded ring-buffer drainer -- the T019 shape (per-pipe drainer threads
# with bounded live tails). The ring is what on_exit reads; the drainer reads
# the pipe into the ring. A full ring = oldest dropped (loudly), pipe never
# blocks, the child never wedges on a full OS buffer.
_RING_LINES = 200


class ManagedChild:
    """One supervised subprocess with non-blocking backoff and circuit breaker.

    The daemon owns one per runtime tier. Lifecycle:
      spawn -> monitor (poll, drainer thread pulling stdout into a ring buffer)
           -> on exit: restart | pause (breaker trip) | deliberate stop (exit 0)

    F2: backoff is non-blocking -- _next_spawn_at timestamp, no sleeps outside
    the daemon's main tick. The heartbeat and signal handling survive any
    backoff duration.

    F1: drainer thread reads the child's stdout pipe into a bounded ring buffer
    (_RING_LINES lines). The pipe never fills; the child never blocks on print.
    on_exit receives ring contents, not a partial post-mortem pipe read.

    N1: exit code 0 = DELIBERATE HANDOVER -- the daemon does not respawn. A
    runner that stood down (successor took the lock) or exited via SIGINT stays
    down. Daemon becomes presence-only until restart.
    """

    def __init__(self, args: List[str], env: Optional[Dict[str, str]] = None,
                 cwd: Optional[str] = None,
                 on_blocker: Optional[Callable[[], None]] = None,
                 breaker_window_s: float = 300.0,
                 breaker_max: int = 3):
        self._args = list(args)
        self._env = dict(env or {})
        self._cwd = cwd
        self._on_blocker = on_blocker
        self._breaker_window_s = breaker_window_s
        self._breaker_max = breaker_max
        self._proc: Optional[subprocess.Popen] = None
        self._crashes: Deque[float] = collections.deque()
        self._tripped = False
        self._backoff_idx = 0
        self._backoffs = (1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
        # F2: non-blocking backoff -- spawn only when now >= this timestamp
        self._next_spawn_at: float = 0.0
        # F1: drainer thread + bounded ring buffer (stdout pipe -> ring)
        self._ring: Deque[str] = collections.deque(maxlen=_RING_LINES)
        self._drainer: Optional[threading.Thread] = None
        self._drainer_done = threading.Event()
        # exit hooks
        self.on_exit: Optional[Callable[[int, Optional[str]], None]] = None
        self.last_summary: Optional[Dict[str, Any]] = None

    # -- public ------------------------------------------------------------

    @property
    def alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @property
    def tripped(self) -> bool:
        return self._tripped

    @property
    def pid(self) -> Optional[int]:
        return self._proc.pid if self._proc else None

    def spawn(self) -> Optional[subprocess.Popen]:
        """Launch the child. Returns the Popen handle, or None if the circuit breaker
        is tripped, the previous child is still alive, or backoff hasn't elapsed yet."""
        if self._tripped:
            return None
        if self.alive:
            return self._proc
        if time.time() < self._next_spawn_at:
            return None  # F2: backoff not yet elapsed; caller retries on next tick
        self._proc = subprocess.Popen(
            self._args, env=self._env, cwd=self._cwd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1)
        # F1: start drainer thread to prevent pipe wedge
        self._ring.clear()
        self._drainer_done.clear()
        def _drain():
            try:
                for line in self._proc.stdout:
                    self._ring.append(line.rstrip("\n\r"))
            except Exception:
                pass
            finally:
                self._drainer_done.set()
        self._drainer = threading.Thread(target=_drain, daemon=True)
        self._drainer.start()
        return self._proc

    def poll(self) -> Optional[int]:
        """Check the child. Returns its exit code if it exited since last poll,
        None if still running (or never spawned). On exit, calls on_exit(code, tail)
        and runs the non-blocking restart/backoff/breaker logic (F2).

        If backoff hasn't elapsed and the child isn't alive, attempts a re-spawn
        (spawn() gates on _next_spawn_at internally)."""
        if self._proc is None:
            # backoff may have elapsed while no child was running -> try spawn
            if not self._tripped and time.time() >= self._next_spawn_at:
                self.spawn()
            return None
        code = self._proc.poll()
        if code is None:
            return None
        # child exited -- wait for drainer to finish, then collect ring
        if self._drainer is not None:
            self._drainer_done.wait(timeout=5)
        tail = "\n".join(list(self._ring)) if self._ring else ""
        if self.on_exit:
            try:
                self.on_exit(code, tail)
            except Exception:
                pass
        self._handle_exit(code or 0)
        return code

    def terminate(self) -> None:
        """Stop the child on daemon exit."""
        if self._proc is None:
            return
        try:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=3)
        except Exception:
            pass
        self._proc = None

    # -- internal -----------------------------------------------------------

    def _handle_exit(self, code: int) -> None:
        self._proc = None
        if code == 0:
            # N1: benign exit = DELIBERATE HANDOVER. The daemon does not
            # contest -- a runner that stood down or exited cleanly stays down.
            self._backoff_idx = 0
            self._crashes.clear()
            self._next_spawn_at = float("inf")   # never auto-respawn
            return
        # crash
        now = time.time()
        self._crashes.append(now)
        while self._crashes and (now - self._crashes[0]) > self._breaker_window_s:
            self._crashes.popleft()
        if len(self._crashes) >= self._breaker_max:
            self._tripped = True
            if self._on_blocker:
                try:
                    self._on_blocker()
                except Exception:
                    pass
            return
        # F2: non-blocking backoff -- schedule, don't sleep
        delay = self._backoffs[min(self._backoff_idx, len(self._backoffs) - 1)]
        self._backoff_idx += 1
        self._next_spawn_at = time.time() + delay
        # spawn() will fire on the next poll() tick when now >= _next_spawn_at


# ---------------------------------------------------------------- summary helpers
def read_summary(path: str) -> Optional[Dict[str, Any]]:
    """Read a runner's exit summary JSON. None when absent or unreadable."""
    try:
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.loads(f.read().strip() or "{}") or None
    except Exception:
        return None


def format_summary_for_prompt(s: Dict[str, Any]) -> str:
    """One-liner suitable for the runner's system prompt / the daemon's card summary."""
    verdict = str(s.get("verdict") or "?").upper()
    turns = s.get("turns", "?")
    err = s.get("last_error", "")
    ts = str(s.get("timestamp") or "")[:19]
    line = f"last run: {verdict}, {turns} turn(s)"
    if err:
        line += f" (error: {err[:80]})"
    if ts:
        line += f" @ {ts}"
    return line
