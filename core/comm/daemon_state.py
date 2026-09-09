"""daemon_state -- the autopilot's shared surface (slice A1, T075 gamma-scope).

Spec: docs/library/report/20260715_presence-autopilot-reconciliation-claude_b5cb93.md.
Daniel directive verbatim: note `presence-autopilot-directive`.

Four consumers, one tiny module:
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
- a BARE RUNNER asks standalone_warning() right after it takes bifrost:runner:<agent>:
  no <ns>:daemon:<agent> key means nobody supervises this seat (no respawn, no circuit
  breaker, no runner-down card) and THIS seat hosts no discord outbound pump beat --
  the absence that read as normal on 2026-08-26 (defer 9e1bc7ce78: Heimdall's Discord
  went silent while every liveness signal stayed green). One LOUD stderr line at
  startup, never a refusal: the runner holds its own lock, not the daemon's, so there
  is nothing to refuse -- only something to say.

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


# ------------------------------------------------- standalone runner (9e1bc7ce78)
#: what a --spawn-runner daemon provides over a runner seat; a bare runner has none of it.
RUNNER_DAEMON_SERVICES = (
    "discord outbound pump beat (fleet-wide election: any live daemon carries every seat's outbound)",
    "runner supervision (respawn + circuit breaker)",
    "presence-card runner-down visibility",
)


def _any_daemon_live(cli, ns: str) -> Optional[bool]:
    """Is ANY <ns>:daemon:* key live? The discord pump election is ONE fleet-wide key
    (discord_feed._PUMP_LOCK_KEY), so one live daemon anywhere hosts every seat's outbound.
    None = cannot tell -- rendered as UNKNOWN, never as a confident claim either way."""
    pattern = f"{ns}:daemon:*"
    try:
        scan = getattr(cli, "scan_iter", None)
        if callable(scan):
            for _ in scan(match=pattern, count=200):
                return True
            return False
        keys = getattr(cli, "keys", None)
        if callable(keys):
            return bool(keys(pattern))
    except Exception:
        pass
    return None


def relaunch_hint(agent: str, runner_script: Optional[str] = None) -> str:
    """The supervised relaunch for a RUNNER seat. The flag IS the brain: a flagless launch is
    alpha mode, which takes runner_lock ITSELF and therefore REFUSES under a live bare runner
    (M1-P11 no-steal) -- the refusal the 2026-08-26 finder hit. The daemon's --runner-script
    default is the deepseek script (RECOVERY.md landmine
    daemon_spawn_runner_hardcodes_deepseek_script), so any other runner names its own; the
    lane flag rides along because a resurrected daemon without it spawns runners whose cursors
    diverge from the drilled work-lane config (revive.py, page-proven)."""
    cmd = f"py scripts/bifrost_daemon.py --agent {agent} --spawn-runner"
    script = str(runner_script or "").strip()
    if script and script != "bifrost_runner_deepseek.py":
        cmd += f" --runner-script {script}"
    return cmd + " --runner-consume-lane work"


def standalone_warning(agent: str, c=None, ns: Optional[str] = None,
                       runner_script: Optional[str] = None) -> Optional[str]:
    """One LOUD line for a runner that just took bifrost:runner:<agent> with no daemon over
    it; None when <ns>:daemon:<agent> is live (a managed child, or a W102 idle-watcher that
    holds its own lock, keeps the pump beat and reclaims when this runner's lock frees).
    Call it AFTER lock acquisition: a refused runner is not standalone. Pure and fail-open:
    doubt renders as doubt ([STANDALONE?]), never as a confident claim in either direction."""
    nsp = _ns(ns)
    key = f"{nsp}:daemon:{agent}"
    cli = _client(c)
    try:
        present = bool(cli.exists(key)) if cli is not None else None
    except Exception:
        present = None
    if present:
        return None
    hint = relaunch_hint(agent, runner_script)
    services = "; ".join(RUNNER_DAEMON_SERVICES)
    tail = f"Supervised relaunch: {hint}  (flagless = alpha mode, which REFUSES under this runner)"
    if present is None:
        return (f"[STANDALONE?] cannot tell whether a daemon holds {key} (bus unanswerable) -- "
                f"if none does, '{agent}' runs WITHOUT its daemon's services: {services}. {tail}")
    fleet = _any_daemon_live(cli, nsp)
    if fleet is True:
        pump = "another seat's daemon is live, so the discord outbound pump still has a host"
    elif fleet is False:
        pump = (f"NO {nsp}:daemon:* key is live anywhere -- the discord outbound pump has NO HOST "
                f"(Discord goes silent while every liveness signal stays green)")
    else:
        pump = (f"could not enumerate {nsp}:daemon:* -- whether the discord outbound pump "
                f"has a host is UNKNOWN")
    return (f"[STANDALONE] no daemon holds {key} -- '{agent}' runs WITHOUT its daemon's "
            f"services: {services}. Fleet: {pump}. {tail}")


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
            # 9e1bc7ce78: the nag names the MODE. consume_rearms runs ONLY under
            # --manage-listener (bifrost_daemon.py gates it on manage_listener); a flagless
            # launch is alpha mode, which answers no .rearm trigger and retires nothing.
            "line": ("[stop-hook] daemon not running -- start it once: "
                     f"py scripts/bifrost_daemon.py --agent {agent} --manage-listener "
                     "(retires the arm chore; ONLY the listener-manager mode answers .rearm "
                     "triggers -- a flagless launch is alpha mode and retires nothing)")
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
