"""revive -- the house's recovery reconciler (T382, the revive ladder's L2 core).

Daniil's doctrine sentence: "I want to be able to launch akashic aurora even
if nothing is running, from discord." And his safety requirement: safe to run
when everything is already up. So this is a RECONCILER, never a launcher:

    observe -> skip-if-healthy -> heal-only-the-dead -> verify, per rung,
    in dependency order (redis -> daemon -> gateway), stopping at any rung
    whose heal fails verification. Bare converge can kill NOTHING: the only
    levers on the default path are `docker start` (a documented no-op on a
    running container), exact scheduled-task starts, and detached daemon
    spawns that the house's own singleton locks absorb if they race. An
    all-skip run is a successful, boring run.

Single-flight: a lock file refuses concurrent converges. Every run prints
its confession -- what it SAW, what it SKIPPED, what it TOUCHED, what it
PROVED -- in lines the Discord gateway can relay in-channel verbatim.

Doors: `py scripts/revive.py --observe` (the dry run, = !status-deep),
`py scripts/revive.py` (converge), `--target <organ>` (one rung only).
The OS watchdog now nudges the owned gateway Scheduled Task directly. This
script remains the richer read/repair lever used by `!status-deep` and
`!revive`, and uses that same owned task when the gateway is proven absent.

decide() is PURE (observation in, plan out) and pinned in
tests/test_t382_revive.py; the I/O lives in observe()/_heal_step()/_verify().
"""
from __future__ import annotations

import json
import os
import re
import shutil
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
GATEWAY_TASK_NAME = os.environ.get(
    "AKASHIC_DISCORD_GATEWAY_TASK", "AkashicAurora-DiscordGateway"
)
DAEMON_AGENTS = ("deepseek", "kimi", "claude")   # the DaemonLock absorbs duplicates
# S1 (wake doctrine, 2026-09-03): each agent's daemon has a MODE. deepseek/kimi
# daemons spawn+supervise a runner; claude's daemon supervises WAKE LISTENERS
# (--manage-listener) -- there is no bifrost_runner_claude by design (Token
# Frugality), so planning --spawn-runner for claude would be the F13 wrong-script
# class, and expecting a claude runner would page a phantom death forever. The
# mode map keeps one rung with per-agent truth instead of a second roster.
DAEMON_MODE = {"deepseek": "--spawn-runner", "kimi": "--spawn-runner",
               "claude": "--manage-listener"}
# runner children exist only for spawn-runner daemons; observe()'s runner rung
# and count lines derive from THIS, never from DAEMON_AGENTS directly.
RUNNER_AGENTS = tuple(a for a in DAEMON_AGENTS
                      if DAEMON_MODE.get(a) == "--spawn-runner")
# `app` is FIRST because it is the deepest layer and the one this ladder was blind to
# until 2026-08-24: the MSIX package that HOSTS the conductor seat. On that day the
# ladder began at redis, so a dead Claude Desktop was not merely unhealed -- it was
# invisible, and !revive ran twice reporting that it ran. See core/fleet/app_package.py.
_ORDER = ("app", "redis", "daemon", "gateway")   # runners are the daemon's children:
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


def _cmdlines() -> Optional[str]:
    """Full python command lines (tasklist hides args; wmic-era fallback).

    Returns None when the process table could NOT BE READ -- a timeout, a shell failure,
    anything. That is not the same fact as "no processes are running", and this function
    used to spell them identically (both as ""). Downstream, the only consumer of the
    count is a SPAWNER, so an empty string meant every unreadable probe was heard as
    "everything is dead, start more" -- and the 25s CIM timeout gets likelier exactly as
    the machine comes under memory pressure. That is a positive feedback loop: pressure
    slows the probe, the silence reads as death, the cure adds pressure. It ran every 5
    minutes and put four concurrent gateways up before the 2026-08-26 exhaustion.

    An empty STRING still means a genuine zero -- the probe answered and found nothing.
    """
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" "
             "| ForEach-Object { '{0} {1}' -f $_.ProcessId, $_.CommandLine }"],
            capture_output=True, text=True, timeout=25, encoding="utf-8",
            errors="replace")
        if r.returncode != 0:
            return None          # the shell failed: we did not learn anything
        return r.stdout or ""
    except Exception:                                                   # noqa: BLE001
        return None              # timeout / spawn failure: unreadable, NOT empty


def _gateway_health(
    cmdlines: str,
    readiness_record: Optional[Dict[str, Any]],
    *,
    expected_world: str,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Join exact process cardinality to the process-owned readiness generation."""
    lines = [line for line in str(cmdlines or "").splitlines()
             if "bifrost_runner_discord.py" in line]
    count = len(lines)
    if count == 0:
        return {
            "healthy": False,
            "repairable": True,
            "readiness": False,
            "detail": "0 gateway process(es) -- proven absent",
        }
    if count > 1:
        return {
            "healthy": False,
            "repairable": False,
            "readiness": False,
            "detail": (
                f"{count} gateway process(es) -- DUPLICATE: default recovery refuses "
                "to add or kill a process"
            ),
        }

    match = re.match(r"^\s*(\d+)\s+", lines[0])
    if not match:
        return {
            "healthy": False,
            "repairable": False,
            "readiness": False,
            "detail": "1 gateway process, but its PID could not be attributed",
        }
    pid = int(match.group(1))
    from core.comm import gateway_readiness

    verdict = gateway_readiness.assess(
        readiness_record,
        live_pids={pid},
        expected_world=expected_world,
        now=now,
        ttl=gateway_readiness.READINESS_TTL,
    )
    return {
        **verdict,
        "repairable": bool(verdict.get("healthy")),
        "readiness": bool(verdict.get("healthy")),
        "pid": pid,
    }


def observe(include_app: bool = True) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if include_app:
        # Cheap probe: status only. The 629 MB block-map verification is part of the
        # HEAL, never of a probe that a scheduled task runs every few minutes.
        try:
            from core.fleet import app_package
            out["app"] = app_package.observe_app()
        except Exception as e:                                          # noqa: BLE001
            # A probe that cannot run must read as NOT healthy. An unreadable answer
            # reported as health is the defect this whole rung exists to end.
            out["app"] = {"healthy": False, "repairable": False, "pkg": None,
                          "detail": f"app probe failed ({type(e).__name__}: "
                                    f"{str(e)[:60]}) -- cannot prove healthy"}
    redis_client = None
    try:
        from core.comm.bus import Bus
        redis_client = Bus("revive-probe", promote=False)._client
        ok = bool(redis_client.ping())
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

    if cmds is None:
        # THE REFUSAL. Same discipline the app rung above already applies: a probe that
        # cannot run reads as NOT healthy AND NOT repairable, so decide() plans nothing
        # and unreachable_report names it. We cannot prove absence, so we do not "heal"
        # it -- spawning against an unreadable process table is how duplicates breed.
        blind = ("process table unreadable (probe timed out or failed) -- cannot prove "
                 "absence, so this rung REFUSES to spawn; re-run when the host is calmer")
        for organ in ("daemon", "runners", "gateway"):
            out[organ] = {"healthy": False, "repairable": False, "detail": blind,
                          "dead": []}
        return out

    dead_daemons = [a for a in DAEMON_AGENTS if not _live(a, "bifrost_daemon.py")]
    dead_runners = [a for a in RUNNER_AGENTS if not _live(a, "bifrost_runner_")]
    out["daemon"] = {
        "healthy": not dead_daemons,
        "detail": (f"all {len(DAEMON_AGENTS)} daemon(s) alive: {', '.join(DAEMON_AGENTS)}"
                   if not dead_daemons else
                   f"DOWN: {', '.join(dead_daemons)} "
                   f"(alive: {', '.join(a for a in DAEMON_AGENTS if a not in dead_daemons) or 'none'})"),
        "repairable": True,      # the probe ANSWERED -- a zero here is a real absence
        "dead": dead_daemons}
    out["runners"] = {
        "healthy": not dead_runners,
        "detail": (f"all {len(RUNNER_AGENTS)} runner(s) alive: {', '.join(RUNNER_AGENTS)}"
                   if not dead_runners else
                   f"DOWN: {', '.join(dead_runners)} (daemon's children -- healed by "
                   f"the daemon rung, verified here)"),
        "repairable": True,
        "dead": dead_runners}
    # Presence is necessary, never sufficient. The readiness generation is stamped
    # by Discord's own asyncio loop and names its PID + world, so a live-but-stale
    # socket or an old generation cannot borrow health from a command-line match.
    try:
        from core.comm import gateway_readiness
        readiness_record = gateway_readiness.read(client=redis_client)
    except Exception:                                                   # noqa: BLE001
        readiness_record = None
    try:
        from core.world import current as current_world
        expected_world = current_world().name
    except Exception:                                                   # noqa: BLE001
        expected_world = str(os.environ.get("AKASHIC_WORLD") or "prod")
    out["gateway"] = _gateway_health(
        cmds,
        readiness_record,
        expected_world=expected_world,
    )
    return out


# -------------------------------------------------------------------- decide
_DEPS = {"app": (), "redis": (), "daemon": ("redis",), "gateway": ()}


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
        if row.get("repairable") is False:
            # A rung that told us it CANNOT be proven broken is never "healed". This is
            # the app rung's discipline generalised to every organ: an unknown bad state
            # is not the state we know how to fix. Absent key == repairable (a rung that
            # never speaks to the question keeps its old behaviour).
            continue
        if organ == "app":
            # ONLY a repairable state earns a plan. An app that is down for a reason
            # this rung has no lever for is left ALONE and named in the unreachable
            # report -- we never treat an unknown bad state as the one we can fix.
            if not row.get("repairable"):
                continue
            plan.append({"organ": "app", "kind": "msix-repair",
                         "pkg": row.get("pkg")})
        elif organ == "redis":
            plan.append({"organ": "redis",
                         "cmd": ["docker", "start", REDIS_CONTAINER],
                         "kind": "docker-start"})
        elif organ == "daemon":
            # HEAL-ONLY-THE-DEAD (Sol audit R2): observed carries `dead` per agent
            # (observe() populates it from _live()). Looping over every DAEMON_AGENTS
            # member planned BOTH launches when ONE was dead -- a missing kimi
            # spawned a DUPLICATE deepseek daemon, relying on a downstream lock
            # refusal instead of the module's own promise. Plan exactly the dead
            # agents. Absent `dead` (legacy observation shape) falls back to all
            # agents, preserving the old behaviour for callers that never speak to
            # the per-agent question.
            dead_agents = row.get("dead") or list(DAEMON_AGENTS)
            for agent in dead_agents:
                if agent not in DAEMON_AGENTS:
                    continue          # never plan an agent this rung doesn't own
                # S1: the mode map, not a hardcoded flag -- claude's daemon is a
                # listener-manager, and --spawn-runner for it would be F13 again.
                mode = DAEMON_MODE.get(agent, "--spawn-runner")
                cmd = [sys.executable,
                       os.path.join(ROOT, "scripts", "bifrost_daemon.py"),
                       "--agent", agent, mode]
                if mode == "--spawn-runner":
                    # relaunch_must_carry_the_lane_env (page-proven): the daemon's
                    # lane default is None, so a resurrected daemon without this
                    # flag spawns runners whose cursors diverge from the drilled
                    # work-lane config -- the insta-fire wake-loop class returns.
                    # The SunshineFleet task carries it; the necromancer must too.
                    cmd += ["--runner-consume-lane", "work"]
                plan.append({"organ": "daemon", "cmd": cmd,
                             "kind": "detached-spawn", "agent": agent})
        elif organ == "gateway":
            if os.name == "nt":
                plan.append({
                    "organ": "gateway",
                    "cmd": [shutil.which("schtasks.exe") or "schtasks.exe",
                            "/Run", "/TN", GATEWAY_TASK_NAME],
                    "kind": "scheduled-task-start",
                })
            else:
                plan.append({"organ": "gateway",
                             "cmd": [sys.executable,
                                     os.path.join(ROOT, "scripts",
                                                  "bifrost_runner_discord.py")],
                             "kind": "detached-spawn"})
    return plan


def unreachable_report(observed: Dict[str, Dict[str, Any]],
                       plan: List[Dict[str, Any]],
                       target: Optional[str] = None) -> List[str]:
    """Name every organ that is DOWN and that this run will NOT heal, and say why.

    THE SENTENCE THIS EXISTS TO PRODUCE. On 2026-08-24 Daniil ran !revive twice while
    the conductor was dead; the ladder had no rung at the application layer, saw
    nothing wrong in the three rungs it owned, and reported that the lever ran. A
    lever that recovered nothing must never render as "touched NOTHING (a boring run
    is a successful run)" -- boring and blind produce the same silence, and only one
    of them is good news.

    So an organ that is down and unplanned is reported with its REASON: deferred
    behind a dependency, owned by another rung, or -- the 12:05 case -- outside
    anything this ladder can reach.
    """
    planned = {s.get("organ") for s in plan}
    lines: List[str] = []
    for organ in _ORDER + ("runners",):
        if target and organ != target:
            continue
        row = observed.get(organ) or {}
        if row.get("healthy") or organ in planned:
            continue
        deps_down = [d for d in _DEPS.get(organ, ())
                     if not (observed.get(d) or {}).get("healthy")]
        if deps_down:
            lines.append(f"{organ}: DOWN, deferred -- dependency {', '.join(deps_down)} "
                         f"is down; the next converge plans further")
        elif organ == "runners":
            lines.append(f"{organ}: DOWN -- the daemon owns its children; the daemon "
                         f"rung heals them")
        else:
            lines.append(f"{organ}: DOWN and no rung here reaches it -- "
                         f"{row.get('detail')}. The fault is below this ladder.")
    return lines


# ---------------------------------------------------------------------- heal
def _heal_app(step: Dict[str, Any]) -> bool:
    """Sol's 2026-08-24 repair, as a rung: prove the payload, clear ONLY the stale
    status bit, then prove recovery BY LAUNCHING -- never by re-reading the field we
    just wrote.

    Refusal-first: `clear_refusals` is the door. Missing evidence refuses. A refusal
    is written into the step's receipt so the confession Discord relays says WHY, not
    just that something did not happen."""
    from core.fleet import app_package as ap

    receipt: List[str] = []
    step["receipt"] = receipt
    pkg = step.get("pkg") or ap.query_package()
    elevated = ap.is_elevated()

    loc = (pkg or {}).get("install_location") or ""
    receipt.append(f"verifying payload at {loc or '<unknown>'} (this reads the whole "
                   f"package; it is the expensive half and it is the point)")
    proof = ap.verify_payload(loc)
    receipt.append(ap.proof_receipt(proof))

    refusals = ap.clear_refusals(pkg, proof, elevated=elevated)
    if refusals:
        receipt.append(f"REFUSED to clear ({len(refusals)} reason(s)):")
        receipt.extend(f"  - {r}" for r in refusals)
        return False

    ok, detail = ap.clear_modified_status(str(pkg.get("full_name")))
    receipt.append(f"ClearPackageStatus(Modified): {'ok' if ok else 'FAILED'} -- {detail}")
    if not ok:
        return False

    recovered, why = ap.verify_recovered(str(pkg.get("full_name")))
    receipt.append(f"PROOF (a launch, not a status read): {why}")
    return recovered


def _heal_step(step: Dict[str, Any]) -> bool:
    kind = step.get("kind")
    try:
        if kind == "msix-repair":
            return _heal_app(step)
        if kind == "docker-start":
            r = subprocess.run(step["cmd"], capture_output=True, text=True,
                               timeout=60)
            return r.returncode == 0
        if kind == "scheduled-task-start":
            r = subprocess.run(step["cmd"], capture_output=True, text=True,
                               timeout=20)
            step["receipt"] = [
                line for line in ((r.stdout or "") + "\n" + (r.stderr or "")).splitlines()
                if line.strip()
            ][:8]
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
        row = observe().get(organ) or {}
        if row.get("healthy") and (
            organ != "gateway" or row.get("readiness") is True
        ):
            return True
        time.sleep(2.0)
    return False


# ------------------------------------------------------------------ converge
def _take_lock() -> None:
    # ATOMIC single-flight (Sol audit R4): the old shape was
    # `if os.path.exists(LOCK_PATH): <check age>` then a separate `open(LOCK_PATH,
    # "w")` -- a check-then-write TOCTOU race. Two simultaneous phone/watchdog
    # converges could BOTH pass the exists() check (neither file present yet) and
    # both "acquire". The only way to make the race impossible is an atomic create:
    # O_CREAT|O_EXCL fails for exactly one of two contenders no matter how they
    # interleave, because the OS makes existence-and-creation ONE step.
    #
    # We keep the TTL discipline: a stale lock (older than LOCK_TTL_S) is removed
    # and re-taken, so a crashed converger never wedges the lever forever. The
    # exists()->getmtime probe here is ONLY for detecting expiry, never for
    # acquiring -- acquisition is the O_EXCL open below.
    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    try:
        # Atomic create-and-write: succeeds iff the file did NOT already exist.
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        age = time.time() - os.path.getmtime(LOCK_PATH)
        if age < LOCK_TTL_S:
            try:
                holder = open(LOCK_PATH, encoding="utf-8").read().strip()
            except OSError:
                holder = "?"
            raise ReviveLocked(
                f"revive already in progress (holder pid {holder}, "
                f"{age:.0f}s old) -- follow its confession; the lock "
                f"expires in {LOCK_TTL_S - age:.0f}s")
        # Stale lock: a prior converger crashed before dropping. Reclaim it
        # (remove + retry the atomic create once).
        try:
            os.remove(LOCK_PATH)
        except OSError:
            pass
        try:
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            raise ReviveLocked(
                "revive already in progress (a concurrent converger re-took the "
                "lock before this one could reclaim the stale holder)")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
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
    for organ in ("app", "redis", "daemon", "runners", "gateway"):
        row = observed.get(organ) or {}
        mark = "OK  " if row.get("healthy") else "DEAD"
        say(f"[revive] SAW {mark} {organ}: {row.get('detail')}")
    plan = decide(observed, target=target)
    unreachable = unreachable_report(observed, plan, target=target)
    report: Dict[str, Any] = {"observed": observed, "plan": plan,
                              "healed": [], "stopped_at": None,
                              "unreachable": unreachable}
    if observe_only:
        say(f"[revive] observe-only: {len(plan)} rung(s) would heal")
        for line in unreachable:
            say(f"[revive] UNREACHED {line}")
        return report
    if not plan:
        # A boring run and a blind run produce the same silence; only one of them is
        # good news. So say WHICH, always, and never claim health for an organ this
        # ladder merely cannot see (2026-08-24).
        if unreachable:
            say(f"[revive] recovered NOTHING -- {len(unreachable)} organ(s) down that "
                f"this run will not heal:")
            for line in unreachable:
                say(f"[revive]   {line}")
        else:
            say("[revive] all rungs healthy -- touched NOTHING "
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
            for line in step.get("receipt") or ():
                say(f"[revive]   {line}")
            if ok and organ not in healed_organs:
                healed_organs.append(organ)
            if not ok:
                # `app` has no dependents, so a refusal there must NOT block the bus
                # rungs. Stopping the whole ladder on an app refusal would have made
                # 2026-08-24 worse, not better: a package this rung declines to touch
                # would have blocked redis/daemon recovery too.
                if organ == "app":
                    report.setdefault("refused", []).append(organ)
                    say(f"[revive] {organ} not repaired -- see its receipt above; "
                        f"continuing (nothing downstream depends on it)")
                    continue
                report["stopped_at"] = organ
                say(f"[revive] STOP: {organ} heal failed -- nothing "
                    f"downstream attempted; fix this rung and re-run")
                return report
        for organ in healed_organs:
            if organ == "app":
                # Already proven by a LAUNCH inside _heal_app. Re-observing here would
                # re-read the status field we just wrote -- asking the gauge how it is
                # feeling, which is precisely how a dead seat got certified alive.
                report["healed"].append({"organ": organ, "verified": True})
                say(f"[revive] PROVE {organ}: proven by launch (see receipt above)")
                continue
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
                    choices=["app", "redis", "daemon", "gateway"],
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
