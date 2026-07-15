"""daemon_state -- the autopilot's shared surface (slice A1, T075 gamma-scope).

Spec: research/reviewed/presence-autopilot-reconciliation-2026-07-15.md.
Daniel directive verbatim: note `presence-autopilot-directive`.

Three consumers, one tiny module:
- the STOP HOOK asks stop_hook_wake_verdict(): a LIVE daemon means the hook never
  blocks a turn-end again (the ~15-arms/6-blocks day this retires is 2026-07-15);
  it leaves a `.rearm` trigger when the session's listener seat is absent, and
  when the daemon is DOWN it returns the legacy verdict plus a ONCE-latched nag
  ("start the daemon") -- a nudge, never spam, never a block by itself.
- the DAEMON polls consume_rearms() each tick (spawn per trigger; a failed spawn
  leaves the trigger for the next tick -- crash-safe), and runs
  sweep_stale_markers() at boot + hourly under ruling R1: a marker dies ONLY
  seatless AND >24h old -- a stale-marker-WITH-seat is an idle-but-alive session
  (K7 immunity; the same-day 46m-idle live session is the pinned evidence).
- the CARD renders build_runtimes(): live / down / blocked per managed child --
  runner-down becomes a <=8s heartbeat fact instead of a 6h silence.

Fail-open everywhere: this module makes ergonomics, never wedges. Kill switch
for the hook path: AKASHIC_DAEMON_WAKE=0 (checked by the caller, ruling 4).
"""
from __future__ import annotations

import os
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional

MARKER_MAX_AGE_S = 24 * 3600         # ruling R1: age gate
REARM_SUFFIX = ".rearm"


def _ns(ns: Optional[str] = None) -> str:
    return ns or os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _client(c=None):
    if c is not None:
        return c
    try:
        from core.comm.bus import get_bus
        return get_bus("control")._client
    except Exception:
        return None


def daemon_is_live(agent: str, c=None, ns: Optional[str] = None) -> bool:
    """One Redis EXISTS on <ns>:daemon:<agent>. False on any doubt (fail toward
    the legacy path -- the fast path is an optimization, never a right)."""
    cli = _client(c)
    if cli is None:
        return False
    try:
        return bool(cli.exists(f"{_ns(ns)}:daemon:{agent}"))
    except Exception:
        return False


# ---------------------------------------------------------------- rearm triggers
def rearm_path(agent: str, session_id: str, tmp: Optional[str] = None) -> str:
    base = tmp or tempfile.gettempdir()
    return os.path.join(base, f"bifrost_wake_{agent}_{session_id}{REARM_SUFFIX}")


def write_rearm_trigger(agent: str, session_id: str, tmp: Optional[str] = None) -> bool:
    try:
        with open(rearm_path(agent, session_id, tmp), "w", encoding="utf-8") as f:
            f.write(str(time.time()))
        return True
    except Exception:
        return False


def consume_rearms(agent: str, spawn_fn: Callable[[str], bool],
                   tmp: Optional[str] = None) -> int:
    """Daemon-side: for each of OWN agent's .rearm triggers, call spawn_fn(sid);
    truthy result clears the trigger, falsy/raising leaves it for the next tick.
    Returns the number of successful consumes."""
    base = tmp or tempfile.gettempdir()
    prefix = f"bifrost_wake_{agent}_"
    done = 0
    try:
        names = os.listdir(base)
    except Exception:
        return 0
    for name in names:
        if not (name.startswith(prefix) and name.endswith(REARM_SUFFIX)):
            continue
        sid = name[len(prefix):-len(REARM_SUFFIX)]
        try:
            ok = bool(spawn_fn(sid))
        except Exception:
            ok = False
        if ok:
            try:
                os.remove(os.path.join(base, name))
                done += 1
            except Exception:
                pass
    return done


# ---------------------------------------------------------------- marker janitor (R1)
def sweep_stale_markers(agent: str, tmp: Optional[str] = None,
                        now: Optional[float] = None,
                        max_age_s: int = MARKER_MAX_AGE_S) -> int:
    """Remove OWN agent's .alive markers that are BOTH seatless and older than
    the age gate. Never touches a marker whose sid still holds a .pid seat
    (idle-but-alive sessions keep their sibling visibility -- ruling R1)."""
    from core.comm import wake_seat
    base = tmp or tempfile.gettempdir()
    prefix = f"bifrost_wake_{agent}_"
    now_f = float(now if now is not None else time.time())
    removed = 0
    try:
        names = os.listdir(base)
    except Exception:
        return 0
    for name in names:
        if not (name.startswith(prefix) and name.endswith(".alive")):
            continue
        sid = name[len(prefix):-len(".alive")]
        path = os.path.join(base, name)
        try:
            if os.path.exists(wake_seat.seat_path(agent, sid, base)):
                continue                      # seated = alive somewhere; keep
            if (now_f - os.path.getmtime(path)) <= max_age_s:
                continue                      # young enough to matter; keep
            os.remove(path)
            removed += 1
        except Exception:
            continue
    return removed


# ---------------------------------------------------------------- stop-hook verdict
def _nag_latch_path(agent: str, session_id: str, tmp: Optional[str] = None) -> str:
    base = tmp or tempfile.gettempdir()
    return os.path.join(base, f"bifrost_wake_{agent}_{session_id}.daemon_nag")


def stop_hook_wake_verdict(agent: str, session_id: str, c=None,
                           ns: Optional[str] = None,
                           tmp: Optional[str] = None) -> Dict[str, Any]:
    """The A1 predicate the stop hook consults BEFORE its legacy wake logic.

    {"pass": True, "line": ...}         daemon live -> never block; a missing
                                        listener seat leaves a .rearm trigger.
    {"pass": False, "nag": bool, ...}   daemon down -> legacy path decides;
                                        nag is True exactly once per session."""
    from core.comm import wake_seat
    if daemon_is_live(agent, c=c, ns=ns):
        seated = os.path.exists(wake_seat.seat_path(agent, session_id, tmp))
        if not seated:
            write_rearm_trigger(agent, session_id, tmp)
        return {"pass": True,
                "line": (f"[stop-hook] daemon owns wakeability for {agent} "
                         f"({'listener seated' if seated else 'rearm trigger left'}) -- pass")}
    latch = _nag_latch_path(agent, session_id, tmp)
    nag = not os.path.exists(latch)
    if nag:
        try:
            with open(latch, "w", encoding="utf-8") as f:
                f.write(str(time.time()))
        except Exception:
            nag = False
    return {"pass": False, "nag": nag,
            "line": ("[stop-hook] daemon not running -- start it once: "
                     f"py scripts/bifrost_daemon.py --agent {agent} (retires the arm chore)")
            if nag else ""}


# ---------------------------------------------------------------- card runtimes (P5)
def build_runtimes(children: Dict[str, Any]) -> Dict[str, str]:
    """{'runner': 'live'|'down'|'blocked', ...} from ManagedChild-shaped objects
    (alive/tripped attributes). 'blocked' = circuit breaker tripped -- a louder
    fact than 'down' (restarting has STOPPED; a human owns the next move)."""
    out: Dict[str, str] = {}
    for name, ch in (children or {}).items():
        try:
            if getattr(ch, "tripped", False):
                out[name] = "blocked"
            elif getattr(ch, "alive", False):
                out[name] = "live"
            else:
                out[name] = "down"
        except Exception:
            out[name] = "down"
    return out
