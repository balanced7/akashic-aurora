"""arsenal.panel.probe -- is this service up, down, or could we not look?

Every probe answers UP / DOWN / **UNKNOWN**, and UNKNOWN is never collapsed into DOWN. That is the
`reachability` verb's doctrine, adopted here for the same reason: the panel is the screen Daniel reads
when something is broken, so "no such process" and "I could not enumerate processes" must not look the
same. A status probe that answers DOWN when schtasks was blocked sends him hunting a dead service that
is fine.

EVERY I/O SEAM IS INJECTABLE (`Prober(connect=..., processes=..., run=..., service_status=...)`). The
test harness supplies fakes, so the whole status surface can be pinned without touching a real daemon,
a real scheduled task or a real port. The same shape is what let the desk-themes tests run 245 green on
fakes while the lights were live.

PROBES NEVER START OR STOP ANYTHING. Read-only by construction: a TCP connect, a process enumeration, a
`schtasks /query`, a service status read. Running `/api/status` twice must not change any answer, which
`tests/test_phone_panel.py` pins.
"""
from __future__ import annotations

import socket
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

UP = "UP"
DOWN = "DOWN"
UNKNOWN = "UNKNOWN"

#: Windows: never flash a console window for a background query (the 2026-09-05 cmd-spam fix).
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

#: How long a status probe may take. The panel is read on a phone over a tailnet, so a black-holed
#: address must not hold the whole screen hostage -- same budget the reachability verb uses.
DEFAULT_TIMEOUT_S = 1.0

#: `schtasks` and `sc` are the two external readers. Named as argv vectors, never strings.
SCHTASKS = ("schtasks",)
SC = ("sc",)


def _norm(element: str) -> str:
    """One argv element, comparable across the two ways Windows spells a path.

    FORWARD SLASHES, and no backslash in any pattern source: a heredoc or a tool layer can collapse
    `\\` and turn `\\b`/`\\t`/`\\n` into control characters that silently match nothing (a lesson this
    house paid for while hunting a process by its command line)."""
    return str(element).replace("\\", "/").rstrip("/")


class Prober:
    """The status reader. Construct once, use per service; every seam defaults to the real thing."""

    def __init__(self,
                 *,
                 connect: Optional[Callable[[str, int, float], bool]] = None,
                 processes: Optional[Callable[[], List[Sequence[str]]]] = None,
                 run: Optional[Callable[[Sequence[str]], "tuple[int, str]"] ] = None,
                 service_status: Optional[Callable[[str], Optional[str]]] = None,
                 timeout: float = DEFAULT_TIMEOUT_S) -> None:
        self._connect = connect or _tcp_answers
        self._processes = processes or _proc_argvs
        self._run = run or _run_argv
        self._service_status = service_status
        self.timeout = timeout

    # ------------------------------------------------------------------------------ public
    def probe(self, spec) -> Dict[str, Any]:
        """{state, why, detail} for one spec. Never raises: a probe that dies is UNKNOWN + reason."""
        kind = (spec.probe or {}).get("kind")
        try:
            if kind == "port":
                return self._port(spec.probe)
            if kind == "argv":
                return self._argv(spec.probe)
            if kind == "task":
                return self._task(spec.probe)
            if kind == "service":
                return self._service(spec.probe)
            if kind == "absent":
                return {"state": DOWN, "why": spec.probe.get("why", "not installed on this PC"),
                        "detail": {"probe": "absent"}}
        except Exception as exc:                                  # a probe must never break the screen
            return {"state": UNKNOWN, "detail": {"probe": kind},
                    "why": f"the {kind} probe failed: {type(exc).__name__}: {exc}"}
        return {"state": UNKNOWN, "detail": {"probe": kind},
                "why": f"unknown probe kind {kind!r} (the loader validates this; seeing it means the "
                       f"spec was built by hand)"}

    # ------------------------------------------------------------------------------ kinds
    def _port(self, probe: Dict[str, Any]) -> Dict[str, Any]:
        host, port = probe.get("host", "127.0.0.1"), int(probe["port"])
        answers = bool(self._connect(host, port, self.timeout))
        return {"state": UP if answers else DOWN,
                "why": "" if answers else f"nothing answers a connect on {host}:{port}",
                "detail": {"probe": "port", "host": host, "port": port}}

    def _argv(self, probe: Dict[str, Any]) -> Dict[str, Any]:
        want = [_norm(x) for x in probe.get("match") or ()]
        try:
            found = [[_norm(a) for a in argv] for argv in self._processes()]
        except Exception as exc:
            return {"state": UNKNOWN, "detail": {"probe": "argv"},
                    "why": f"the process list could not be read: {type(exc).__name__}: {exc} -- "
                           f"this is NOT a claim that the service is down"}
        hits = [argv for argv in found if all(any(w == a for a in argv) for w in want)]
        if hits:
            return {"state": UP, "why": "", "detail": {"probe": "argv", "matches": len(hits)}}
        return {"state": DOWN, "detail": {"probe": "argv", "matches": 0},
                "why": "no live process carries those arguments (matched on argv ELEMENTS, never on "
                       "a substring of the joined command line -- the shell that runs this check "
                       "contains this check's own text)"}

    def _task(self, probe: Dict[str, Any]) -> Dict[str, Any]:
        name = probe["name"]
        rc, out = self._run(list(SCHTASKS) + ["/query", "/tn", name, "/fo", "list"])
        if rc != 0:
            low = (out or "").strip()
            return {"state": UNKNOWN, "detail": {"probe": "task", "name": name, "rc": rc},
                    "why": f"`schtasks /query /tn {name}` did not answer (rc {rc}): "
                           f"{low[:200] or '(no output)'} -- a task the reader cannot query is "
                           f"UNKNOWN, not DOWN"}
        status = ""
        for line in (out or "").splitlines():
            key, _, value = line.partition(":")
            if key.strip().lower() == "status":
                status = value.strip()
                break
        low = status.lower()
        if low == "running":
            return {"state": UP, "why": "", "detail": {"probe": "task", "name": name,
                                                       "status": status}}
        if low in ("ready", "disabled", "queued"):
            return {"state": DOWN, "detail": {"probe": "task", "name": name, "status": status},
                    "why": f"the task exists and is {status}; it is not running now"}
        return {"state": UNKNOWN, "detail": {"probe": "task", "name": name, "status": status},
                "why": f"`schtasks` answered without a status line I recognise ({status!r})"}

    def _service(self, probe: Dict[str, Any]) -> Dict[str, Any]:
        name = probe["name"]
        status = None
        if self._service_status is not None:
            status = self._service_status(name)
        else:
            try:
                import psutil
                status = psutil.win_service_get(name).status()
            except Exception as exc:
                rc, out = self._run(list(SC) + ["query", name])
                if rc != 0:
                    return {"state": UNKNOWN, "detail": {"probe": "service", "name": name},
                            "why": f"the Windows service {name!r} could not be read "
                                   f"({type(exc).__name__}); `sc query` said: "
                                   f"{(out or '').strip()[:200] or f'rc {rc}'}"}
                text = (out or "").lower()
                if "running" in text:
                    status = "running"
                elif "stopped" in text:
                    status = "stopped"
        if status is None:
            return {"state": UNKNOWN, "detail": {"probe": "service", "name": name},
                    "why": "the service reader returned nothing"}
        status = str(status).lower()
        if status == "running":
            return {"state": UP, "why": "", "detail": {"probe": "service", "name": name,
                                                       "status": status}}
        if status in ("stopped", "stopping", "start_pending", "paused"):
            return {"state": DOWN, "detail": {"probe": "service", "name": name, "status": status},
                    "why": f"the service is {status}"}
        return {"state": UNKNOWN, "detail": {"probe": "service", "name": name, "status": status},
                "why": f"the service reported {status!r}"}


# ------------------------------------------------------------------------------- real seams
def _tcp_answers(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _proc_argvs() -> List[List[str]]:
    """Every live process's argv. psutil is the house's reader (reachability uses it too)."""
    import psutil
    out: List[List[str]] = []
    for proc in psutil.process_iter(["cmdline"]):
        try:
            out.append([str(a) for a in (proc.info.get("cmdline") or [])])
        except Exception:
            continue
    return out


def _run_argv(argv: Sequence[str]) -> "tuple[int, str]":
    """Run a READ-ONLY query. A list and `shell=False`: nothing here is ever interpreted."""
    try:
        done = subprocess.run(list(argv), capture_output=True, text=True, timeout=10,
                              creationflags=_NO_WINDOW)
        return done.returncode, (done.stdout or "") + (done.stderr or "")
    except Exception as exc:
        return 1, f"{type(exc).__name__}: {exc}"


def tail(path: Optional[str], *, lines: int = 12, max_bytes: int = 4096) -> List[str]:
    """The last `lines` non-empty lines of a log the ALLOWLIST declared, or [] with a reason.

    The path always comes from the spec, never from a request: a log endpoint that takes a path is a
    file-read endpoint, and this API is reachable from a phone."""
    if not path:
        return []
    try:
        st = Path(path).stat()
        with open(path, "rb") as fh:
            fh.seek(max(0, st.st_size - max_bytes))
            chunk = fh.read().decode("utf-8", "replace")
        return [ln for ln in chunk.splitlines() if ln.strip()][-lines:]
    except FileNotFoundError:
        return [f"(no log file at {path})"]
    except Exception as exc:
        return [f"(log unreadable: {type(exc).__name__}: {exc})"]
