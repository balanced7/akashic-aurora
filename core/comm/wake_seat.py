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
Fenced design + reconciliation: docs/library/design/20260701_wave-2-design-claude-fenced-wake-seat-ow_7c4aaf.md.
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
    agent_parts = agent.split("_")
    try:
        for name in os.listdir(base):
            if not (name.startswith("bifrost_wake_") and name.endswith(".pid")):
                continue
            # W153 K4 (fence, deepseek A3): EXACT-component boundary, not prefix.
            # A raw prefix made agent "codex" enumerate codex_root's seats and
            # parse "root_<sid>" as a session id -- one agent's janitor reaping
            # another's watchers. Underscore agent ids still own their own seats.
            parts = name[len("bifrost_wake_"):-4].split("_")
            if len(parts) == len(agent_parts) + 1 and parts[:-1] == agent_parts:
                out.append((os.path.join(base, name), parts[-1]))
    except Exception:
        pass
    return out


def read_pid(path: str) -> Optional[int]:
    try:
        return int(open(path).read().strip())
    except Exception:
        return None


def _pid_alive_tristate(pid: int) -> Optional[bool]:
    """True / False / None(cannot tell) -- the ask_bg probe semantics, NOT the reaper's.

    K8's "fail toward alive" above governs DESTRUCTIVE decisions (a false-dead re-opens
    the kill loop). A RENDER consumer needs the opposite discipline: a probe error must
    surface as cannot-tell, because a boot line that says "wakeable" on a tasklist
    timeout is the exact over-claim W149 exists to end (fence dissent, 2026-08-13:
    deepseek's half reused the stop hook's fail-open probe and would have rendered
    wakeable on probe failure, violating its own A4)."""
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                             capture_output=True, text=True, timeout=6,
                             stdin=subprocess.DEVNULL)
        if out.returncode != 0:
            return None                    # the probe failed: cannot tell
        return str(pid) in (out.stdout or "")
    except Exception:
        return None                        # timeout/probe failure: cannot tell


def watcher_state(agent: str, session_id: Optional[str] = None,
                  tmp: Optional[str] = None,
                  pid_probe=None) -> Tuple[str, Optional[int]]:
    """PURE read of THIS session's watcher seat: (state, pid). Writes nothing, spawns
    nothing, consumes nothing -- the W149 boot line's only probe primitive.

    States (the fence's D1 distinction -- the remedies differ, so the states must):
      'armed'      seat file present, pid alive       -> armed is NOT proof of reachable
      'dead-seat'  seat file present, pid dead        -> the 08-12 failure; stale-seat re-arm
      'unarmed'    no seat file                       -> first arm
      'unknown'    unreadable pid, or probe cannot tell -> claim NEITHER direction (A4)
    """
    try:
        path = seat_path(agent, session_id, tmp)
        if not os.path.exists(path):
            return "unarmed", None
        pid = read_pid(path)
        if pid is None:
            return "unknown", None
        alive = (pid_probe or _pid_alive_tristate)(pid)
        if alive is True:
            return "armed", pid
        if alive is False:
            return "dead-seat", pid
        return "unknown", pid
    except Exception:
        return "unknown", None


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


def _tombstone_key(session_id: str, namespace: Optional[str] = None) -> str:
    return f"{namespace or os.environ.get('BIFROST_NAMESPACE', 'bifrost')}:session:ended:{session_id}"


def write_tombstone(session_id: str, tmp: Optional[str] = None, c=None,
                    namespace: Optional[str] = None) -> bool:
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
            cli.set(_tombstone_key(session_id, namespace), str(time.time()),
                    ex=7 * 24 * 3600)
            ok = True
    except Exception:
        pass
    return ok


def clear_tombstone(session_id: str, tmp: Optional[str] = None, c=None,
                    namespace: Optional[str] = None) -> bool:
    """T086 S1b: the resurrection edge. SessionEnd writes a tombstone; a later SessionStart
    for the SAME session id clears it -- the harness owns BOTH edges, so restart/compact
    cycles that end-and-continue one session heal themselves (live receipt 2026-07-19: a
    live seat was blocked from re-arming by its own cycle's tombstone). A true zombie never
    sees a SessionStart, so S1's dead-by-record protection stands. Both legs best-effort;
    True if a record existed to clear."""
    if not session_id:
        return False
    existed = False
    try:
        p = tombstone_path(session_id, tmp)
        if os.path.exists(p):
            os.remove(p)
            existed = True
    except Exception:
        pass
    try:
        cli = c
        if cli is None:
            from core.comm.bus import get_bus
            cli = get_bus("control")._client
        if cli is not None:
            if cli.delete(_tombstone_key(session_id, namespace)):
                existed = True
    except Exception:
        pass
    return existed


def is_tombstoned(session_id: str, tmp: Optional[str] = None, c=None,
                  namespace: Optional[str] = None) -> bool:
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
            return bool(cli.exists(_tombstone_key(session_id, namespace)))
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
            # W153 K5': ROTATE, never discard -- both fence halves independently
            # chose rotation so "auditable from the log alone" stays true across
            # the current + previous window instead of being false by construction.
            try:
                os.replace(path, path + ".1")
            except Exception:
                pass
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


def agent_watcher(pid: int, snap: Dict[int, Dict], agent: str) -> bool:
    """The KILL-warRANT identity (W153 K1', fence-amended): our KIND and our AGENT.

    deepseek's dissent: name-match alone is not a kill warrant -- a recycled pid
    can be ANOTHER agent's watcher or an unrelated bifrost_wake_report.py, and
    killing on substring reopens the loop the Wave-2 fence dissolved. The agent
    token is word-bounded because --agent codex is a substring of
    --agent codex_root (the K4 collision, one level down). is_watcher above stays
    the lenient kind-only check for non-lethal consumers."""
    cmd = (snap.get(pid, {}) or {}).get("cmdline") or ""
    if "bifrost_wake" not in cmd:
        return False
    return bool(re.search(rf"--agent\s+{re.escape(agent)}(?!\S)", cmd))


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
    """True ONLY on returncode 0 (W153 K3). Access-denied and races exit nonzero:
    claiming those as kills let the janitor remove the seat file of a LIVE
    watcher, leaving it running but invisible -- the caller keeps the seat on
    False so the next pass retries with evidence intact."""
    try:
        r = subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True, timeout=5)
        return r.returncode == 0
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
    # W153 tri-state identity: None = UNVERIFIED (fast path never examined it --
    # do not judge), False = verified-not-ours (clean). The reconciliation's own
    # catch: an honest-but-binary False here would have cleaned every healthy
    # fresh seat in the fleet one line before the freshness check.
    if pid_is_watcher is False:
        return "clean", f"stale seat: pid {pid} recycled to a non-watcher"
    if my_session and session_id == my_session:
        return "skip", "own session's seat"
    if session_id and tombstoned:
        if pid_is_watcher is True:
            return "kill", f"session-tombstoned: watcher pid {pid} outlived its ended session (T086 S1)"
        return "skip", f"tombstoned sid: identity unverified for pid {pid} -- assuming alive (K8/W153)"
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
            if pid is None:
                # W153 K6': a NONEMPTY unparseable seat younger than the fresh
                # gate may be a torn write in flight -- fail toward alive. The
                # same garbage past the gate is just garbage; fall through and
                # reap_decision cleans it (the janitor never goes hoarder).
                try:
                    raw = open(path, encoding="utf-8", errors="replace").read().strip()
                    age_min = ((now if now is not None else time.time())
                               - os.path.getmtime(path)) / 60.0
                except Exception:
                    raw, age_min = "", None
                if raw and age_min is not None and age_min < fresh:
                    results.append((path, "skip",
                                    "seat unreadable but YOUNG -- possible torn write, assuming alive (K8/W153)"))
                    append_provenance(agent, f"skip seat {os.path.basename(path)}: unreadable young (K8/W153)", tmp)
                    continue
            tomb = bool(sid and is_tombstoned(sid, tmp))
            pid_alive = False
            pid_is_watcher: Optional[bool] = None      # tri-state (W153): None = unverified
            marker_age = activity_age_min(agent, sid, now=now, tmp=tmp) if sid else None
            fresh_fast = bool(sid and marker_age is not None and marker_age < fresh
                              and sid != (my_session or ""))
            # A fresh marker alone cannot prove the PID is alive -- but it does not need
            # to: a fresh marker means the session lives, and a dead pid under a live
            # session heals at that session's own next stop (wake_armed sees it dead).
            # W153 (fence, deepseek A1): a TOMBSTONED sid always takes the process
            # look -- the fast path may skip the WMI cost only where no kill can be
            # in play, and it never synthesizes identity.
            need_process_look = pid is not None and (tomb or not fresh_fast)
            if pid is not None and need_process_look:
                if not snap_taken:
                    snap, snap_taken = snapshot_fn(), True
                if snap is None:
                    results.append((path, "skip", "snapshot unavailable -- assuming alive (K8)"))
                    append_provenance(agent, f"skip seat {os.path.basename(path)}: snapshot unavailable (K8)", tmp)
                    continue
                pid_alive = pid in snap
                pid_is_watcher = agent_watcher(pid, snap, agent)   # kill-warrant form (K1')
            elif pid is not None:
                pid_alive = True                       # the session lives (fresh marker)
                pid_is_watcher = None                  # identity NEVER synthesized (W153)
            action, reason = reap_decision(
                sid, pid, pid_alive, pid_is_watcher, marker_age, fresh,
                (lambda p=pid: chain_alive(p, snap or {})), my_session,
                tombstoned=tomb)
            if action == "kill":
                # W153 choke-point backstop (claude half): whatever decision path
                # produced "kill" -- present or future -- no pid dies unidentified.
                if pid_is_watcher is not True:
                    results.append((path, "skip", "kill WITHHELD: identity unverified (W153 K1')"))
                    append_provenance(agent, f"skip seat {os.path.basename(path)}: kill withheld, identity unverified (W153)", tmp)
                    continue
                if not kill_fn(pid):
                    results.append((path, "skip", "kill FAILED (taskkill rc!=0) -- seat kept for retry (K3/W153)"))
                    append_provenance(agent, f"skip seat {os.path.basename(path)}: kill FAILED, seat kept (K3/W153)", tmp)
                    continue
            if action in ("kill", "clean"):
                try:
                    os.remove(path)
                except Exception:
                    pass
                # W42: sweep the reaped session's SIDECARS too -- the gamma-a wake-dedup
                # .seen (else it litters tempdir until reboot, the fence's "acceptable
                # litter, file a WISH") and the .alive activity marker. Best-effort;
                # session-scoped naming mirrors seat_path. A SKIP reaps nothing (fail-open).
                if sid:
                    for extra in (os.path.join(os.path.dirname(path),
                                               f"bifrost_wake_{agent}_{sid}.seen"),
                                  activity_marker_path(agent, sid, tmp)):
                        try:
                            os.remove(extra)
                        except OSError:
                            pass
            results.append((path, action, reason))
            append_provenance(agent, f"{action} seat {os.path.basename(path)}: {reason}", tmp)
        except Exception as e:
            results.append((path, "skip", f"error {type(e).__name__} -- assuming alive (K8)"))
            append_provenance(agent, f"skip seat {os.path.basename(path)}: error {type(e).__name__} (K8)", tmp)
    return results
