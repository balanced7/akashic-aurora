"""arsenal.panel.actions -- the ONLY place in this package that changes the world.

Everything else is a reader. This module takes a (service, verb) pair that the allowlist already
accepted and performs it -- and its whole design is about the fact that it is reachable from a phone
that may be in Daniel's pocket, in another building, on a tailnet.

THE FIVE INVARIANTS, and each one has a pin in `tests/test_phone_panel.py`:

  1. NO SHELL, EVER. `start` is `subprocess.Popen(list(spec.start), shell=False)`. There is no branch
     that builds a string. `shell=True` appears nowhere in this package, and a test asserts that by
     reading this file's own source -- because "we were careful" is not a property that survives a
     future edit.
  2. NO REQUEST DATA REACHES A COMMAND. The caller passes a ServiceSpec (from the allowlist) and one
     of three literal verbs. There is no parameter through which a request string could travel.
  3. A STOP MUST PROVE ITS TARGET. `kill_argv` matches on argv ELEMENTS (never a substring of a
     joined command line -- the shell that launched this check contains this check's own text), and
     it re-reads the exact pid's argv immediately before terminating it. If the re-read disagrees,
     nothing is killed and the verb fails. A broken predicate must fail SAFE.
  4. STOP BEFORE START, AND NEVER HALF. `restart` stops first; if the stop did not verify, the start
     does not run and the caller is told. A restart that starts a second copy beside a live one is how
     a port ends up with two listeners.
  5. EVERY ACTION IS VERIFIED, NOT ASSUMED. After starting, the panel waits for the service's own
     probe to read UP (bounded), and reports what it SAW. `ok: true` means the probe agreed, never
     "the process was spawned".

RESTART OF A `task_end` SERVICE. A scheduled task is started by `schtasks /Run`, so a task-backed
service declares `restart: task_run` and gets end-then-run. Nothing here guesses which mechanism a
service uses: the stop kind and the restart style are both declared in the allowlist.
"""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from .probe import DOWN, UP, Prober

#: Windows: a spawned daemon must not flash a console (2026-09-05) and must outlive the API process.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_DETACHED = _NO_WINDOW | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

#: How long to wait for a started service's own probe to say UP. Long enough for a Python server to
#: bind, short enough that a phone request does not time out.
START_WAIT_S = 12.0
POLL_S = 0.25

#: Executables whose argv IS the whole action (they exit immediately and their exit status is the
#: answer). These are RUN and their status is checked, never spawned detached where the status is lost.
CONTROL_COMMANDS = ("schtasks", "net", "sc", "sc.exe")


@dataclass
class ActionResult:
    """What happened, in terms the audit line and the screen can both use."""

    service: str
    verb: str
    ok: bool
    state: str                                  # the state AFTER the verb, per the probe
    detail: str = ""
    pids: List[int] = field(default_factory=list)
    elapsed_ms: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {"service": self.service, "verb": self.verb, "ok": self.ok, "state": self.state,
                "detail": self.detail, "pids": list(self.pids), "elapsed_ms": self.elapsed_ms}


class ActionRefused(RuntimeError):
    """The action is not allowed for this service. Raised BEFORE anything is touched."""


class ActionRunner:
    """Performs allowlisted verbs. All seams injectable, so tests touch no real daemon."""

    def __init__(self,
                 *,
                 popen: Optional[Callable[..., Any]] = None,
                 run: Optional[Callable[..., Any]] = None,
                 processes: Optional[Callable[[], List[Sequence[str]]]] = None,
                 terminate: Optional[Callable[[int], None]] = None,
                 prober: Optional[Prober] = None,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep,
                 start_wait_s: float = START_WAIT_S) -> None:
        self._popen = popen or _real_popen
        self._run = run or _real_run
        self._processes = processes or _real_processes
        self._terminate = terminate or _real_terminate
        self.prober = prober or Prober()
        self._clock = clock
        self._sleep = sleep
        self.start_wait_s = start_wait_s

    # -------------------------------------------------------------------------------- public
    def perform(self, spec, verb: str) -> ActionResult:
        """Run one verb against one spec. Raises ActionRefused before touching anything."""
        if verb not in spec.allowed_verbs():
            raise ActionRefused(
                f"{spec.id!r} does not accept {verb!r} (it declares: "
                f"{', '.join(spec.allowed_verbs()) or 'no actions'}"
                + (f" -- {spec.why_no_actions}" if spec.why_no_actions else "") + ")")
        t0 = self._clock()
        if verb == "start":
            res = self._start(spec)
        elif verb == "stop":
            res = self._stop(spec)
        else:
            res = self._restart(spec)
        res.elapsed_ms = int((self._clock() - t0) * 1000)
        return res

    # -------------------------------------------------------------------------------- verbs
    def _start(self, spec) -> ActionResult:
        if spec.start is None:
            return ActionResult(spec.id, "start", False, DOWN, "no start is declared for this service")
        before = self.prober.probe(spec)
        if before.get("state") == UP:
            return ActionResult(spec.id, "start", True, UP,
                                "already up before the request; nothing was started")
        exe = str(spec.start[0]).replace("\\", "/").rsplit("/", 1)[-1].lower()
        if exe in CONTROL_COMMANDS:
            # A CONTROL COMMAND, not a daemon: `schtasks /Run` / `net start` exit immediately and their
            # exit status IS the answer, so wait for it. Spawning these detached would throw the status
            # away and leave the verb reporting "spawned" for a task that refused to start.
            rc, out = self._run(list(spec.start))
            if rc != 0:
                return ActionResult(spec.id, "start", False, before.get("state", DOWN),
                                    f"`{' '.join(spec.start)}` failed (rc {rc}): "
                                    f"{(out or '').strip()[:200]}")
            after = self._wait_up(spec)
            return ActionResult(spec.id, "start", after.get("state") == UP,
                                after.get("state", DOWN),
                                f"control command accepted; probe now reads {after.get('state')}"
                                + (f" ({after.get('why')})" if after.get("why") else ""))
        try:
            proc = self._popen(list(spec.start), cwd=spec.start_cwd, detached=True)
        except Exception as exc:
            return ActionResult(spec.id, "start", False, DOWN,
                                f"the spawn failed: {type(exc).__name__}: {exc}")
        pids = [p for p in [getattr(proc, "pid", None)] if isinstance(p, int)]
        after = self._wait_up(spec)
        ok = after.get("state") == UP
        detail = ("started and the probe reads UP" if ok else
                  f"spawned (pid {pids[0] if pids else '?'}) but the probe still reads "
                  f"{after.get('state')}: {after.get('why', '')}")
        return ActionResult(spec.id, "start", ok, after.get("state", DOWN), detail, pids)

    def _stop(self, spec) -> ActionResult:
        stop = spec.stop or {}
        kind = stop.get("type")
        if kind is None:
            return ActionResult(spec.id, "stop", False, UP, "no stop is declared for this service")
        if kind == "none":
            return ActionResult(spec.id, "stop", False, UP,
                                f"refused: {stop.get('why', 'stopping this from the phone is refused')}")
        if kind == "task_end":
            rc, out = self._run(["schtasks", "/End", "/TN", stop["name"]])
            if rc != 0:
                return ActionResult(spec.id, "stop", False, UP,
                                    f"`schtasks /End /TN {stop['name']}` failed (rc {rc}): "
                                    f"{(out or '').strip()[:200]}")
            after = self._wait_down(spec)
            return ActionResult(spec.id, "stop", after.get("state") == DOWN,
                                after.get("state", UP),
                                f"schtasks /End sent; probe now reads {after.get('state')}"
                                + (f" ({after.get('why')})" if after.get("why") else ""))
        if kind == "service_stop":
            rc, out = self._run(["net", "stop", stop["name"]])
            if rc != 0:
                return ActionResult(spec.id, "stop", False, UP,
                                    f"`net stop {stop['name']}` failed (rc {rc}): "
                                    f"{(out or '').strip()[:200]}")
            after = self._wait_down(spec)
            return ActionResult(spec.id, "stop", after.get("state") == DOWN,
                                after.get("state", UP),
                                f"net stop sent; probe now reads {after.get('state')}")
        # kill_argv -- invariant 3 above
        pids, why = self._targets(stop.get("match") or ())
        if not pids:
            return ActionResult(spec.id, "stop", False, UP, why or "no matching process to stop")
        killed: List[int] = []
        gone: List[int] = []
        problems: List[str] = []
        for pid in pids:
            argv_now = self._argv_of(pid)
            if argv_now is None:
                # VANISHED IS NOT THE SAME AS CHANGED, and the drill of 2026-10-31 is why this branch
                # exists: `py -m http.server 8901` is a LAUNCHER SHIM that exits while its python child
                # keeps the port, so between listing the targets and killing them the shim is routinely
                # gone. Reporting that as a refusal made a correct stop look broken. A vanished pid is
                # simply not a target any more -- it was never going to be killed, so nothing is lost.
                gone.append(pid)
                continue
            want = stop.get("match") or ()
            if not all(any(_same(w, a) for a in argv_now) for w in want):
                # A pid whose argv CHANGED is the dangerous case: pid reuse, or a predicate that matched
                # something else. Leave it alive and say so.
                problems.append(f"pid {pid} no longer matches its declared argv -- left alone")
                continue
            try:
                self._terminate(pid)
                killed.append(pid)
            except Exception as exc:
                problems.append(f"pid {pid}: {type(exc).__name__}: {exc}")
        after = self._wait_down(spec)
        ok = bool(killed) and after.get("state") == DOWN
        detail = f"terminated {killed}" if killed else "nothing was terminated"
        if gone:
            detail += f"; already gone: {gone}"
        if problems:
            detail += "; " + "; ".join(problems)
        detail += f"; probe now reads {after.get('state')}"
        return ActionResult(spec.id, "stop", ok, after.get("state", UP), detail, killed)

    def _restart(self, spec) -> ActionResult:
        stopped = self._stop(spec)
        if not stopped.ok:
            return ActionResult(spec.id, "restart", False, stopped.state,
                                "the stop did not verify, so the start did NOT run: "
                                + stopped.detail, stopped.pids)
        started = self._start(spec)
        return ActionResult(spec.id, "restart", started.ok, started.state,
                            f"stop: {stopped.detail} | start: {started.detail}",
                            stopped.pids + started.pids)

    # -------------------------------------------------------------------------------- helpers
    def _wait_up(self, spec) -> Dict[str, Any]:
        return self._wait(spec, UP)

    def _wait_down(self, spec) -> Dict[str, Any]:
        return self._wait(spec, DOWN)

    def _wait(self, spec, want: str) -> Dict[str, Any]:
        deadline = self._clock() + self.start_wait_s
        last = self.prober.probe(spec)
        while last.get("state") != want and self._clock() < deadline:
            self._sleep(POLL_S)
            last = self.prober.probe(spec)
        return last

    def _targets(self, match: Sequence[str]) -> "tuple[List[int], str]":
        """Every pid whose argv elements carry the declared match. Fails CLOSED with a reason."""
        try:
            rows = self._processes()
        except Exception as exc:
            return [], f"the process list could not be read: {type(exc).__name__}: {exc}"
        pids: List[int] = []
        for row in rows or ():
            argv = [str(a) for a in row]
            if all(any(_same(w, a) for a in argv) for w in match):
                cand = self._pid_of(row)
                if cand is not None:
                    pids.append(cand)
        if not pids:
            return [], "no live process matches the declared argv, so there is nothing to stop"
        return pids, ""

    def _pid_of(self, row) -> Optional[int]:
        """The pid of a process row, if the row carries one (real psutil rows are argv lists, so the
        real seam passes pids separately -- see _real_processes)."""
        return getattr(row, "pid", None)

    def _argv_of(self, pid: int) -> Optional[List[str]]:
        """Re-read one pid's argv immediately before terminating it (invariant 3)."""
        for row in self._processes() or ():
            if self._pid_of(row) == pid:
                return [str(a) for a in row]
        return None


def _same(want: str, got: str) -> bool:
    """One argv element compared to another, forward-slashed and case-folded (Windows paths)."""
    return str(want).replace("\\", "/").rstrip("/").lower() == \
        str(got).replace("\\", "/").rstrip("/").lower()


# ------------------------------------------------------------------------------- real seams
def _real_popen(argv: Sequence[str], cwd: Optional[str] = None, detached: bool = True):
    """Spawn a daemon. A LIST, `shell=False`, no window, in its own process group.

    `close_fds` and the inherited handles are the point: the API process may be restarted from the
    phone while the daemon it started keeps running, so the child must not hold this process open."""
    return subprocess.Popen(list(argv), cwd=cwd, shell=False, close_fds=True,
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=_DETACHED if detached else _NO_WINDOW)


def _real_run(argv: Sequence[str]):
    try:
        done = subprocess.run(list(argv), capture_output=True, text=True, timeout=20,
                              shell=False, creationflags=_NO_WINDOW)
        return done.returncode, (done.stdout or "") + (done.stderr or "")
    except Exception as exc:
        return 1, f"{type(exc).__name__}: {exc}"


class _Proc:
    """A process row carrying its pid AND its argv, so `_pid_of` and the kill check agree."""

    __slots__ = ("pid", "argv")

    def __init__(self, pid: int, argv: Sequence[str]) -> None:
        self.pid = pid
        self.argv = [str(a) for a in argv]

    def __iter__(self):
        return iter(self.argv)


def _real_processes() -> List[_Proc]:
    import psutil
    out: List[_Proc] = []
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            out.append(_Proc(int(proc.info["pid"]), proc.info.get("cmdline") or []))
        except Exception:
            continue
    return out


def _real_terminate(pid: int) -> None:
    import psutil
    proc = psutil.Process(pid)
    proc.terminate()
    try:
        proc.wait(timeout=3.0)
    except Exception:
        proc.kill()
