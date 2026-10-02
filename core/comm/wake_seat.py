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
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # windowless: never flash a console (2026-09-05, cmd-spam fix)
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


# ---------------------------------------------------------------- listener ORIGIN (2026-10-01)
# WHY THIS EXISTS. Two listeners can hold one seat file and look identical to every reader:
# one launched by a harness-tracked parent (bifrost-standby as a run_in_background task, or
# bifrost_wake.py launched the same way) whose EXIT STARTS A TURN, and one spawned by
# bifrost_daemon --manage-listener, which holds the seat, consumes mail, and can wake
# NOBODY -- a detached process notifies no harness. The stop hook read "seat pid alive" as
# "wakeable" and passed, so an interactive session went deaf while every surface said armed
# (lesson detached_daemon_listener_holds_the_seat_but_cannot_wake_an_interactive_session;
# Daniel 2026-10-01: "How do we take the discipline out of it and have an ergonomic solution
# that just works."). The origin is stamped by the LAUNCHER through BIFROST_WAKE_ORIGIN and
# written by the listener beside its seat; a seat with no origin record, or an UNSTAMPED
# launch, is UNKNOWN, and unknown is not wakeable -- a false block costs one re-arm, a
# false pass costs deafness (Heimdall D6c: a silent default must never be a wakeable one).
ORIGIN_HARNESS = "harness"   # harness-tracked parent: its exit re-invokes the session
ORIGIN_DAEMON = "daemon"     # bifrost_daemon child: presence + consume, never a wake
ORIGIN_DIRECT = "direct"     # EXPLICIT stamp only: a launcher asserting a harness parent (D6c)
ORIGIN_ENV = "BIFROST_WAKE_ORIGIN"
WAKEABLE_ORIGINS = frozenset({ORIGIN_HARNESS, ORIGIN_DIRECT})


def origin_path(agent: str, session_id: Optional[str] = None, tmp: Optional[str] = None) -> str:
    """Sidecar beside the seat: the seat keeps its bare-int contract for every reader."""
    base = tmp or tempfile.gettempdir()
    if session_id:
        return os.path.join(base, f"bifrost_wake_{agent}_{session_id}.origin")
    return os.path.join(base, f"bifrost_wake_{agent}.origin")


def write_origin(agent: str, session_id: Optional[str], origin: str, pid: int,
                 tmp: Optional[str] = None) -> bool:
    """Record `<origin>:<pid>`; best-effort, never raises (a stamp must not stop the arm)."""
    try:
        with open(origin_path(agent, session_id, tmp), "w", encoding="utf-8") as f:
            f.write(f"{(origin or ORIGIN_DIRECT).strip()}:{int(pid)}")
        return True
    except Exception:
        return False


def remove_origin(agent: str, session_id: Optional[str], pid: Optional[int] = None,
                  tmp: Optional[str] = None) -> None:
    """Remove the sidecar -- only if it still names `pid` when one is given (newest-wins:
    a successor's stamp is never deleted by a retiring predecessor)."""
    try:
        p = origin_path(agent, session_id, tmp)
        if pid is not None:
            _, opid = read_origin(agent, session_id, tmp)
            if opid is not None and opid != int(pid):
                return
        os.remove(p)
    except Exception:
        pass


def read_origin(agent: str, session_id: Optional[str] = None,
                tmp: Optional[str] = None) -> Tuple[str, Optional[int]]:
    """(origin, pid) from the sidecar; ('none', None) when absent or unreadable."""
    try:
        raw = open(origin_path(agent, session_id, tmp), encoding="utf-8").read().strip()
    except Exception:
        return "none", None
    if not raw:
        return "none", None
    origin, _, pid_s = raw.partition(":")
    try:
        pid = int(pid_s) if pid_s else None
    except Exception:
        pid = None
    return (origin.strip() or "none"), pid


def wake_origin_state(agent: str, session_id: Optional[str] = None,
                      tmp: Optional[str] = None, pid_probe=None) -> Tuple[str, Optional[int]]:
    """PURE: the seat's watcher_state refined by WHO launched the seated listener.

      'armed-harness' / 'armed-direct'   seat alive, launched by a harness-tracked parent
      'armed-daemon'                     seat alive, daemon child -- presence, NOT wake
      'armed-unknown'                    seat alive, no origin record or a stale one
      'none' / 'dead-seat' / 'unknown'   exactly watcher_state's own verdicts
    """
    state, pid = watcher_state(agent, session_id, tmp, pid_probe)
    if state != "armed":
        return state, pid
    origin, opid = read_origin(agent, session_id, tmp)
    if origin == "none" or (opid is not None and pid is not None and opid != pid):
        return "armed-unknown", pid
    if origin in (ORIGIN_HARNESS, ORIGIN_DAEMON, ORIGIN_DIRECT):
        return f"armed-{origin}", pid
    return "armed-unknown", pid


def arm_command(agent: str, session_id: Optional[str] = None, *, repo: Optional[str] = None) -> str:
    """THE one arm command. Every surface that tells a seat how to arm must call this.

    WHY THIS EXISTS (2026-10-02). Two surfaces used to build their own, and they disagreed in a
    way that broke the thing they were both trying to fix:

        boot, agent/harness/context.py
            py scripts/bifrost_wake.py --agent <a> --min-tier 0
        the stop hook, agent/harness/hooks/claude_stop.py
            BIFROST_CONSUME_LANE=work BIFROST_WAKE_LANE=work py agent_cli.py bifrost-standby <a>
                --session <sid>

    `scripts/bifrost_wake.py` stamps its origin from BIFROST_WAKE_ORIGIN and DEFAULTS TO
    "unknown"; `bifrost-standby` sets it to "harness"; and WAKEABLE_ORIGINS does not contain
    "unknown", so `harness_armed()` is False for a listener armed the first way. A seat that
    obeyed BOOT therefore armed a watcher the STOP HOOK refused, and was blocked with "holds the
    seat with no origin record". The house recorded that recurring three or more times and read it
    as a seat forgetting its ritual. The ritual was fine; the instruction was wrong.

    So this function is deliberately shaped so it CANNOT emit the broken form: it always routes
    through `bifrost-standby`, which is the launcher that stamps a wakeable origin, and it always
    carries the lane env and the session.

    IT IS A STRING, NOT A SPAWN, and that is not an oversight. `scripts/bifrost_wake.py` delivers
    by PRINTING to stdout and exiting, so a wake only lands if something is reading that stream. A
    watcher spawned detached from inside a hook or a CLI prints into a void while `any_armed()`
    cheerfully answers "armed" -- a surface asserting reachability it does not have, which is
    strictly worse than reporting none. The arm has to be launched on a channel the harness is
    watching, which means the SEAT must run it. Every caller here hands the string over; nobody
    runs it for the seat.
    """
    root = repo or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cli = os.path.join(root, "agent_cli.py").replace("\\", "/")
    sess = f" --session {session_id}" if session_id else ""
    return (f"BIFROST_CONSUME_LANE=work BIFROST_WAKE_LANE=work py {cli} "
            f"bifrost-standby {agent}{sess}")


def harness_armed(agent: str, session_id: Optional[str] = None,
                  tmp: Optional[str] = None, pid_probe=None) -> bool:
    """True only for a seat whose listener can START A TURN when it exits."""
    state, _ = wake_origin_state(agent, session_id, tmp, pid_probe)
    return state in {f"armed-{o}" for o in WAKEABLE_ORIGINS}


# ---------------------------------------------------------------- wake RECEIPTS (S3, 2026-10-01)
# Every wake is a full model turn. Before S3 nothing recorded how many there were or whether
# they carried mail, so "a chatty sender burns plan" was a feeling. One JSON line per listener
# exit -- woke / quiet / cycled, the tiers that fired, what the floor held back -- lets the
# standby print the day's count on every arm and lets doctor page on a seat that wakes for
# nothing. Lives under state/ (git-ignored) beside the other machine-local ledgers.
def wake_receipts_path(agent: str, base: Optional[str] = None) -> str:
    root = base or os.environ.get("AKASHIC_WAKE_RECEIPTS_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "state", "wake-receipts")
    return os.path.join(root, f"{agent}.jsonl")


def append_wake_receipt(agent: str, receipt: Dict, base: Optional[str] = None) -> bool:
    """Append one receipt; best-effort, never raises (a receipt must never cost the wake).
    Under pytest the MACHINE ledger is never written unless the test names a directory
    (base or AKASHIC_WAKE_RECEIPTS_DIR): the listener pins drive watch() on a fake clock, and
    their receipts would otherwise land in state/wake-receipts/ with 1970 timestamps."""
    try:
        import json
        if (os.environ.get("PYTEST_CURRENT_TEST") and not base
                and not os.environ.get("AKASHIC_WAKE_RECEIPTS_DIR")):
            return False
        p = wake_receipts_path(agent, base)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        rec = dict(receipt)
        rec.setdefault("ts", time.time())
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=True) + "\n")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- wake OBSERVABILITY (S5, 2026-10-01)
# Daniel's ladder property (5): doctor shows per seat who launched the listener, since when, and
# what the wakes cost; and PAGES when a session that is demonstrably alive has had no listener
# that can start a turn. A heartbeat proves presence and cannot prove absence (the standing
# lesson): the EXPECTATION here is the session's own activity marker, touched at every hook
# firing -- a seat alive within the hour that is not reachable from idle is a finding, not a gap.
WAKE_PAGE_AFTER_MIN = 10.0      # unarmed this long with the session alive -> page
WAKE_STALE_AFTER_MIN = 60.0     # alive marker older than this -> the session is gone, janitor's job


def agents_with_seats(tmp: Optional[str] = None) -> List[str]:
    """Agents that have ANY seat file in the tempdir (exact-component split, as iter_seats)."""
    base = tmp or tempfile.gettempdir()
    found: List[str] = []
    try:
        for name in os.listdir(base):
            if name.startswith("bifrost_wake_") and name.endswith(".pid"):
                parts = name[len("bifrost_wake_"):-4].split("_")
                agent = "_".join(parts[:-1]) if len(parts) > 1 else parts[0]
                if agent and agent not in found:
                    found.append(agent)
    except Exception:
        pass
    return sorted(found)


def wake_tag(agent: str, session_id: Optional[str], tmp: Optional[str] = None) -> str:
    """One word for a roster row: armed-harness / armed-daemon / armed-unknown / dead-seat /
    unarmed (watcher_state's own vocabulary; 'unarmed' is a measured absence of a seat file,
    never a probe failure, which is 'unknown')."""
    try:
        state, _ = wake_origin_state(agent, session_id or None, tmp)
        return state
    except Exception:
        return "unknown"


def wake_observations(agent: str, tmp: Optional[str] = None, now: Optional[float] = None,
                      pid_probe=None) -> List[Dict]:
    """PURE read, one row per session seat of `agent`: state, origin, pid, armed_since (seat
    file mtime), alive_age_min (activity marker; None = no marker ever)."""
    t = now if now is not None else time.time()
    rows: List[Dict] = []
    for path, sid in iter_seats(agent, tmp):
        state, pid = wake_origin_state(agent, sid, tmp, pid_probe)
        origin, _ = read_origin(agent, sid, tmp)
        try:
            armed_since = os.path.getmtime(path)
        except Exception:
            armed_since = None
        alive = activity_age_min(agent, sid, now=t, tmp=tmp) if sid else None
        rows.append({"agent": agent, "session_id": sid or "", "state": state, "origin": origin,
                     "pid": pid, "armed_since": armed_since, "alive_age_min": alive})
    # sessions with an activity marker but NO seat file at all are the loudest case
    try:
        base = tmp or tempfile.gettempdir()
        seen = {r["session_id"] for r in rows}
        prefix = f"bifrost_wake_{agent}_"
        for name in os.listdir(base):
            if name.startswith(prefix) and name.endswith(".alive"):
                sid = name[len(prefix):-len(".alive")]
                if sid and sid not in seen and "_" not in sid:
                    rows.append({"agent": agent, "session_id": sid, "state": "unarmed", "origin": "none",
                                 "pid": None, "armed_since": None,
                                 "alive_age_min": activity_age_min(agent, sid, now=t, tmp=tmp)})
    except Exception:
        pass
    return rows


def wake_findings(agents: Optional[List[str]] = None, tmp: Optional[str] = None,
                  now: Optional[float] = None, receipts_base: Optional[str] = None,
                  pid_probe=None, arm_hint=None) -> List[Dict]:
    """Doctor-shaped findings ({agent, state, grade, line, drill}) for reachability from idle.

      page       a session alive within WAKE_STALE_AFTER_MIN, unarmed (no harness-parented
                 listener) for more than WAKE_PAGE_AFTER_MIN
      dashboard  reachable seats (origin + since + alive age); unarmed inside the grace
                 (a turn may be running); stale seats the janitor owns; the 24 h receipt counts
    arm_hint(agent, sid) -> the exact arm line for the drill (the caller knows its cwd)."""
    t = now if now is not None else time.time()
    out: List[Dict] = []
    for agent in (agents if agents is not None else agents_with_seats(tmp)):
        rows = wake_observations(agent, tmp, t, pid_probe)
        for r in rows:
            sid8 = (r["session_id"] or "legacy")[:8]
            alive = r["alive_age_min"]
            alive_txt = (f"alive {alive:.0f}m ago" if alive is not None else "no activity marker")
            reachable = r["state"] in {f"armed-{o}" for o in WAKEABLE_ORIGINS}
            drill = (arm_hint(agent, r["session_id"]) if (arm_hint and r["session_id"]) else
                     f"py agent_cli.py bifrost-standby {agent} --session {r['session_id']}")
            if reachable:
                since = (time.strftime("%H:%M", time.localtime(r["armed_since"]))
                         if r["armed_since"] else "?")
                out.append({"agent": agent, "state": "wake_reachable", "grade": "dashboard",
                            "line": f"{agent}#{sid8}: reachable from idle -- {r['state']} since {since}, {alive_txt}",
                            "drill": ""})
            elif alive is None:
                continue                                  # no evidence of a live session: not a finding
            elif alive <= WAKE_PAGE_AFTER_MIN:
                out.append({"agent": agent, "state": "wake_unarmed_grace", "grade": "dashboard",
                            "line": f"{agent}#{sid8}: unarmed ({r['state']}) but {alive_txt} -- inside the "
                                    f"{WAKE_PAGE_AFTER_MIN:.0f} min grace, a turn may be running",
                            "drill": drill})
            elif alive <= WAKE_STALE_AFTER_MIN:
                out.append({"agent": agent, "state": "wake_deaf", "grade": "page",
                            "line": f"{agent}#{sid8}: DEAF -- session {alive_txt} but NOT reachable from idle "
                                    f"({r['state']}: no harness-parented listener) for > "
                                    f"{WAKE_PAGE_AFTER_MIN:.0f} min; mail queues until someone arms it",
                            "drill": drill})
            else:
                out.append({"agent": agent, "state": "wake_seat_stale", "grade": "dashboard",
                            "line": f"{agent}#{sid8}: seat records stale ({r['state']}, {alive_txt}) -- "
                                    f"the session is gone; janitor",
                            "drill": ""})
        s = wake_receipts_summary(agent, since_s=24 * 3600, now=t, base=receipts_base)
        if s["wakes"] or rows:
            out.append({"agent": agent, "state": "wake_cost", "grade": "dashboard",
                        "line": f"{agent}: wakes 24h {s['wakes']} ({s['with_mail']} with mail, "
                                f"{s['quiet']} quiet, {s['cycled']} deadline cycles; "
                                f"{s['held_below_floor']} held below floor)",
                        "drill": ""})
    return out


def wake_receipts_summary(agent: str, since_s: float = 24 * 3600, now: Optional[float] = None,
                          base: Optional[str] = None) -> Dict[str, int]:
    """Counts over the window: wakes (listener exits), with_mail, quiet, cycled,
    held_below_floor (sum). Missing file -> zeros, which is a measured zero: the ledger
    exists from the first arm after S3, and absence before that is 'not yet recorded'."""
    out = {"wakes": 0, "with_mail": 0, "quiet": 0, "cycled": 0, "held_below_floor": 0}
    try:
        import json
        cutoff = (now if now is not None else time.time()) - float(since_s)
        with open(wake_receipts_path(agent, base), encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if float(r.get("ts") or 0) < cutoff:
                    continue
                out["wakes"] += 1
                o = r.get("outcome")
                if o == "woke":
                    out["with_mail"] += 1
                elif o == "cycled":
                    out["cycled"] += 1
                else:
                    out["quiet"] += 1
                out["held_below_floor"] += int(r.get("below_floor") or 0)
    except Exception:
        pass
    return out


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
                             stdin=subprocess.DEVNULL, creationflags=_NO_WINDOW)
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
            capture_output=True, text=True, timeout=timeout_s,
            creationflags=_NO_WINDOW).stdout
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


class CensusUnavailable(RuntimeError):
    """The process table could not be read. NOT a verdict of 'nothing is running'.

    process_snapshot() returns None on any failure (K8: fail toward alive). Callers that
    turned that None into an empty dict were converting "I could not look" into "there is
    nothing there" -- T176's law (a miss must not read as a decision) broken at a door.
    Raising forces the caller to say which it means.
    """


_PY_INTERPRETERS = {
    "python.exe", "pythonw.exe", "py.exe", "pyw.exe", "python3.exe",
    "python", "python3", "py",
}


def _argv_tokens(cmdline: str) -> List[str]:
    """Split a Windows command line into argv tokens, quotes stripped. Never raises."""
    import shlex

    try:
        toks = shlex.split(cmdline, posix=False)
    except ValueError:
        toks = cmdline.split()
    out = []
    for t in toks:
        t = t.strip()
        if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
            t = t[1:-1]
        if t:
            out.append(t)
    return out


def _path_basename(token: str) -> str:
    return re.split(r"[\\/]", token)[-1].lower()


def script_processes(
    snap: Optional[Dict[int, Dict]],
    script_name: str,
    exclude_pids: Optional[set] = None,
) -> List[int]:
    """PIDs of python processes actually RUNNING <script_name>, matched by launch SHAPE.

    THE RULE (sol, learn:experiment:gateway_status_probe_must_exclude_self_pid): require
    executable kind plus an exact argv-token shape, and exclude the observer. Never a
    substring test -- a shell that greps for the script, an editor with it open, and
    `py -c "...script_name..."` all MENTION it, and none of them are it.

    That distinction is not pedantry. On 2026-09-23 `gateway status` reported four live
    gateways, three of which were the investigating shells, while a real singleton guard
    was enforcing exactly one -- i.e. the census was least trustworthy precisely during
    the incident it exists for. The same defect counted a process-table string into four
    concurrent gateways on 2026-08-26 (tests/test_dc6200d491_gateway_singleton.py).

    Matching, in order:
      1. the snapshot must exist            -> CensusUnavailable, never a silent []
      2. the process is a python interpreter (by Name, else by argv[0])
      3. some argv TOKEN's basename == script_name  (token, not substring)
      4. the pid is not the observer, nor in exclude_pids

    Args:
        snap: a process_snapshot() result. None raises -- see CensusUnavailable.
        script_name: e.g. "bifrost_runner_discord.py". Matched on basename, case-insensitive.
        exclude_pids: additional pids to omit. The calling process is ALWAYS omitted.

    Returns:
        Sorted list of pids. An empty list is a measured absence, and only that.
    """
    if snap is None:
        raise CensusUnavailable(
            "process_snapshot() returned None -- the process table could not be read. "
            "This is not evidence that no process is running; say so to the operator "
            "rather than reporting an absence you did not measure."
        )

    wanted = _path_basename(script_name)
    omit = {os.getpid()} | set(exclude_pids or ())
    hits: List[int] = []

    for pid, rec in snap.items():
        if pid in omit:
            continue
        cmdline = (rec.get("cmdline") or "").strip()
        if not cmdline:
            continue
        tokens = _argv_tokens(cmdline)
        if not tokens:
            continue
        # (2) executable kind. Prefer the snapshot's Name; fall back to argv[0].
        name = _path_basename(rec.get("name") or "") or _path_basename(tokens[0])
        if name not in _PY_INTERPRETERS:
            continue
        # (3) the script must be an argv TOKEN, not a substring of one.
        if any(_path_basename(t) == wanted for t in tokens):
            hits.append(pid)

    # (5) COLLAPSE LAUNCHERS. `py script.py` is TWO processes -- py.exe and the
    # python.exe it spawns -- both carrying the same argv, so a shape census counts one
    # launch twice. sol found this first on the production branch and his comment states
    # it exactly: "py.exe is deliberately excluded: its child python.exe owns the
    # runtime, and counting both would turn one `py script.py` launch into two
    # gateways." Measured here 2026-09-23 against this very function: asked for
    # codex_bifrost_wake.py it returned [53976, 55332], and 55332's ppid IS 53976.
    #
    # This is the general form of his rule rather than his name list -- drop any hit that
    # is the PARENT of another hit -- so py.exe->python.exe, pyw.exe->pythonw.exe and any
    # future launcher collapse without enumerating them. The child owns the runtime, so
    # the child is the one kept. Two hits with no parent/child relationship remain TWO,
    # which is what the singleton guard exists to catch.
    hit_set = set(hits)
    hits = [p for p in hits
            if not any(snap[q].get("ppid") == p for q in hit_set if q != p)]

    return sorted(hits)


WATCHER_SCRIPTS = ("bifrost_wake.py", "codex_bifrost_wake.py")


def is_watcher(pid: int, snap: Dict[int, Dict]) -> bool:
    """Identity check: the pid is OUR kind of process (never judge a recycled pid).

    LENIENT means kind-only -- it does not ask WHICH agent (that is agent_watcher, the
    kill warrant). It has never meant "any process that says the word".

    Until 2026-09-23 the body was `"bifrost_wake" in cmdline`, which on the live host
    accepted TWELVE processes: two real watchers, six bash shells and four python
    one-liners, every one of the ten a shell that merely NAMED bifrost_wake while
    DIAGNOSING it. So the recycled-pid guard failed in precisely its own scenario --
    stale seat file, recycled pid, and whoever was debugging the wake system at that
    moment satisfied the identity check.

    Now matched by launch shape via script_processes: interpreter kind + an exact argv
    token. Same law and the same callable as the gateway census (ddf88661); this is its
    second door, and the corpus already held the rule
    (sol, learn:experiment:gateway_status_probe_must_exclude_self_pid).

    A pid absent from the snapshot, with an unreadable command line, or judged while the
    process table cannot be read, is UNPROVEN and therefore False -- for a lethal
    consumer, unproven must never read as convicted.
    """
    if pid not in (snap or {}):
        return False
    try:
        return any(pid in script_processes(snap, script, exclude_pids=set())
                   for script in WATCHER_SCRIPTS)
    except CensusUnavailable:
        return False


def agent_watcher(pid: int, snap: Dict[int, Dict], agent: str) -> bool:
    """The KILL-warRANT identity (W153 K1', fence-amended): our KIND and our AGENT.

    deepseek's dissent: name-match alone is not a kill warrant -- a recycled pid
    can be ANOTHER agent's watcher or an unrelated bifrost_wake_report.py, and
    killing on substring reopens the loop the Wave-2 fence dissolved. The agent
    token is word-bounded because --agent codex is a substring of
    --agent codex_root (the K4 collision, one level down). is_watcher above stays
    the lenient kind-only check for non-lethal consumers."""
    if not is_watcher(pid, snap):            # KIND, now by launch shape (2026-09-23)
        return False
    cmd = (snap.get(pid, {}) or {}).get("cmdline") or ""
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
                           capture_output=True, timeout=5, creationflags=_NO_WINDOW)
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


# --------------------------------------------------------------- reachability (2026-09-23)
#: Aggregate precedence across an agent's sessions. ARMED wins because ONE listening session
#: is enough to reach the agent -- a stale sibling seat must never mask a live one. UNKNOWN
#: outranks the two negatives because a probe that cannot tell must not manufacture a verdict.
_ARMED_PRECEDENCE = ("armed", "unknown", "dead-seat", "unarmed")


def any_armed(agent: str, tmp: Optional[str] = None, pid_probe=None) -> str:
    """Is ANY session of `agent` holding a live wake listener? One of the four
    `watcher_state` states, aggregated across every seat file the agent owns.

    'unarmed' here means something precise and load-bearing: not one seat file exists, so
    nothing is listening and we KNOW it. That is a determination, not an absence of one --
    which is exactly the distinction the rest of this house keeps having to relearn.
    """
    seats = iter_seats(agent, tmp)
    if not seats:
        return "unarmed"
    states = {watcher_state(agent, sid, tmp, pid_probe)[0] for _path, sid in seats}
    for state in _ARMED_PRECEDENCE:
        if state in states:
            return state
    return "unknown"


def armed_sessions(agent: str, tmp: Optional[str] = None, pid_probe=None) -> List[Optional[str]]:
    """Session ids whose watcher is ARMED right now (None = a legacy per-agent seat)."""
    out: List[Optional[str]] = []
    for _path, sid in iter_seats(agent, tmp):
        if watcher_state(agent, sid, tmp, pid_probe)[0] == "armed":
            out.append(sid)
    return out


def reachable(agent: str, *, presence_live: bool, tmp: Optional[str] = None,
              pid_probe=None, live_sessions=None) -> bool:
    """Will a durable send to `agent` actually be READ, without anyone intervening?

    PRESENCE IS NOT REACHABILITY, and conflating them cost the operator four messages --
    two of them for five days -- between 2026-09-17 and 2026-09-23. His mail was delivered
    perfectly, to a seat that was LIVE and beating, with no wake listener armed. Discord's
    `_auto_wake` reads "live" as "the lane plus its armed listener ARE the wake" and so said
    nothing; the notice that would have told him nobody was home was never posted. He got
    silence, which is indistinguishable from being ignored.

    A LIVE SEAT WITH NO ARMED LISTENER IS A LIT ROOM WITH NOBODY IN IT.

    Both halves are necessary. An armed watcher on a seat with no presence is a listener for
    a session that is gone; presence with nothing armed is the incident above.

    FAIL-OPEN IS DELIBERATELY NARROW. It applies ONLY to 'unknown' -- a probe that genuinely
    cannot tell -- because `watcher_state`'s own law is to claim neither direction there. It
    does NOT apply to 'unarmed' or 'dead-seat', which are real determinations. The predicate
    this replaces failed open on everything, justified by the cost of spawning a duplicate
    paid seat; the 2026-09-04 ruling removed spawning, so that cost is gone while the cost of
    a false 'reachable' turned out to be five days of unread operator mail.
    """
    if not presence_live:
        return False
    state = any_armed(agent, tmp, pid_probe)
    if state not in ("armed", "unknown"):
        return False
    if live_sessions is None or state == "unknown":
        return True                       # prior contract / probe cannot tell -> assert nothing

    # THE SESSION MUST STILL EXIST (2026-09-23, found by the previous fix verifying itself
    # wrong). The wake mechanism is PROCESS EXIT RE-INVOKING THE OWNING SESSION, so a watcher
    # whose session is no longer a live conversation exits into nothing. It is armed, it is a
    # real process, and it wakes no one. Because any_armed aggregates over every session of an
    # agent, one stray drill watcher (pid 58216, session 'pin-ephemeral-0000') made a wholly
    # unreachable agent read as reachable -- the very failure this predicate exists to end,
    # one layer down. A legacy seat (sid None) predates per-session seats and cannot be
    # matched either way, so it keeps the benefit of the doubt rather than inventing a verdict.
    live = {str(s) for s in live_sessions}
    return any(sid is None or str(sid) in live
               for sid in armed_sessions(agent, tmp, pid_probe))
