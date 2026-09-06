"""bifrost.daemon -- the agent's continuous-presence body (T075 M1-alpha + M1-delta).

Spec: docs/library/report/20260715_t060-m1-continuous-presence-reconciliati_32cac4.md (fence t060-m1-design
CLOSED; deepseek's blind half governs the pins). M1-alpha: lock + presence +
heartbeat + bus-loss guard + stable identity + clean exits. M1-delta: runner as
managed child + circuit breaker + summary-injection convo survival (v1).

TWO LOCK TIERS (delta split, no conflict):
  bifrost:daemon:<agent>  -- the daemon's own singleton lock (DaemonLock in
                             bifrost_child.py). Prevents twin daemons only.
  bifrost:runner:<agent>  -- the runner child's lock (existing runner_lock).
                             Guards the consume path; byte-identical to today.
The daemon checks runner_lock.holder() before spawning -- a bare runner already
live = refuse (coexistence, M1-P11).

- NO consume-path moves (ruling 1: the cursor stays where it is; daemon-as-consumer
  is PARKED behind T047 + its own fence).
- Managed children via bifrost_child.ManagedChild: backoff restart, circuit breaker
  (3 crashes/5min -> blocker).

  py scripts/bifrost_daemon.py --agent deepseek --spawn-runner
  py scripts/bifrost_daemon.py --agent claude                        # M1-alpha mode
  py scripts/bifrost_daemon.py --agent t075drill --max-runtime 5     # drill hatch
"""
from __future__ import annotations

# --- windowless (2026-09-05 fleet cmd-spam fix): load the tree's console-suppression
# in-process so every subprocess (git presence/heartbeat, etc.) this process or its
# children spawn is CREATE_NO_WINDOW. Does NOT depend on PYTHONPATH being wired into the
# launch env -- that missing wiring was the original gap. Idempotent; honors
# AKASHIC_SHOW_CONSOLES (the sitecustomize's own escape hatch). ---
import os as _os, sys as _sys
_qd = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "scripts", "quiet")
if _os.path.isdir(_qd):
    if _qd not in _sys.path:
        _sys.path.insert(0, _qd)
    try:
        import sitecustomize as _quiet_sitecustomize  # noqa: F401  (patches subprocess.Popen)
    except Exception:
        pass

import argparse
import json
import os
import signal
import sys
import tempfile
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Top-level so check_wiring's reachability graph SEES the edge — the feed beat below is the
# production caller that makes the T223 bridge real (built != wired was this exact feature's
# recurring wound, and an import hidden inside the loop body re-created it at the graph layer).
from core.comm.seat_identity import git_identity_env as _GIT_ID  # noqa: E402  (t384: author=seat)
from core.comm import discord_feed as _DFEED  # noqa: E402
from core.comm import self_restart as _SELF_RESTART  # noqa: E402  (t376 S2: daemon stale-code arm)

_STOP = {"flag": False, "reason": ""}


def _say(line: str) -> None:
    print(line, flush=True)


def _stable_token(agent: str) -> str:
    """The daemon's identity: minted once, reused across restarts (M1-P12).
    Atomic write (tmp+replace) so a crash mid-mint never leaves a torn id file."""
    d = os.path.join(os.path.expanduser("~"), ".akashic")
    path = os.path.join(d, f"daemon_{agent}.id")
    try:
        with open(path, encoding="utf-8") as f:
            tok = f.read().strip()
        if tok:
            return tok
    except OSError:
        pass
    tok = f"daemon:{agent}:{uuid.uuid4().hex}"
    os.makedirs(d, exist_ok=True)
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(tok + "\n")
    os.replace(tmp, path)
    return tok


def _install_signals() -> None:
    def _handle(signum, _frame):
        _STOP["flag"] = True
        _STOP["reason"] = "sigint" if signum == getattr(signal, "SIGINT", None) else f"signal-{signum}"
    # SIGBREAK is the Windows CTRL_BREAK path (how a drill stops a console child);
    # SIGTERM registers harmlessly where the platform supports it.
    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _handle)
        except (ValueError, OSError):
            pass


def _env_int(name: str, fallback: int) -> int:
    try:
        v = int(os.environ.get(name, "") or 0)
        return v if v > 0 else fallback
    except (TypeError, ValueError):
        return fallback


def _exit_code(value: str) -> int:
    parsed = int(value)
    if not 0 <= parsed <= 255:
        raise argparse.ArgumentTypeError("exit code must be between 0 and 255")
    return parsed


def daemon_self_restart_reason(
    agent: str,
    *,
    in_flight: bool = False,
    external_supervisor: bool = False,
):
    """Rotate only when this daemon owns its own process lifetime.

    ``respawn_self`` deliberately detaches its successor on Windows.  That is the
    right metabolism for an ad-hoc daemon, but an externally supervised service
    must keep the supervisor-owned process alive so crashes remain observable and
    retryable by that supervisor.
    """
    if external_supervisor:
        return None
    return _SELF_RESTART.maybe_self_restart(agent, in_flight=in_flight)


def acquire_daemon_lock(
    dlock,
    *,
    external_supervisor: bool = False,
    retry_s: float = 1.0,
    sleep_fn=time.sleep,
) -> bool:
    """Acquire once by default; supervised services wait in the same process.

    A scheduler cannot reliably own a service that exits during the lease handoff.
    Waiting here keeps the original scheduled action alive while the prior TTL
    expires.  The unsupervised contract remains fail-fast.
    """
    delay = float(retry_s)
    if delay <= 0:
        raise ValueError("daemon lock retry interval must be positive")
    while True:
        if dlock.acquire():
            return True
        if not external_supervisor:
            return False
        sleep_fn(delay)


def build_parser() -> argparse.ArgumentParser:
    """Build the daemon CLI; extracted so launch posture is offline-testable."""
    ap = argparse.ArgumentParser(
        description="Continuous-presence daemon (M1-alpha + M1-delta): lock + presence "
                    "+ heartbeat + bus-loss guard + managed-runner child.")
    ap.add_argument("--agent", required=True, help="agent id whose presence this daemon holds")
    ap.add_argument("--ttl", type=int, default=None,
                    help="lock TTL seconds (default: env AKASHIC_DAEMON_LOCK_TTL_S raw, else scaled 60)")
    ap.add_argument("--hb", type=int, default=None,
                    help="heartbeat seconds (default: env AKASHIC_DAEMON_HB_S raw, else scaled 8; clamped < ttl)")
    ap.add_argument("--max-runtime", type=float, default=0.0, dest="max_runtime",
                    help="exit cleanly after N RAW seconds (drill hatch; 0 = run forever)")
    ap.add_argument("--spawn-runner", action="store_true", dest="spawn_runner",
                    help="M1-delta: spawn the selected Bifrost runner as a managed child "
                         "(circuit breaker + summary injection)")
    ap.add_argument(
        "--runner-script",
        default="bifrost_runner_deepseek.py",
        dest="runner_script",
        help=(
            "runner basename under scripts/ (default bifrost_runner_deepseek.py); "
            "use bifrost_runner_sol.py for Sunshine"
        ),
    )
    ap.add_argument(
        "--runner-arg",
        action="append",
        default=[],
        dest="runner_arg",
        help=(
            "extra child argument, repeatable; use --runner-arg=--flag when the value "
            "begins with a dash"
        ),
    )
    ap.add_argument(
        "--runner-consume-lane",
        choices=("legacy", "work"),
        default=None,
        dest="runner_consume_lane",
        help="explicit consume lane inherited by the managed runner child",
    )
    ap.add_argument(
        "--refusal-exit-code",
        type=_exit_code,
        default=0,
        dest="refusal_exit_code",
        help=(
            "exit code when another daemon owns the singleton lease (default 0); "
            "a host supervisor may use a nonzero code to request retry"
        ),
    )
    ap.add_argument(
        "--external-supervisor",
        action="store_true",
        dest="external_supervisor",
        help=(
            "keep this daemon process anchored to an external supervisor instead of "
            "launching a detached stale-code successor"
        ),
    )
    ap.add_argument("--manage-listener", action="store_true", dest="manage_listener",
                    help="Autopilot A1: answer .rearm triggers by spawning wake listeners "
                         "as managed children + sweep stale markers")
    ap.add_argument("--summary-file", default=None, dest="summary_file",
                    help="path to runner's exit summary (default: state/runner_<agent>_last.json)")
    return ap


def managed_runner_argv(
    agent: str,
    summary_file: str,
    *,
    runner_script: str = "bifrost_runner_deepseek.py",
    runner_args=None,
    inject_summary: bool = False,
):
    """Construct one full-door managed child command without changing legacy defaults."""
    name = str(runner_script or "").strip()
    if (
        not name
        or name != os.path.basename(name)
        or not name.startswith("bifrost_runner_")
        or not name.endswith(".py")
    ):
        raise ValueError(f"invalid managed runner basename: {runner_script!r}")
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    if not os.path.isfile(script):
        raise ValueError(f"managed runner does not exist: {script}")
    extra = [str(value) for value in (runner_args or [])]
    if any(not value or "\x00" in value for value in extra):
        raise ValueError("managed runner arguments must be non-empty strings without NUL")
    command = [
        sys.executable,
        script,
        "--agent",
        str(agent),
        "--agentic",
        "--allow-write",
        "--allow-exec",
        *extra,
        "--summary-file",
        str(summary_file),
    ]
    if inject_summary:
        command.extend(["--inject-summary", str(summary_file)])
    return command


def managed_runner_env(
    agent: str,
    *,
    consume_lane=None,
    base=None,
):
    """Build the managed child's environment with an optional attested lane."""
    lane = str(consume_lane or "").strip().lower() or None
    if lane not in (None, "legacy", "work"):
        raise ValueError(f"invalid managed runner consume lane: {consume_lane!r}")
    environment = dict(os.environ if base is None else base)
    environment.update(_GIT_ID(agent))
    if lane is not None:
        environment["BIFROST_CONSUME_LANE"] = lane
    return environment


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    from typing import Optional as _Opt
    from core.comm import runner_lock
    from core.comm.bus import Bus
    from core.comm.timescale import scaled
    from typing import Dict, Optional
    from scripts.bifrost_child import DaemonLock, ManagedChild, read_summary, format_summary_for_prompt
    from core.comm import daemon_state as _ds

    agent = str(args.agent)
    ttl = int(args.ttl) if args.ttl else _env_int("AKASHIC_DAEMON_LOCK_TTL_S", scaled(60))
    hb = int(args.hb) if args.hb else _env_int("AKASHIC_DAEMON_HB_S", scaled(8))
    hb = max(1, min(hb, max(1, ttl // 2)))
    guard_every = scaled(30)
    token = _stable_token(agent)

    bus = Bus(agent, promote=False)
    if not (bus.online and bus.probe()):
        _say(f"[daemon] bus OFFLINE at launch agent={agent} -- exiting 2 "
             f"(the host supervisor owns backoff; a presence daemon with no bus has nothing to hold)")
        return 2

    c = bus._client
    spawn_runner = bool(args.spawn_runner)
    manage_listener = bool(args.manage_listener)

    # ---- A1 listener management state -------------------------------------------
    listeners: Dict[str, ManagedChild] = {}     # sid[:8] -> ManagedChild
    next_marker_sweep: float = 0.0              # boot + hourly

    def _spawn_listener(sid: str, ns: _Opt[str] = None) -> bool:
        """Spawn a wake listener ManagedChild for sid. Reuses existing child if
        already alive. N1: benign exit = no auto-respawn (next .rearm trigger).

        T167: `ns` exists because the ONLY caller has always passed it --
        `lambda sid: _spawn_listener(sid, bus.ns)` -- against a one-argument def. Every rearm
        raised TypeError, consume_rearms swallowed it ("falsy/raising leaves it for the next
        tick"), and the autopilot spawned nothing, forever, in silence. Reproduced 2026-08-04:
        a valid trigger for session cdfb9126 went unanswered for 134s with the daemon alive.
        The caller's intent is honoured rather than deleted -- the listener now inherits the
        namespace it was always meant to be given.
        """
        sid8 = sid[:8] if len(sid) > 8 else sid
        if sid8 in listeners and listeners[sid8].alive:
            return True  # already seated
        _env = dict(os.environ, BIFROST_WAKE_LANE="work")
        if ns:
            _env["BIFROST_NAMESPACE"] = str(ns)
        lch = ManagedChild(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "bifrost_wake.py"),
             "--agent", agent, "--session", sid],
            env=_env,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            breaker_window_s=300,
            breaker_max=3,
        )
        if lch.spawn():
            listeners[sid8] = lch
            _say(f"[daemon] listener spawned agent={agent} sid={sid8} pid={lch.pid}")
            return True
        return False

    # ---- delta path: daemon lock (bifrost:daemon:<agent>) + runner child ----------
    child: _Opt[ManagedChild] = None
    dlock = None
    idle_mode = False  # W102: daemon alive but runner spawning deferred
    summary_file = args.summary_file or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "state", f"runner_{agent}_last.json")
    last_summary_text = ""

    if spawn_runner or manage_listener:
        dlock = DaemonLock(c, bus.ns, agent, ttl=ttl)
        # R-a1 twin-refusal adapted for the daemon lock
        existing = c.get(f"{bus.ns}:daemon:{agent}")
        waited_for_lock = False
        if existing:
            try:
                rec = json.loads(existing)
                if rec.get("token") != dlock.token:
                    if not args.external_supervisor:
                        refusal_code = int(args.refusal_exit_code)
                        _say(f"[daemon] refused agent={agent}: another daemon pid={rec.get('pid')} "
                              f"holds the daemon lock -- exiting {refusal_code}")
                        return refusal_code
                    waited_for_lock = True
                    _say(f"[daemon] waiting agent={agent}: prior daemon pid={rec.get('pid')} "
                          "holds the lease; external supervisor keeps this process "
                          "anchored until the TTL handoff")
            except Exception:
                pass
        if not acquire_daemon_lock(
            dlock,
            external_supervisor=args.external_supervisor,
            retry_s=min(max(float(hb), 1.0), 5.0),
        ):
            refusal_code = int(args.refusal_exit_code)
            _say(f"[daemon] refused agent={agent}: daemon lock held by another process "
                  f"-- exiting {refusal_code}")
            return refusal_code
        if waited_for_lock:
            _say(f"[daemon] acquired agent={agent}: prior daemon lease released; "
                 "scheduler-owned process retained")
        # Coexistence: spawn-runner inspects the runner lock BEFORE spawning.
        # manage-listener-only NEVER touches runner_lock -- it coexists with a
        # consuming session (session:<sid> token, RB-21) and with a bare runner.
        if spawn_runner:
            rh = runner_lock.holder(agent)
            if rh and not str(rh.get("token", "")).startswith("daemon:"):
                # W102 full fix: a foreign bare runner (self-restarted successor,
                # kimi-style self-managing seat) holds the seat. The daemon goes IDLE
                # instead of refusing boot: it holds its own daemon lock, maintains
                # presence, and probes runner_lock.holder() until the foreign holder
                # releases -- then it reclaims and spawns. This closes the gap the
                # half-fix (28c5bcd) discovered: the hard-refuse left the seat
                # daemon-less until the takeover chain broke.
                _say(f"[daemon] idle agent={agent}: a foreign runner pid={rh.get('pid')} "
                     f"holds the runner lock (token prefix: {str(rh.get('token', ''))[:20]}...) "
                     f"-- daemon alive, spawning deferred; will reclaim when lock frees "
                     f"(W102 idle-watcher)")
                idle_mode = True

        # ---- blocker callback (M1-P9 circuit breaker) ------------------------------
        def _send_blocker():
            try:
                bus.broadcast("blocker",
                              f"[blocker] runner child for '{agent}' unstable: "
                              f"{child._breaker_max} crashes in "
                              f"{int(child._breaker_window_s)}s -- restarting stopped. "
                              f"Daemon presence still held. Restart the daemon to reset.",
                              meta={"via": f"{agent}-daemon", "kind": "blocker"})
                _say(f"[daemon] BLOCKER broadcast agent={agent}: circuit breaker tripped "
                     f"({child._breaker_max} crashes in {int(child._breaker_window_s)}s)")
            except Exception:
                pass

        def _on_runner_exit(code: int, tail: str):
            s = read_summary(summary_file)
            if s:
                child.last_summary = s
                nonlocal last_summary_text
                last_summary_text = format_summary_for_prompt(s)
                _say(f"[daemon] runner exited code={code} summary={last_summary_text}")
            else:
                _say(f"[daemon] runner exited code={code} (no summary file)")
            if tail:
                short = " ".join(str(tail).split())[:200]
                if short:
                    _say(f"[daemon] runner tail: {short}")

        # ---- runner child (spawn-runner only) --------------------------------------
        if spawn_runner and not idle_mode:
            prev = read_summary(summary_file)
            runner_args = managed_runner_argv(
                agent,
                summary_file,
                runner_script=args.runner_script,
                runner_args=args.runner_arg,
                inject_summary=bool(prev),
            )
            if prev:
                last_summary_text = format_summary_for_prompt(prev)
            child = ManagedChild(
                runner_args,
                env=managed_runner_env(
                    agent,
                    consume_lane=args.runner_consume_lane,
                ),
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                on_blocker=_send_blocker,
                breaker_window_s=float(os.environ.get("AKASHIC_CB_WINDOW_S", "300")),
                breaker_max=int(os.environ.get("AKASHIC_CB_MAX", "3")),
            )

            child.on_exit = _on_runner_exit
            if not child.spawn():
                _say(f"[daemon] runner spawn blocked agent={agent} (circuit breaker pre-tripped?) "
                     f"-- daemon still alive, restart to reset")
            else:
                _say(f"[daemon] runner spawned agent={agent} pid={child.pid}")
        _say(f"[daemon] up agent={agent} ns={bus.ns} daemon-token={dlock.token[:20]}... "
             f"ttl={ttl}s hb={hb}s pid={os.getpid()}"
             + (" mode=runner-manager" if (spawn_runner and not idle_mode) else "")
             + (" mode=listener-manager" if manage_listener else "")
             + (" mode=idle-watcher" if idle_mode else ""))
        # 2026-09-06 incident: this daemon owns its wake listener as a MANAGED CHILD, so its
        # own restart KILLS that listener -- and a killed listener writes no .rearm trigger
        # (R18 writes one only on a deadline self-cycle). consume_rearms then has no input and
        # sits idle and correct while the seat is deaf. A supervisor must therefore re-arm
        # after ITS OWN restart, from a signal the dead worker did not produce.
        if manage_listener:
            try:
                _armed = _ds.rearm_orphaned_sessions(agent, tmp=tempfile.gettempdir())
                if _armed:
                    _say(f"[daemon] startup re-arm agent={agent} sessions={_armed} "
                         f"(orphaned by this daemon's restart; no deadline cycle occurred)")
            except Exception as _e:
                _say(f"[daemon] startup re-arm FAILED agent={agent}: "
                     f"{type(_e).__name__}: {_e} -- listeners may need a manual arm")
    else:
        # ---- alpha path: daemon holds the runner lock directly ---------------------
        h = runner_lock.holder(agent)
        if h and h.get("token") == token and int(h.get("pid") or -1) != os.getpid():
            _say(f"[daemon] refused agent={agent}: live twin pid={h.get('pid')} holds MY token "
                 f"(delete ~/.akashic/daemon_{agent}.id to fork identity; a crashed twin expires "
                 f"within ttl={ttl}s) -- exiting 0")
            return 0
        if not runner_lock.acquire(agent, token, ttl=ttl):
            h = runner_lock.holder(agent) or {}
            _say(f"[daemon] refused agent={agent}: held by pid={h.get('pid', '?')} "
                 f"token8={str(h.get('token', ''))[-8:]} (M1-P11 coexistence -- no steal; "
                 f"stop the holder or wait out its TTL) -- exiting 0")
            return 0
        gen = runner_lock.generation_of(token)
        _say(f"[daemon] up agent={agent} ns={bus.ns} token={token} gen={gen} "
             f"ttl={ttl}s hb={hb}s pid={os.getpid()} mode=alpha")

    # ---- shared: presence card + heartbeat loop -----------------------------------
    card = {"runtime_class": "daemon", "wake_mode": "supervisor",
            "door": "scripts/bifrost_daemon.py",
            "slice": ("M1-delta" if (spawn_runner and not idle_mode or manage_listener)
                      else "W102-idle" if idle_mode
                      else "M1-alpha"),
            "pid": os.getpid(),
            "token8": (dlock.token[-8:] if (spawn_runner or manage_listener) else token[-8:]),
            "gen": 0 if (spawn_runner or manage_listener) else runner_lock.generation_of(token),
            "runtimes": {}}
    if spawn_runner and last_summary_text:
        card["summary"] = last_summary_text
    bus.register(card=card)

    # T077 A3: runner-down visibility + 10-min re-escalation
    runner_down_since: Optional[float] = None
    runner_last_escalation: float = 0.0
    RE_ESCALATION_S = 600  # 10 minutes

    _install_signals()
    started = time.time()
    next_beat = 0.0
    next_discord_feed = 0.0
    next_dark_probe = 0.0
    next_self_restart_check = 0.0
    dark_since = None
    reason = "stop"
    try:
        while True:
            if _STOP["flag"]:
                reason = _STOP["reason"] or "signal"
                break
            if args.max_runtime and (time.time() - started) >= args.max_runtime:
                reason = "max-runtime"
                break
            time.sleep(0.2)
            now = time.time()

            # ---- discord feed beat: the subscription that makes the T223 bridge real.
            # Off-by-default (configured() is one env read when unset); tail-inits on
            # first contact so the archive never replays to a phone; and a notification
            # mirror must never wound the supervisor, hence the blanket except.
            if now >= next_discord_feed:
                next_discord_feed = now + 10.0
                try:
                    if _DFEED.configured():
                        # pump_if_owner (not pump): four seats' daemons all reach this
                        # tick independently -- the election makes them ONE logical
                        # pump instead of four racing the same cursor + webhook.
                        _DFEED.pump_if_owner(bus)
                except Exception:                                       # noqa: BLE001
                    pass

            # ---- t376 S2: the daemon's stale-code arm (its own metabolism) --------
            # Runners already metabolize (maybe_self_restart at their loop top); the
            # daemon did not (E2). This is the same ceremony: at a turn boundary,
            # compare the daemon's OWN stamp to a FRESH HEAD, and when provably stale
            # past cooldown + jitter and idle, respawn a successor (same argv/env) and
            # stand down cleanly via the respawn-before-exit-0 contract (S1). Gated on
            # a slow cadence (guard_every, 30s) so gather()'s git calls don't run every
            # 0.2s tick. in_flight reflects LIVE child-management state — a stale-code
            # rotation must never land mid-child-spawn and orphan a spawn (S2-P3).
            if now >= next_self_restart_check:
                next_self_restart_check = now + guard_every
                try:
                    _in_flight = bool(child is not None and child.alive) or \
                                 any(lch.alive for lch in listeners.values())
                    _reason = daemon_self_restart_reason(
                        agent,
                        in_flight=_in_flight,
                        external_supervisor=args.external_supervisor,
                    )
                    if _reason:
                        _say(f"[daemon] self-restart agent={agent}: {_reason} -- "
                             f"successor launched; standing down (respawn-before-exit-0)")
                        reason = _reason
                        break
                except Exception:                                       # noqa: BLE001
                    pass

            # ---- child poll -------------------------------------------------------
            if child is not None:
                child.poll()
            for _sid, lch in list(listeners.items()):
                lch.poll()

            # ---- W102: idle-mode reclaim probe (once per heartbeat) ---------------
            # When the daemon booted under a foreign holder (bare runner, self-
            # restarted successor), it went idle instead of refusing. Probe the
            # runner lock on each heartbeat cadence; when the foreign holder releases
            # (or its token becomes daemon-prefixed), spawn the runner child and
            # leave idle mode. The reclaim check fires at the same rate as the
            # heartbeat (hb seconds) so it never thrashes Redis.
            if idle_mode and spawn_runner and child is None:
                try:
                    rh = runner_lock.holder(agent)
                    if rh is None:
                        _say(f"[daemon] reclaim agent={agent}: runner lock freed -- "
                             f"spawning runner child (W102)")
                        idle_mode = False
                    elif str(rh.get("token", "")).startswith("daemon:"):
                        _say(f"[daemon] reclaim agent={agent}: runner lock now held by "
                             f"a daemon token -- spawning runner child (W102)")
                        idle_mode = False
                    if not idle_mode:
                        # Re-run the spawn block with the same explicit runner contract.
                        prev = read_summary(summary_file)
                        runner_args = managed_runner_argv(
                            agent,
                            summary_file,
                            runner_script=args.runner_script,
                            runner_args=args.runner_arg,
                            inject_summary=bool(prev),
                        )
                        if prev:
                            # last_summary_text is main()'s own local -- plain
                            # assignment binds it; `nonlocal` here is a SyntaxError
                            # (only legal in a NESTED function; fence red 2026-07-29).
                            last_summary_text = format_summary_for_prompt(prev)
                        child = ManagedChild(
                            runner_args,
                            env=managed_runner_env(
                                agent,
                                consume_lane=args.runner_consume_lane,
                            ),
                            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            on_blocker=_send_blocker,
                            breaker_window_s=float(os.environ.get("AKASHIC_CB_WINDOW_S", "300")),
                            breaker_max=int(os.environ.get("AKASHIC_CB_MAX", "3")),
                        )
                        child.on_exit = _on_runner_exit
                        if not child.spawn():
                            _say(f"[daemon] reclaim spawn BLOCKED agent={agent} "
                                 f"(circuit breaker pre-tripped?) -- daemon still alive")
                        else:
                            _say(f"[daemon] runner spawned agent={agent} pid={child.pid} "
                                 f"(reclaimed from idle, W102)")
                            card["slice"] = "M1-delta"
                except Exception as e:
                    _say(f"[daemon] reclaim probe error agent={agent}: "
                         f"{type(e).__name__}: {e} -- will retry")

            # ---- A1: consume rearm triggers + marker sweep -----------------------
            if manage_listener:
                _ds.consume_rearms(agent,
                    lambda sid: _spawn_listener(sid, bus.ns),
                    tmp=tempfile.gettempdir())
                if now >= next_marker_sweep:
                    swept = _ds.sweep_stale_markers(agent, tmp=tempfile.gettempdir())
                    if swept:
                        _say(f"[daemon] marker sweep agent={agent} removed={swept}")
                    next_marker_sweep = now + 3600

            # ---- A1+A3: build runtimes from ALL children --------------------------
            rt_input = {}
            if child is not None:
                rt_input["runner"] = child
            for sid8, lch in listeners.items():
                rt_input[f"listener:{sid8}"] = lch
            card["runtimes"] = _ds.build_runtimes(rt_input) if rt_input else {}

            # ---- A3: runner-down re-escalation -----------------------------------
            runner_state = card["runtimes"].get("runner", "")
            if runner_state in ("down", "blocked"):
                # W102: the child handle is a SPAWN-TOOL, not a liveness instrument.
                # A self-restarted successor (stale-code takeover, launcher recover)
                # holds the seat's runner_lock while the daemon's own child is long
                # dead. Consult the seat's lock -- the same instrument the spawn path
                # already trusts (holder() before spawning) -- before counting the
                # seat down. Live receipt 2026-07-29: healthy exit-0 successors did
                # the seat's work for 30+ min while the daemon paged runner_down
                # every re-escalation window.
                try:
                    from core.comm import runner_lock as _rl
                    seat_held = bool(_rl.holder(agent))
                except Exception:
                    seat_held = False        # unknowable lock: keep legacy behavior
                if seat_held:
                    if runner_down_since is not None:
                        _say(f"[daemon] child down but '{agent}' seat lock is HELD -- "
                             f"foreign/self-restarted runner has the seat; standing "
                             f"down the escalation and retracting the page (W102)")
                        try:
                            from core.comm import pager
                            pager.clear_key(f"{agent}:runner_down")
                        except Exception:
                            pass
                    runner_down_since = None
                else:
                    if runner_down_since is None:
                        runner_down_since = now
                    down_s = int(now - runner_down_since)
                    if runner_state == "down" and down_s >= RE_ESCALATION_S \
                            and (now - runner_last_escalation) >= RE_ESCALATION_S:
                        try:
                            bus.broadcast("blocker",
                                          f"[blocker] runner for '{agent}' down {int(down_s/60)}min — "
                                          f"daemon presence held. Check: py agent_cli.py doctor {agent}",
                                          meta={"via": f"{agent}-daemon", "kind": "blocker"})
                            runner_last_escalation = now
                            _say(f"[daemon] re-escalation broadcast agent={agent}: "
                                 f"runner down {int(down_s/60)}min")
                            try:   # T078-W4: page-grade -> the pager surface (a live
                                #    seat relays via PushNotification; hook injects [PAGE])
                                from core.comm import pager
                                # KEYED so this page can be RETRACTED when the runner comes
                                # back. A keyless page has no retraction path and renders
                                # forever (2026-07-27: a resolved lane_stall shouted into
                                # every prompt for nine hours). Same key shape the doctor
                                # uses -- "<agent>:<state>".
                                pager.page(agent, f"runner down {int(down_s/60)}m -- "
                                                  f"daemon holding presence; doctor {agent}",
                                           key=f"{agent}:runner_down")
                            except Exception:
                                pass
                        except Exception:
                            pass
            else:
                runner_down_since = None
            if child is not None and child.last_summary:
                latest = format_summary_for_prompt(child.last_summary)
                if latest != card.get("summary"):
                    card["summary"] = latest

            if now < next_beat:
                continue
            next_beat = now + hb
            if dark_since is not None and now < next_dark_probe:
                continue
            if not bus.probe():
                if dark_since is None:
                    dark_since = now
                    _say(f"[daemon] bus lost agent={agent} -- guard engaged "
                         f"(probe every {guard_every}s; tenure survives)")
                next_dark_probe = now + guard_every
                continue
            if dark_since is not None:
                _say(f"[daemon] bus back agent={agent} after {int(now - dark_since)}s "
                     f"-- presence re-registered")
                dark_since = None

            # ---- lock heartbeat ---------------------------------------------------
            if spawn_runner or manage_listener:
                if not dlock.heartbeat():
                    _say(f"[daemon] stand-down agent={agent}: daemon lock lost -- exiting 0")
                    return 0
            else:
                if not runner_lock.heartbeat(agent, token, ttl=ttl):
                    _say(f"[daemon] stand-down agent={agent}: lock lost to a successor -- exiting 0")
                    return 0

            bus.register(card=card)

        # ---- clean exit -----------------------------------------------------------
        for _sid, lch in list(listeners.items()):
            lch.terminate()
        if spawn_runner and child is not None:
            child.terminate()
        if spawn_runner or manage_listener:
            if dlock is not None:
                dlock.release()
        else:
            runner_lock.release(agent, token)
        _say(f"[daemon] clean exit agent={agent} reason={reason} (lock released)")
        return 0
    except Exception as e:
        _say(f"[daemon] FAULT agent={agent}: {type(e).__name__}: {e} -- exiting 1")
        return 1
    finally:
        try:
            for _sid, lch in list(listeners.items()):
                lch.terminate()
            if spawn_runner and child is not None:
                child.terminate()
            if spawn_runner or manage_listener:
                if dlock is not None:
                    dlock.release()
            else:
                runner_lock.release(agent, token)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
