"""revive -- the house's recovery reconciler (T382, the revive ladder's L2 core).

Daniil's doctrine sentence: "I want to be able to launch akashic aurora even
if nothing is running, from discord." And his safety requirement: safe to run
when everything is already up. So this is a RECONCILER, never a launcher:

    observe -> skip-if-healthy -> heal-only-the-dead -> verify, per rung,
    in dependency order (redis -> daemon -> gateway), stopping at any rung
    whose heal fails verification. Bare converge can kill NOTHING: the only
    levers on the default path are `docker start` (a documented no-op on a
    running container) and detached spawns that the house's own singleton
    locks absorb if they race (DaemonLock twin-refusal, runner lock
    contest, S3a relay dedupe). An all-skip run is a successful, boring run.

Single-flight: a lock file refuses concurrent converges. Every run prints
its confession -- what it SAW, what it SKIPPED, what it TOUCHED, what it
PROVED -- in lines the Discord gateway can relay in-channel verbatim.

Doors: `py scripts/revive.py --observe` (the dry run, = !status-deep),
`py scripts/revive.py` (converge), `--target <organ>` (one rung only).
The same script IS the OS watchdog: a scheduled task running
`--target gateway` every few minutes is L1's supervisor -- one mechanism,
two duties.

decide() is PURE (observation in, plan out) and pinned in
tests/test_t382_revive.py; the I/O lives in observe()/_heal_step()/_verify().
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

LOCK_PATH = os.path.join(ROOT, "state", "revive.lock")
LOCK_TTL_S = 300.0
REDIS_CONTAINER = "akashic-redis"
DAEMON_AGENTS = ("deepseek", "kimi")      # one daemon per runner agent; the
                                          # DaemonLock absorbs duplicates
_ORDER = ("redis", "daemon", "gateway")   # runners are the daemon's children:
                                          # it spawns them; we verify, not heal


class ReviveLocked(RuntimeError):
    """A converge is already in progress -- follow ITS confession instead."""


# ------------------------------------------------------------------- observe
def _procs() -> List[str]:
    try:
        r = subprocess.run(["tasklist", "/FO", "CSV", "/V"], capture_output=True,
                           text=True, timeout=20, encoding="utf-8",
                           errors="replace")
        return (r.stdout or "").splitlines()
    except Exception:                                                   # noqa: BLE001
        return []


def _cmdlines() -> str:
    """Full python command lines (tasklist hides args; wmic-era fallback)."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" "
             "| Select-Object -ExpandProperty CommandLine"],
            capture_output=True, text=True, timeout=25, encoding="utf-8",
            errors="replace")
        return r.stdout or ""
    except Exception:                                                   # noqa: BLE001
        return ""


def observe() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    try:
        from core.comm.bus import Bus
        ok = bool(Bus("revive-probe", promote=False)._client.ping())
        out["redis"] = {"healthy": ok, "detail": "ping ok" if ok else "no ping"}
    except Exception as e:                                              # noqa: BLE001
        out["redis"] = {"healthy": False,
                        "detail": f"{type(e).__name__}: {str(e)[:80]}"}
    cmds = _cmdlines()
    # PER AGENT, never in aggregate (drill 2026-08-24). Counting processes asked
    # "is anything alive?" when the only useful question is "is EVERY seat alive?" --
    # so one surviving daemon reported the whole rung healthy and PROVE confirmed a
    # heal that never happened. And counting SCRIPT names could not distinguish
    # agents at all: every runner agent runs bifrost_runner_deepseek.py, so
    # `bifrost_runner_kimi` matched nothing ever while `bifrost_runner_deepseek`
    # matched both. The discriminator is `--agent <name>`, which is the only place
    # a process states which seat it IS.
    def _live(pattern_agent: str, script: str) -> bool:
        return any(script in ln and f"--agent {pattern_agent}" in ln
                   for ln in cmds.splitlines())

    dead_daemons = [a for a in DAEMON_AGENTS if not _live(a, "bifrost_daemon.py")]
    dead_runners = [a for a in DAEMON_AGENTS if not _live(a, "bifrost_runner_")]
    gateway_n = cmds.count("bifrost_runner_discord.py")
    out["daemon"] = {
        "healthy": not dead_daemons,
        "detail": (f"all {len(DAEMON_AGENTS)} daemon(s) alive: {', '.join(DAEMON_AGENTS)}"
                   if not dead_daemons else
                   f"DOWN: {', '.join(dead_daemons)} "
                   f"(alive: {', '.join(a for a in DAEMON_AGENTS if a not in dead_daemons) or 'none'})"),
        "dead": dead_daemons}
    out["runners"] = {
        "healthy": not dead_runners,
        "detail": (f"all {len(DAEMON_AGENTS)} runner(s) alive: {', '.join(DAEMON_AGENTS)}"
                   if not dead_runners else
                   f"DOWN: {', '.join(dead_runners)} (daemon's children -- healed by "
                   f"the daemon rung, verified here)"),
        "dead": dead_runners}
    out["gateway"] = {"healthy": gateway_n > 0,
                      "detail": f"{gateway_n} gateway process(es)"}
    return out


# -------------------------------------------------------------------- decide
_DEPS = {"redis": (), "daemon": ("redis",), "gateway": ()}


def decide(observed: Dict[str, Dict[str, Any]],
           target: Optional[str] = None) -> List[Dict[str, Any]]:
    """PURE: the heal plan for this observation. Healthy rungs are skipped;
    a rung whose dependency is unhealthy is DEFERRED (the next converge sees
    a healthier world and plans further). Runners are never healed directly
    -- the daemon owns its children."""
    plan: List[Dict[str, Any]] = []
    for organ in _ORDER:
        if target and organ != target:
            continue
        row = observed.get(organ) or {}
        if row.get("healthy"):
            continue
        if any(not (observed.get(d) or {}).get("healthy") for d in _DEPS[organ]):
            continue                       # deferred: dependency is dead
        if organ == "redis":
            plan.append({"organ": "redis",
                         "cmd": ["docker", "start", REDIS_CONTAINER],
                         "kind": "docker-start"})
        elif organ == "daemon":
            for agent in DAEMON_AGENTS:
                plan.append({"organ": "daemon",
                             "cmd": [sys.executable,
                                     os.path.join(ROOT, "scripts",
                                                  "bifrost_daemon.py"),
                                     "--agent", agent, "--spawn-runner"],
                             "kind": "detached-spawn", "agent": agent})
        elif organ == "gateway":
            plan.append({"organ": "gateway",
                         "cmd": [sys.executable,
                                 os.path.join(ROOT, "scripts",
                                              "bifrost_runner_discord.py")],
                         "kind": "detached-spawn"})
    return plan


# ---------------------------------------------------------------------- heal
def _heal_step(step: Dict[str, Any]) -> bool:
    kind = step.get("kind")
    try:
        if kind == "docker-start":
            r = subprocess.run(step["cmd"], capture_output=True, text=True,
                               timeout=60)
            return r.returncode == 0
        if kind == "detached-spawn":
            os.makedirs(os.path.join(ROOT, "state", "logs"), exist_ok=True)
            log = open(os.path.join(
                ROOT, "state", "logs",
                f"revive-{step['organ']}-{int(time.time())}.log"),
                "a", encoding="utf-8")
            flags = 0x00000008 | 0x00000200      # DETACHED | NEW_PROCESS_GROUP
            env = dict(os.environ)
            env.setdefault("BIFROST_CONSUME_LANE", "work")
            subprocess.Popen(step["cmd"], stdout=log, stderr=log, cwd=ROOT,
                             creationflags=flags, env=env)
            return True
    except Exception:                                                   # noqa: BLE001
        return False
    return False


def _verify(organ: str, deadline_s: float = 25.0) -> bool:
    end = time.time() + deadline_s
    while time.time() < end:
        if (observe().get(organ) or {}).get("healthy"):
            return True
        time.sleep(2.0)
    return False


# ------------------------------------------------------------------ converge
def _take_lock() -> None:
    try:
        if os.path.exists(LOCK_PATH):
            age = time.time() - os.path.getmtime(LOCK_PATH)
            if age < LOCK_TTL_S:
                holder = open(LOCK_PATH, encoding="utf-8").read().strip()
                raise ReviveLocked(
                    f"revive already in progress (holder pid {holder}, "
                    f"{age:.0f}s old) -- follow its confession; the lock "
                    f"expires in {LOCK_TTL_S - age:.0f}s")
    except ReviveLocked:
        raise
    except Exception:                                                   # noqa: BLE001
        pass
    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    with open(LOCK_PATH, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))


def _drop_lock() -> None:
    try:
        os.remove(LOCK_PATH)
    except OSError:
        pass


def converge(target: Optional[str] = None,
             observe_only: bool = False) -> Dict[str, Any]:
    say = lambda s: print(s, flush=True)                     # noqa: E731
    observed = observe()
    for organ in ("redis", "daemon", "runners", "gateway"):
        row = observed.get(organ) or {}
        mark = "OK  " if row.get("healthy") else "DEAD"
        say(f"[revive] SAW {mark} {organ}: {row.get('detail')}")
    plan = decide(observed, target=target)
    report: Dict[str, Any] = {"observed": observed, "plan": plan,
                              "healed": [], "stopped_at": None}
    if observe_only:
        say(f"[revive] observe-only: {len(plan)} rung(s) would heal")
        return report
    if not plan:
        say("[revive] all rungs healthy or deferred -- touched NOTHING "
            "(a boring run is a successful run)")
        return report
    _take_lock()
    try:
        healed_organs = []
        for step in plan:
            organ = step["organ"]
            say(f"[revive] HEAL {organ}: {step['kind']} "
                f"{step.get('agent', '')}".rstrip())
            ok = _heal_step(step)
            if ok and organ not in healed_organs:
                healed_organs.append(organ)
            if not ok:
                report["stopped_at"] = organ
                say(f"[revive] STOP: {organ} heal failed -- nothing "
                    f"downstream attempted; fix this rung and re-run")
                return report
        for organ in healed_organs:
            proved = _verify(organ)
            report["healed"].append({"organ": organ, "verified": proved})
            verdict = ("verified alive" if proved else
                       "NOT verified in time -- inspect its log in state/logs/")
            say(f"[revive] PROVE {organ}: {verdict}")
    finally:
        _drop_lock()
    return report


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="the house's recovery reconciler")
    ap.add_argument("--observe", action="store_true",
                    help="dry run: report health, heal nothing (=!status-deep)")
    ap.add_argument("--target", default=None,
                    choices=["redis", "daemon", "gateway"],
                    help="converge one rung only")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        report = converge(target=a.target, observe_only=a.observe)
    except ReviveLocked as e:
        print(f"[revive] REFUSED: {e}", flush=True)
        return 3
    if a.json:
        print(json.dumps(report, default=str))
    if report.get("stopped_at"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
