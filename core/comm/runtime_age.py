"""runtime_age (T116) -- how much code a RUNNING process cannot possibly contain.

T114 taught heartbeats to stamp the commit they run, and the roster to derive
STALE-CODE from that stamp. It works perfectly for every process started after it
shipped, and is blind to every process that predates it -- which is the entire
population that made the gap worth closing. On 2026-07-28 a fix was committed,
tested, pushed and announced while both runners kept executing the module they
imported an hour earlier; the roster said LIVE and nothing could say LIVE ON WHAT.

This is the fallback that needs no cooperation from the process, because the
processes that most need catching are exactly the ones too old to have been taught
to report. The evidence is already on the machine:

    the runner lock records a pid
    the OS records when that pid started
    git records when each commit landed

    bifrost:runner:deepseek  pid 44680  started 04:38:49   |  HEAD 05:51:27
    bifrost:runner:kimi      pid 47800  started 04:38:55   |  16 commits between

WHAT THIS MAY AND MAY NOT CLAIM. A process older than a commit definitely does not
contain it. A commit landing after a process started does not necessarily change
that process's behaviour -- it may touch nothing the process imports. So the answer
is a FACT ("N commits have landed since this process started"), never a verdict
("this process is wrong"). Where T114's stamp exists it is ground truth and wins;
this is an upper bound, and `source` always says which one answered. Conflating
"started before" with "definitely running the wrong code" would make the signal
arguable, and an arguable signal gets ignored -- the failure this arc keeps paying
for.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pid -> ISO start time (or ""). A process's start time cannot change, so this is a
# constant per pid; re-probing per doctor tick would spend a subprocess to re-learn it.
_START_CACHE: Dict[int, str] = {}
_HEAD_SHA: Optional[str] = None


def _git(*args: str, timeout: int = 5) -> str:
    try:
        # ENCODING EXPLICIT. text=True alone decodes with the LOCALE codec (cp1252 here),
        # so ONE commit subject carrying a character outside cp1252 raised
        # UnicodeDecodeError, hit the except below, and returned "" -- which
        # commits_since() reads as ZERO COMMITS LANDED, i.e. "your code is current".
        # Measured 2026-08-24: reported 0 while git reported 102, blinded by an emoji in
        # this repo's own commit subject. The zero-on-doubt doctrine below is right for a
        # COUNT and backwards for a STALENESS CHECK -- silence there means "nothing
        # changed", which is the unsafe direction. Git speaks UTF-8; read it as UTF-8.
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=timeout, stdin=subprocess.DEVNULL, close_fds=True)
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def head_sha() -> str:
    global _HEAD_SHA
    if _HEAD_SHA is None:
        _HEAD_SHA = _git("rev-parse", "--short=12", "HEAD")
    return _HEAD_SHA or ""


def commits_since(iso_ts: str) -> int:
    """How many commits landed after `iso_ts`. Zero on any doubt -- an inflated count
    would be a louder claim than the evidence supports."""
    if not iso_ts:
        return 0
    out = _git("log", f"--since={iso_ts}", "--oneline")
    return len([ln for ln in out.splitlines() if ln.strip()]) if out else 0


def _probe_start_time(pid: int) -> str:
    """The OS's record of when `pid` started, ISO-8601, or "" if unknowable.

    Windows-specific by necessity (this fleet runs on Windows). On any other platform,
    or a dead/unreadable pid, this returns "" and every caller degrades to UNKNOWN --
    never to STALE. Accusing a process we cannot read is how a real staleness report
    gets tuned out."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f"(Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue)"
             f".StartTime.ToString('o')"],
            capture_output=True, text=True, timeout=10,
            stdin=subprocess.DEVNULL, close_fds=True)
        return (r.stdout or "").strip()
    except Exception:
        return ""


def _redis():
    try:
        from core.comm.bus import get_bus
        return get_bus("runtime_age")._client
    except Exception:
        return None


def start_time(pid: int) -> str:
    """Cached `_probe_start_time` -- CROSS-PROCESS (P8). A process's start time is a
    cross-process constant, and the per-process dict alone was a boot-path
    regression: the door-gate's probe child is a FRESH process every time, so every
    door probe re-paid one PowerShell spawn PER PID and boot degraded 1.3s -> 5.0s
    (the gate's own budget) -- the detector built to catch stale processes made the
    door look wedged. Redis carries the value (1h TTL, cheap staleness bound for
    pid reuse); the subprocess runs only on a truly cold fleet."""
    try:
        pid = int(pid)
    except Exception:
        return ""
    if pid <= 0:
        return ""
    if pid in _START_CACHE:
        return _START_CACHE[pid]
    c = _redis()
    key = f"{os.environ.get('BIFROST_NAMESPACE', 'bifrost')}:pidstart:{pid}"
    if c is not None:
        try:
            hit = c.get(key)
            if hit is not None:
                _START_CACHE[pid] = str(hit)
                return _START_CACHE[pid]
        except Exception:
            pass
    try:
        val = _probe_start_time(pid) or ""
    except Exception:
        val = ""
    _START_CACHE[pid] = val
    if c is not None:
        try:
            # empty is cached too ("" = unreadable pid): an unreadable pid re-probed
            # by every fresh process is the same regression wearing a failure mask.
            c.set(key, val, ex=3600)
        except Exception:
            pass
    return val


def describe(*, pid: int, started_at: str, stamped_sha: str = "") -> Dict[str, Any]:
    """The verdict for one process, with its provenance attached.

    Order matters: a self-reported stamp is EVIDENCE and an age estimate is an upper
    bound, so the stamp wins whenever it exists. A fallback that overrides evidence is
    not a fallback."""
    head = head_sha()
    stamped = str(stamped_sha or "").strip()
    if stamped and head:
        return {"pid": pid, "started_at": started_at, "stamped_sha": stamped,
                "head_sha": head, "commits_behind": 0 if stamped == head else -1,
                "state": "current" if stamped == head else "stale", "source": "stamp"}
    if not started_at:
        return {"pid": pid, "started_at": "", "stamped_sha": "", "head_sha": head,
                "commits_behind": 0, "state": "unknown", "source": "none"}
    behind = commits_since(started_at)
    return {"pid": pid, "started_at": started_at, "stamped_sha": "", "head_sha": head,
            "commits_behind": behind,
            "state": "stale" if behind > 0 else "current", "source": "process_age"}


def for_agent(agent: str, *, client=None) -> Dict[str, Any]:
    """Resolve `agent`'s runner pid from its lock, then describe it. Never raises: the
    doctor calls this on a hot path, and an observability probe that can break the
    diagnostic is worse than no probe."""
    try:
        if client is None:
            from core.comm.bus import get_bus
            client = get_bus("runtime_age")._client
        ns = os.environ.get("BIFROST_NAMESPACE", "bifrost")
        raw = client.get(f"{ns}:runner:{agent}") if client is not None else None
        rec = json.loads(raw) if raw else {}
        pid = int(rec.get("pid") or 0)
        return describe(pid=pid, started_at=start_time(pid) if pid else "")
    except Exception:
        return {"pid": 0, "started_at": "", "stamped_sha": "", "head_sha": "",
                "commits_behind": 0, "state": "unknown", "source": "none"}


def line(agent: str, verdict: Optional[Dict[str, Any]] = None) -> str:
    """One operator-facing sentence, or "" when there is nothing to say. States the
    fact and its provenance, and never converts an upper bound into an accusation."""
    v = verdict if verdict is not None else for_agent(agent)
    if v.get("state") != "stale":
        return ""
    if v.get("source") == "stamp":
        return (f"{agent}: STALE-CODE -- running {str(v.get('stamped_sha'))[:12]}, "
                f"HEAD is {str(v.get('head_sha'))[:12]}. Restart to pick up fixes.")
    started = str(v.get("started_at") or "")[:19]
    return (f"{agent}: STALE-CODE (by process age) -- pid {v.get('pid')} started "
            f"{started}; {v.get('commits_behind')} commit(s) have landed since, and it "
            f"cannot be running any of them. Restart to pick up fixes.")
