"""daemon_state -- the autopilot's shared surface (slice A1, T075 gamma-scope).

Spec: docs/library/report/20260715_presence-autopilot-reconciliation-claude_b5cb93.md.
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
import sys
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
        except Exception as e:
            # T167: fail-open is RIGHT (a bad spawn must not kill the daemon loop) but SILENT
            # fail-open turned a one-line arity typo into a permanent invisible no-op. The daemon
            # called _spawn_listener(sid, bus.ns) against a one-argument def, every rearm raised
            # TypeError, this line ate it, and the wake autopilot spawned nothing for weeks while
            # reporting nothing. Repair is not "catch less" -- it is "say something when you catch".
            ok = False
            try:
                # T170: the reason is BUILT, not hand-written. BoundaryOutcome.caught() is the
                # fail-open-without-silence shape, and this is its first production consumer --
                # deliberately the exact boundary where the silence cost us the wake autopilot.
                from core.outcome import BoundaryOutcome
                print(f"[rearm] {BoundaryOutcome.caught(e, where=f'spawn({agent})', ref=sid).line()}"
                      f" -- trigger left for the next tick", file=sys.stderr, flush=True)
            except Exception:
                pass
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


def rearm_trigger_path(agent: str, session_id: str = "", tmp: Optional[str] = None) -> str:
    """Mirror of bifrost_wake.rearm_trigger_path -- one shape, two readers (T380: never
    compute one shared derived key twice from different inputs)."""
    base = tmp or tempfile.gettempdir()
    name = (f"bifrost_wake_{agent}_{session_id}.rearm" if session_id
            else f"bifrost_wake_{agent}.rearm")
    return os.path.join(base, name)


# ------------------------------------------------- restart re-arm (2026-09-06 incident)
def rearm_orphaned_sessions(agent: str, tmp: Optional[str] = None) -> int:
    """At daemon STARTUP, re-arm the listeners this daemon's own restart orphaned.

    THE INCIDENT (live, unattended, 2026-09-06 ~03:52). The claude autopilot daemon
    self-restarted to pick up a commit. It owns its wake listener as a MANAGED CHILD, so the
    restart killed the listener. `write_rearm_trigger` is by contract "written ONLY on a
    deadline self-cycle -- never on mail exits and never on stand-downs" (R18), so a KILLED
    listener leaves NO trigger behind. `consume_rearms` then had no input, stayed idle and
    CORRECT, and reported nothing wrong while the seat sat deaf and the operator slept.

    THE RULE. A supervisor that owns a worker must re-arm it after the SUPERVISOR'S OWN
    restart: a restart is not a deadline cycle, so the worker's exit path cannot be relied on
    to leave a recovery note.

    WHY `.alive` IS A SOUND INPUT HERE. This failure class exists whenever the recovery
    mechanism's input is produced by the component that died. `.alive` is not: it is touched at
    SessionStart by the SESSION'S own lifecycle (core/comm/incarnation.py) -- a different
    component, with a lifetime that outlives the watcher. That is precisely what breaks the
    in-band loop for this instance.

    SCOPE, stated so it is not oversold: this closes the most common INSTANCE, not the class.
    A session whose daemon never starts at all still produces no input, and that remains the
    job of an out-of-band durable expected-up roster (Wake Doctrine T1/S1, operator-gated).
    """
    from core.comm import wake_seat
    base = tmp or tempfile.gettempdir()
    prefix = f"bifrost_wake_{agent}_"
    armed = 0
    try:
        names = os.listdir(base)
    except Exception:
        return 0
    for name in sorted(names):
        if not (name.startswith(prefix) and name.endswith(".alive")):
            continue
        sid = name[len(prefix):-len(".alive")]
        if not sid:
            continue
        try:
            if os.path.exists(wake_seat.seat_path(agent, sid, base)):
                continue                    # still seated -> live watcher; never double-arm
            trig = rearm_trigger_path(agent, sid, base)
            if os.path.exists(trig):
                continue                    # already requested; idempotent on re-run
            stamp = time.strftime('%Y-%m-%d %H:%M:%S')
            note = (f"[{stamp}] daemon startup: re-arming a session orphaned by the daemon's "
                    f"own restart (no deadline cycle occurred, so the listener left no "
                    f"trigger of its own)")
            with open(trig, "w", encoding="utf-8") as fh:
                fh.write(note + "\n")
            armed += 1
        except Exception:
            continue                        # best-effort: never block daemon startup
    return armed


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
