"""bifrost.daemon -- the agent's continuous-presence body (T075 M1-alpha skeleton).

Spec: research/reviewed/t060-m1-reconciliation-2026-07-15.md (fence t060-m1-design
CLOSED; deepseek's blind half governs the pins: M1-P1/P2/P11/P12). This slice is
lock + presence + heartbeat + bus-loss guard + stable identity + clean exits, and
NOTHING else:

- NO consume-path moves (ruling 1: the cursor stays where it is; daemon-as-consumer
  is PARKED behind T047 + its own fence). The daemon never touches ns:cursor:*.
- NO child runtimes (wake listener / runner stay standalone; managed children are
  M1-gamma/delta).

Pure COMPOSITION of existing primitives -- bus.py and runner_lock.py are untouched:

- runner_lock.acquire/heartbeat/release: the SAME singleton lock a runner or a
  consuming session holds. A pre-existing holder means REFUSE AND EXIT (M1-P11
  coexistence -- the operator chooses who runs; no steal, no wait-loop).
- Bus.register(card=...): presence under the agent's id with a card marked
  runtime_class=daemon, refreshed every heartbeat.
- Stable identity (M1-P12, reconciliation ruling 7): the token lives in
  ~/.akashic/daemon_<agent>.id and is REUSED across restarts -- the fencing
  generation (minted per acquisition, L1b) is what distinguishes tenures, not the
  token. This deliberately inverts runner_lock's pid:random convention; the twin
  hazard that inversion creates is handled below (R-a1).

R-a1 SAME-TOKEN TWIN REFUSAL: with a stable token, a double-launch on one host
presents as the lock's OWN token under a foreign pid, and runner_lock's re-entrant
path would welcome it. The daemon pre-checks holder(): same token + different pid =
live twin = refuse, exit 0. No pid liveness probe -- os.kill(pid, 0) on Windows
TERMINATES the target -- so a crashed predecessor's record simply expires within
one lock TTL and the next launch succeeds (host-supervisor retries absorb the gap).

BUS-LOSS GUARD (RB-30 discipline): liveness is bus.probe() per beat -- NEVER
`online`, which is a construction-time fact and can never flip mid-run. While dark
the daemon probes at guard cadence and does nothing else; the lock may lapse, and
recovery rides heartbeat()'s own vanished-lock nx-reclaim (tenure generation kept;
a usurper that acquired during the outage wins by TTL truth and we stand down).

Exit codes (wake-listener discipline -- operator-facing): 0 = every benign ending
(clean stop, refusal, stand-down); 2 = bus offline at launch (the host supervisor
owns backoff/retry); 1 = real fault.

  py scripts/bifrost_daemon.py --agent claude
  py scripts/bifrost_daemon.py --agent deepseek --ttl 60 --hb 8
  py scripts/bifrost_daemon.py --agent t075drill --max-runtime 5   # drill hatch
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
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
        description="Continuous-presence daemon skeleton (M1-alpha): lock + presence "
                    "+ heartbeat + bus-loss guard. No consume moves, no children.")
    ap.add_argument("--agent", required=True, help="agent id whose presence this daemon holds")
    ap.add_argument("--ttl", type=int, default=None,
                    help="lock TTL seconds (default: env AKASHIC_DAEMON_LOCK_TTL_S raw, else scaled 60)")
    ap.add_argument("--hb", type=int, default=None,
                    help="heartbeat seconds (default: env AKASHIC_DAEMON_HB_S raw, else scaled 8; clamped < ttl)")
    ap.add_argument("--max-runtime", type=float, default=0.0, dest="max_runtime",
                    help="exit cleanly after N RAW seconds (drill hatch; 0 = run forever)")
    args = ap.parse_args(argv)

    from core.comm import runner_lock
    from core.comm.bus import Bus
    from core.comm.timescale import scaled

    agent = str(args.agent)
    ttl = int(args.ttl) if args.ttl else _env_int("AKASHIC_DAEMON_LOCK_TTL_S", scaled(60))
    hb = int(args.hb) if args.hb else _env_int("AKASHIC_DAEMON_HB_S", scaled(8))
    hb = max(1, min(hb, max(1, ttl // 2)))   # a heartbeat slower than the TTL is a self-eviction
    guard_every = scaled(30)                  # dark-probe cadence (M1-P10 lineage)
    token = _stable_token(agent)

    bus = Bus(agent, promote=False)
    if not (bus.online and bus.probe()):
        _say(f"[daemon] bus OFFLINE at launch agent={agent} -- exiting 2 "
             f"(the host supervisor owns backoff; a presence daemon with no bus has nothing to hold)")
        return 2

    # R-a1: a live twin wears OUR token with a foreign pid -- refuse before acquire()
    # would re-entrantly welcome it. (A crashed twin's record expires within `ttl`.)
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
    card = {"runtime_class": "daemon", "wake_mode": "supervisor",
            "door": "scripts/bifrost_daemon.py", "slice": "M1-alpha",
            "pid": os.getpid(), "token8": token[-8:], "gen": gen}
    bus.register(card=card)
    _say(f"[daemon] up agent={agent} ns={bus.ns} token={token} gen={gen} "
         f"ttl={ttl}s hb={hb}s pid={os.getpid()}")

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
            time.sleep(0.2)   # tick: signal-responsive, raw-seconds max-runtime precision
            now = time.time()
            if now < next_beat:
                continue
            next_beat = now + hb
            if dark_since is not None and now < next_dark_probe:
                continue
            if not bus.probe():
                if dark_since is None:
                    dark_since = now
                    _say(f"[daemon] bus lost agent={agent} -- guard engaged "
                         f"(probe every {guard_every}s; tenure survives: heartbeat's "
                         f"nx-reclaim keeps gen, a usurper wins by TTL truth)")
                next_dark_probe = now + guard_every
                continue
            if dark_since is not None:
                _say(f"[daemon] bus back agent={agent} after {int(now - dark_since)}s "
                     f"-- presence re-registered")
                dark_since = None
            if not runner_lock.heartbeat(agent, token, ttl=ttl):
                _say(f"[daemon] stand-down agent={agent}: lock lost to a successor -- exiting 0")
                return 0
            bus.register(card=card)
        runner_lock.release(agent, token)
        _say(f"[daemon] clean exit agent={agent} reason={reason} (lock released)")
        return 0
    except Exception as e:  # noqa: BLE001 -- the exit code IS the error contract
        _say(f"[daemon] FAULT agent={agent}: {type(e).__name__}: {e} -- exiting 1")
        return 1
    finally:
        try:
            runner_lock.release(agent, token)   # idempotent: only ever frees our own hold
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
