"""wake_seat -- the per-session wake-seat protocol (T029 Wave 2, the R1/R16 fix).

One agent id, N concurrent sessions: each session's watcher holds its OWN seat file
(bifrost_wake_<agent>_<session>.pid), so same-id sessions never collide over one seat --
the 2026-07-10 kill loop (session B's start taskkilled session A's LIVE watcher) becomes
structurally impossible. Duty transfers by displacement + stand-down, never by killing:
the session-start janitor cleans seats whose pid is DEAD, migrates the one legacy
name-keyed ghost (K6), and reaps a LIVE watcher only on two-factor-proven orphanhood:

  K7  activity marker stale (turn cadence is NOT liveness -- an idle-but-alive session
      must be immune) AND the watcher's parent chain is dead (the WMI walk that cracked
      the live case; pid-recycle guarded by creation-time ordering).
  K8  ANY verification error = alive. False-alive leaves a stale seat for the janitor's
      next pass; false-dead re-opens the kill loop. Fail toward alive, always.

Every decision appends one line to the provenance log (bifrost_wake_<agent>.reap.log) so
a reap is auditable from the log alone -- never again mistaken for a watcher crash.
Fenced design + reconciliation: docs/resilience-wave2-seat-design-2026-07.md.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from typing import Callable, Dict, List, Optional, Tuple

# Names that identify a live harness ancestor (Claude Desktop engine, CLI engine, or a
# node-hosted harness). Substring match, case-insensitive, on the process NAME only.
HARNESS_NAME_HINTS = ("claude", "node")
FRESH_MIN_DEFAULT = 30                     # AKASHIC_WAKE_MARKER_FRESH_MIN overrides
_RECYCLE_SLACK_MS = 1000                   # parent may not be YOUNGER than child by more


# ---------------------------------------------------------------- paths + seat files
def seat_path(agent: str, session_id: Optional[str] = None, tmp: Optional[str] = None) -> str:
    """Session-scoped seat file; the legacy per-agent path when session_id is falsy."""
    base = tmp or tempfile.gettempdir()
    if session_id:
        return os.path.join(base, f"bifrost_wake_{agent}_{session_id}.pid")
    return os.path.join(base, f"bifrost_wake_{agent}.pid")


def activity_marker_path(agent: str, session_id: str, tmp: Optional[str] = None) -> str:
    """Touched at every hook firing for the session -- the cheap liveness fast path."""
    return os.path.join(tmp or tempfile.gettempdir(), f"bifrost_wake_{agent}_{session_id}.alive")


def iter_seats(agent: str, tmp: Optional[str] = None) -> List[Tuple[str, Optional[str]]]:
    """All seat files for THIS agent: [(path, session_id_or_None_for_legacy)].
    Prefix-exact so agent 'claude' never enumerates 'claude-2' seats."""
    base = tmp or tempfile.gettempdir()
    out: List[Tuple[str, Optional[str]]] = []
    legacy = seat_path(agent, None, base)
    if os.path.exists(legacy):
        out.append((legacy, None))
    prefix = f"bifrost_wake_{agent}_"
    try:
        for name in os.listdir(base):
            if name.startswith(prefix) and name.endswith(".pid"):
                out.append((os.path.join(base, name), name[len(prefix):-4]))
    except Exception:
        pass
    return out


def read_pid(path: str) -> Optional[int]:
    try:
        return int(open(path).read().strip())
    except Exception:
        return None


def touch_activity(agent: str, session_id: str, tmp: Optional[str] = None) -> None:
    try:
        with open(activity_marker_path(agent, session_id, tmp), "w") as f:
            f.write(str(time.time()))
    except Exception:
        pass


def activity_age_min(agent: str, session_id: str, now: Optional[float] = None,
                     tmp: Optional[str] = None) -> Optional[float]:
    """Minutes since the session's last hook firing; None when no marker exists."""
    try:
        ts = float(open(activity_marker_path(agent, session_id, tmp)).read().strip())
        return max(0.0, ((now if now is not None else time.time()) - ts) / 60.0)
    except Exception:
        return None


# ---------------------------------------------------------------- session tombstones (T086 S1)
# The missing discriminator behind C1-5: marker freshness, listener pids, and parent chains
# all prove a PROCESS or the shared HOST lives -- none of them can say "this SESSION ended".
# The tombstone is that fact, written at SessionEnd (clean_death leg 0), consulted by the
# free_if_dead ladder (skip grace), the janitor (override chain-immunity), and the stop hook
# (a resurrected turn of an ended session stands down unarmed). Kill switch: AKASHIC_TOMBSTONE=0.
# Reconciliation D2 (t086-seat-reconciliation-2026-07-16.md): durable state beats signal games.

def tombstone_path(session_id: str, tmp: Optional[str] = None) -> str:
    return os.path.join(tmp or tempfile.gettempdir(), f"akashic_session_ended_{session_id}.tomb")


def write_tombstone(session_id: str, tmp: Optional[str] = None, c=None) -> bool:
    """Record that `session_id` ENDED: local file (bus-independent) + Redis key (shared,
    7d TTL). Best-effort both legs; True if either landed."""
    if not session_id or os.getenv("AKASHIC_TOMBSTONE", "1") == "0":
        return False
    ok = False
    try:
        with open(tombstone_path(session_id, tmp), "w") as f:
            f.write(str(time.time()))
        ok = True
    except Exception:
        pass
    try:
        cli = c
        if cli is None:
            from core.comm.bus import get_bus
            cli = get_bus("control")._client
        if cli is not None:
            ns = os.environ.get("BIFROST_NAMESPACE", "bifrost")
            cli.set(f"{ns}:session:ended:{session_id}", str(time.time()), ex=7 * 24 * 3600)
            ok = True
    except Exception:
        pass
    return ok


def is_tombstoned(session_id: str, tmp: Optional[str] = None, c=None) -> bool:
    """Has this session ENDED? File first (cheap, offline-safe), Redis second.
    FAIL TOWARD ALIVE: any probe error reads as not-tombstoned -- a tombstone may only
    ACCELERATE a release, never cause one on a guess (S1c pin)."""
    if not session_id or os.getenv("AKASHIC_TOMBSTONE", "1") == "0":
        return False
    try:
        if os.path.exists(tombstone_path(session_id, tmp)):
            return True
    except Exception:
        pass
    try:
        cli = c
        if cli is None:
            from core.comm.bus import get_bus
            cli = get_bus("control")._client
        if cli is not None:
            ns = os.environ.get("BIFROST_NAMESPACE", "bifrost")
            return bool(cli.exists(f"{ns}:session:ended:{session_id}"))
    except Exception:
        pass
    return False


# ---------------------------------------------------------------- provenance log
def provenance_path(agent: str, tmp: Optional[str] = None) -> str:
    return os.path.join(tmp or tempfile.gettempdir(), f"bifrost_wake_{agent}.reap.log")


def append_provenance(agent: str, line: str, tmp: Optional[str] = None, keep: int = 400) -> None:
    """One auditable line per decision. Best-effort; trims to the last `keep` lines."""
    path = provenance_path(agent, tmp)
    try:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {line}\n")
        if os.path.getsize(path) > 256 * 1024:
            lines = open(path, encoding="utf-8", errors="replace").read().splitlines()[-keep:]
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------- process evidence
def process_snapshot(timeout_s: int = 10) -> Optional[Dict[int, Dict]]:
    """One WMI pass -> {pid: {ppid, name, cmdline, created_ms}}. None on any failure (K8)."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,"
             "Name,CommandLine,CreationDate | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=timeout_s).stdout
        rows = json.loads(out)
        if isinstance(rows, dict):
            rows = [rows]
        snap: Dict[int, Dict] = {}
        for r in rows:
            try:
                created = None
                m = re.search(r"(\d{10,})", str(r.get("CreationDate") or ""))
                if m:
                    created = int(m.group(1))
                snap[int(r["ProcessId"])] = {
                    "ppid": int(r.get("ParentProcessId") or 0),
                    "name": str(r.get("Name") or ""),
                    "cmdline": str(r.get("CommandLine") or ""),
                    "created": created,
                }
            except Exception:
                continue
        return snap or None
    except Exception:
        return None


def is_watcher(pid: int, snap: Dict[int, Dict]) -> bool:
    """Identity check: the pid is OUR kind of process (never judge a recycled pid)."""
    return "bifrost_wake" in (snap.get(pid, {}).get("cmdline") or "")


def chain_alive(pid: int, snap: Dict[int, Dict], max_depth: int = 12) -> Tuple[bool, str]:
    """Walk the watcher's parent chain. Dead/recycled link before a harness ancestor =
    the owning session is gone. Ambiguity fails toward alive (K8 direction)."""
    cur = snap.get(pid)
    if cur is None:
        return False, f"pid {pid} not in snapshot"
    for _ in range(max_depth):
        ppid = cur.get("ppid") or 0
        if ppid <= 4:                                  # System/Idle -- walked off the top
            return True, "chain intact to system root (no harness ancestor named -- fail-safe alive)"
        parent = snap.get(ppid)
        if parent is None:
            return False, f"chain broken at pid {ppid} (dead)"
        pc, cc = parent.get("created"), cur.get("created")
        if pc is not None and cc is not None and pc > cc + _RECYCLE_SLACK_MS:
            return False, f"chain broken at pid {ppid} (recycled: younger than child)"
        name = (parent.get("name") or "").lower()
        if any(h in name for h in HARNESS_NAME_HINTS):
            return True, f"parent chain found {parent.get('name')} pid {ppid}"
        cur = parent
    return True, "chain walk depth exhausted (fail-safe alive)"


def taskkill(pid: int) -> bool:
    try:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- the decision (pure)
def reap_decision(session_id: Optional[str], pid: Optional[int], pid_alive: bool,
                  pid_is_watcher: bool, marker_age_min: Optional[float], fresh_min: float,
                  chain_fn: Callable[[], Tuple[bool, str]],
                  my_session: Optional[str] = None, tombstoned: bool = False) -> Tuple[str, str]:
    """(action, reason) for one seat: 'skip' | 'clean' (remove file, no kill) | 'kill'.
    Pure given its inputs; chain_fn is called ONLY on the stale-marker slow path (K7)
    and any exception it raises means alive (K8). `tombstoned` (T086 S1) outranks marker
    freshness AND chain immunity: the session is ended BY RECORD -- K7's parent chain
    proves the shared claude.exe host lives, not the session (ca9a86ad receipt 2026-07-16)."""
    if pid is None:
        return "clean", "unreadable seat file"
    if not pid_alive:
        return "clean", f"stale seat: pid {pid} dead"
    if not pid_is_watcher:
        return "clean", f"stale seat: pid {pid} recycled to a non-watcher"
    if my_session and session_id == my_session:
        return "skip", "own session's seat"
    if session_id and tombstoned:
        return "kill", f"session-tombstoned: watcher pid {pid} outlived its ended session (T086 S1)"
    if session_id is None:
        return "kill", f"K6 migration: legacy name-keyed ghost watcher pid {pid}"
    if marker_age_min is not None and marker_age_min < fresh_min:
        return "skip", f"alive: marker {marker_age_min:.0f}m fresh (< {fresh_min:.0f}m)"
    age = "missing" if marker_age_min is None else f"{marker_age_min:.0f}m stale"
    try:
        alive, evidence = chain_fn()
    except Exception as e:
        return "skip", f"marker {age}; chain check unavailable ({type(e).__name__}) -- assuming alive (K8)"
    if alive:
        return "skip", f"alive: marker {age}, {evidence} (K7 idle-session immunity)"
    return "kill", f"orphan: marker {age} + {evidence}"


def fresh_minutes() -> float:
    try:
        return float(os.getenv("AKASHIC_WAKE_MARKER_FRESH_MIN", "") or FRESH_MIN_DEFAULT)
    except Exception:
        return FRESH_MIN_DEFAULT


def janitor(agent: str, my_session: Optional[str] = None, tmp: Optional[str] = None,
            snapshot_fn: Callable[[], Optional[Dict[int, Dict]]] = process_snapshot,
            kill_fn: Callable[[int], bool] = taskkill,
            now: Optional[float] = None) -> List[Tuple[str, str, str]]:
    """The session-start pass: walk every seat for this agent, decide, act, log.
    The WMI snapshot is taken LAZILY -- the marker-fresh fast path never pays for it.
    Returns [(seat_path, action, reason)] for tests/telemetry. Never raises."""
    results: List[Tuple[str, str, str]] = []
    fresh = fresh_minutes()
    snap: Optional[Dict[int, Dict]] = None
    snap_taken = False
    for path, sid in iter_seats(agent, tmp):
        try:
            pid = read_pid(path)
            pid_alive = pid_is_watcher = False
            marker_age = activity_age_min(agent, sid, now=now, tmp=tmp) if sid else None
            need_process_look = pid is not None and not (
                sid and marker_age is not None and marker_age < fresh and sid != (my_session or ""))
            # A fresh marker alone cannot prove the PID is alive -- but it does not need
            # to: a fresh marker means the session lives, and a dead pid under a live
            # session heals at that session's own next stop (wake_armed sees it dead).
            if pid is not None and need_process_look:
                if not snap_taken:
                    snap, snap_taken = snapshot_fn(), True
                if snap is None:
                    results.append((path, "skip", "snapshot unavailable -- assuming alive (K8)"))
                    append_provenance(agent, f"skip seat {os.path.basename(path)}: snapshot unavailable (K8)", tmp)
                    continue
                pid_alive = pid in snap
                pid_is_watcher = is_watcher(pid, snap)
            elif pid is not None:
                pid_alive = pid_is_watcher = True     # fresh-marker fast path: no WMI (K7 pin 2)
            action, reason = reap_decision(
                sid, pid, pid_alive, pid_is_watcher, marker_age, fresh,
                (lambda p=pid: chain_alive(p, snap or {})), my_session,
                tombstoned=(is_tombstoned(sid, tmp) if sid else False))
            if action == "kill":
                kill_fn(pid)
            if action in ("kill", "clean"):
                try:
                    os.remove(path)
                except Exception:
                    pass
            results.append((path, action, reason))
            append_provenance(agent, f"{action} seat {os.path.basename(path)}: {reason}", tmp)
        except Exception as e:
            results.append((path, "skip", f"error {type(e).__name__} -- assuming alive (K8)"))
            append_provenance(agent, f"skip seat {os.path.basename(path)}: error {type(e).__name__} (K8)", tmp)
    return results
