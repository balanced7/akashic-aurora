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

import argparse
import json
import os
import signal
import sys
import tempfile
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def main(argv=None) -> int:
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
                    help="M1-delta: spawn bifrost_runner_deepseek.py as a managed child "
                         "(circuit breaker + summary injection)")
    ap.add_argument("--manage-listener", action="store_true", dest="manage_listener",
                    help="Autopilot A1: answer .rearm triggers by spawning wake listeners "
                         "as managed children + sweep stale markers")
    ap.add_argument("--summary-file", default=None, dest="summary_file",
                    help="path to runner's exit summary (default: state/runner_<agent>_last.json)")
    args = ap.parse_args(argv)

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

    def _spawn_listener(sid: str) -> bool:
        """Spawn a wake listener ManagedChild for sid. Reuses existing child if
        already alive. N1: benign exit = no auto-respawn (next .rearm trigger)."""
        sid8 = sid[:8] if len(sid) > 8 else sid
        if sid8 in listeners and listeners[sid8].alive:
            return True  # already seated
        lch = ManagedChild(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "bifrost_wake.py"),
             "--agent", agent, "--session", sid],
            env=dict(os.environ, BIFROST_WAKE_LANE="work"),
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
    summary_file = args.summary_file or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "state", f"runner_{agent}_last.json")
    last_summary_text = ""

    if spawn_runner or manage_listener:
        dlock = DaemonLock(c, bus.ns, agent, ttl=ttl)
        # R-a1 twin-refusal adapted for the daemon lock
        existing = c.get(f"{bus.ns}:daemon:{agent}")
        if existing:
            try:
                rec = json.loads(existing)
                if rec.get("token") != dlock.token:
                    _say(f"[daemon] refused agent={agent}: another daemon pid={rec.get('pid')} "
                         f"holds the daemon lock -- exiting 0")
                    return 0
            except Exception:
                pass
        if not dlock.acquire():
            _say(f"[daemon] refused agent={agent}: daemon lock held by another process "
                 f"-- exiting 0")
            return 0
        # Coexistence: spawn-runner refuses if a bare runner holds the runner lock.
        # manage-listener-only NEVER touches runner_lock -- it coexists with a
        # consuming session (session:<sid> token, RB-21) and with a bare runner.
        if spawn_runner:
            rh = runner_lock.holder(agent)
            if rh and not str(rh.get("token", "")).startswith("daemon:"):
                _say(f"[daemon] refused agent={agent}: a bare runner pid={rh.get('pid')} holds "
                     f"the runner lock -- stop it first, or let the daemon own it (M1-P11 "
                     f"coexistence) -- exiting 0")
                dlock.release()
                return 0

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

        # ---- runner child (spawn-runner only) --------------------------------------
        if spawn_runner:
            runner_args = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                        "bifrost_runner_deepseek.py"),
                           "--agent", agent, "--agentic",
                           # I6 (api-resilience wave 1, Daniel-sanctioned 2026-07-19: "spin up a
                           # write enabled deepseek module"): the managed spawn omitted the write
                           # door by oversight -- the guarded write_file/edit_file surface + acl
                           # still govern every actual write. Applies at next natural respawn.
                           "--allow-write",
                           "--summary-file", summary_file]
            prev = read_summary(summary_file)
            if prev:
                last_summary_text = format_summary_for_prompt(prev)
                runner_args.extend(["--inject-summary", summary_file])
            child = ManagedChild(
                runner_args,
                env=dict(os.environ),
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                on_blocker=_send_blocker,
                breaker_window_s=float(os.environ.get("AKASHIC_CB_WINDOW_S", "300")),
                breaker_max=int(os.environ.get("AKASHIC_CB_MAX", "3")),
            )

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

            child.on_exit = _on_runner_exit
            if not child.spawn():
                _say(f"[daemon] runner spawn blocked agent={agent} (circuit breaker pre-tripped?) "
                     f"-- daemon still alive, restart to reset")
            else:
                _say(f"[daemon] runner spawned agent={agent} pid={child.pid}")
        _say(f"[daemon] up agent={agent} ns={bus.ns} daemon-token={dlock.token[:20]}... "
             f"ttl={ttl}s hb={hb}s pid={os.getpid()}"
             + (" mode=runner-manager" if spawn_runner else "")
             + (" mode=listener-manager" if manage_listener else ""))
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
            "slice": "M1-alpha" if not (spawn_runner or manage_listener) else "M1-delta",
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
    next_dark_probe = 0.0
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

            # ---- child poll -------------------------------------------------------
            if child is not None:
                child.poll()
            for _sid, lch in list(listeners.items()):
                lch.poll()

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
                            pager.page(agent, f"runner down {int(down_s/60)}m -- "
                                              f"daemon holding presence; doctor {agent}")
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
