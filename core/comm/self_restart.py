"""self_restart (A1) -- a runner that knows it is stale restarts itself.

THE WASTE THIS CLOSES, measured 2026-07-28: every fix took HOURS to reach the
processes that needed it. The fleet ran 29+ commits behind while its own fixes
landed in git; a census deliverable was destroyed a second time by a bug already
fixed; a feature was announced live and both peer probes still exercised the old
code. T114 stamps what a process runs; T116 lets the doctor see staleness from
outside; this module is the remediation half -- the process acts on its own stamp.

THE CEREMONY, between turns only:
    reason = should_restart(stamped_sha=..., head_sha=..., commits_behind=...,
                            uptime_s=..., in_flight=False)
    if reason and respawn_self():
        <log loud, set worklive phase 'restarting', return from the main loop>

The fresh process starts with the SAME argv and environment (same seat, same
--session, same lane env -- dropping the lane env once cost a 6.5h stall), takes
the runner lock at a higher generation, and the old process stands down through
the singleton machinery already trusted for crash takeover. Planned succession
is unplanned succession minus the surprise.

FAIL DIRECTION IS KEEP-RUNNING. A restart fires only on PROVEN staleness:
stamp present, HEAD known, commit count positive, cooldown passed, nothing in
flight. Unknown anything -> stay up. A false restart costs a turn and a warm
cache; a missed restart costs only what today already cost, and the doctor's
STALE-CODE line keeps saying it either way -- nothing is hidden by declining.

Dials: AKASHIC_SELF_RESTART=0 (off), AKASHIC_SELF_RESTART_MIN_BEHIND (default 3),
AKASHIC_SELF_RESTART_MIN_UPTIME_S (default 900 -- the anti-thrash floor: a
restart that re-triggers on boot would flap forever on a busy repo).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import zlib
from typing import Any, Dict, List, Optional

_PROC_START = time.time()

# Fleet-blackout smoothing: when a busy repo makes every long-lived organ stale
# at once, a naive rotation would have the daemon + gateway + UI all respawn in
# the same instant and black the fleet for the spawn window. Each organ derives
# a DETERMINISTIC per-organ delay so their rotations spread across the window
# instead of stacking. Deterministic is the whole point: every process computing
# the same organ's delay must AGREE, so the smoothing cannot ride Python's
# builtin hash() -- that is randomised per process (PYTHONHASHSEED; the tree's
# own law at control_channel.py:66), and two processes would then disagree about
# the same organ's delay. crc32 is the same deterministic primitive port_for()
# already uses for the control-plane port map.
_JITTER_WINDOW_S = 120.0


def rotation_jitter_s(organ: str) -> float:
    """A deterministic per-organ rotation delay in [0, 120)s, pure in `organ`.

    Fleet-blackout smoothing (t376 reconciliation rule 2): spread the planned
    rotations of the daemon / gateway / UI (and any future organ) so a
    single commit that stales all of them does not rotate them in one stack.
    Pure function, crc32-keyed, deterministic across processes and restarts."""
    try:
        return float(zlib.crc32(str(organ).encode("utf-8")) % int(_JITTER_WINDOW_S))
    except Exception:
        return 0.0


def _truthy(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() not in ("0", "false", "no", "off", "")


def _min_behind() -> int:
    try:
        return max(1, int(os.environ.get("AKASHIC_SELF_RESTART_MIN_BEHIND", "3")))
    except Exception:
        return 3


def _min_uptime_s() -> float:
    try:
        return max(60.0, float(os.environ.get("AKASHIC_SELF_RESTART_MIN_UPTIME_S", "900")))
    except Exception:
        return 900.0


def uptime_s() -> float:
    return time.time() - _PROC_START


def should_restart(*, stamped_sha: str, head_sha: str, commits_behind: int,
                   uptime_s: float, in_flight: bool,
                   jitter_s: float = 0.0) -> Optional[str]:
    """A reason string when the ceremony should fire, else None.

    Pure decision core -- every input is passed in so pins never need a repo,
    a clock, or a git. The reason NAMES stamp/head/count because a restart
    nobody can explain is a crash with better manners.

    `jitter_s` is the per-organ fleet-blackout delay (rotation_jitter_s): it
    EXTENDS the anti-thrash floor so organs rotate at spread instants rather
    than all at once. Default 0.0 preserves the runner's existing behaviour
    (runners already break-before-make on a serialized lock and carry no
    fleet-blackout role)."""
    try:
        if not _truthy("AKASHIC_SELF_RESTART", True):
            return None
        if in_flight:
            return None                    # the turn boundary IS the safe point
        stamped = str(stamped_sha or "").strip()
        head = str(head_sha or "").strip()
        if not stamped or not head or stamped == head:
            return None                    # unknown or current: keep running
        try:
            behind = int(commits_behind)
        except Exception:
            return None
        if behind < _min_behind():
            return None                    # differing stamp alone is UNPROVEN age
        if float(uptime_s) < _min_uptime_s() + float(jitter_s):
            return None                    # anti-thrash cooldown + fleet-blackout spread
        return (f"stale-code self-restart: running {stamped[:12]}, HEAD is "
                f"{head[:12]}, {behind} commit(s) behind; uptime "
                f"{int(uptime_s)}s >= floor, idle at turn boundary")
    except Exception:
        return None                        # P8: this runs every turn, everywhere


# P9, THE FROZEN-HEAD TRAP (caught during wiring, before any fence):
# runtime_age.head_sha() caches per process -- right for the doctor's fresh probe
# children, FATAL for a long-lived runner, whose HEAD would freeze at its own boot
# value and the ceremony would never fire. The self-restart feature would itself be
# the day's disease: an instrument frozen at its own birth. Short-TTL re-resolve.
_HEAD_CACHE: Dict[str, Any] = {"sha": "", "at": 0.0}
_HEAD_TTL_S = 60.0


def _resolve_head_fresh() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"],
                           cwd=os.path.dirname(os.path.dirname(
                               os.path.dirname(os.path.abspath(__file__)))),
                           capture_output=True, text=True, timeout=5,
                           stdin=subprocess.DEVNULL, close_fds=True)
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def fresh_head_sha() -> str:
    """HEAD, at most _HEAD_TTL_S old -- so a runner that lives for days keeps
    seeing the repo move underneath it."""
    now = time.time()
    if now - float(_HEAD_CACHE.get("at", 0)) > _HEAD_TTL_S or not _HEAD_CACHE.get("sha"):
        _HEAD_CACHE["sha"] = _resolve_head_fresh()
        _HEAD_CACHE["at"] = now
    return str(_HEAD_CACHE.get("sha") or "")


def gather(agent: str) -> Dict[str, Any]:
    """The live inputs for should_restart, best-effort. Reads the process's OWN
    stamp (this import IS the running code) and a FRESH head (P9). Any hole ->
    empty strings, which the decision core reads as keep-running."""
    out = {"stamped_sha": "", "head_sha": "", "commits_behind": 0}
    try:
        from core.comm import liveness
        out["stamped_sha"] = liveness._safe_code_sha()
        out["head_sha"] = fresh_head_sha()
        if out["stamped_sha"] and out["head_sha"] and out["stamped_sha"] != out["head_sha"]:
            r = subprocess.run(["git", "rev-list", "--count",
                                f"{out['stamped_sha']}..{out['head_sha']}"],
                               cwd=os.path.dirname(os.path.dirname(
                                   os.path.dirname(os.path.abspath(__file__)))),
                               capture_output=True, text=True, timeout=10,
                               stdin=subprocess.DEVNULL, close_fds=True)
            if r.returncode == 0:
                out["commits_behind"] = int((r.stdout or "0").strip() or 0)
    except Exception:
        pass
    return out


def respawn_self(argv: Optional[List[str]] = None) -> bool:
    """Spawn a fresh copy of this process: same interpreter, same argv, INHERITED
    environment (the lane env must survive -- dropping it once cost a 6.5h lane
    stall). Detached + windowless on Windows, same pattern as launcher.py. The
    caller stands down afterwards; the runner lock's generation fencing hands
    the seat over exactly as it would after a crash."""
    try:
        args = [sys.executable] + list(argv if argv is not None else sys.argv)
        flags = 0
        if sys.platform == "win32":
            flags = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                     | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
        p = subprocess.Popen(args, env=dict(os.environ), close_fds=True,
                             creationflags=flags,
                             stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        return bool(getattr(p, "pid", 0))
    except Exception:
        return False


def maybe_self_restart(agent: str, *, in_flight: bool = False) -> Optional[str]:
    """The one-call integration point for runner turn boundaries. Returns the
    reason if a respawn was LAUNCHED (caller must then stand down cleanly),
    else None. Never raises.

    Feeds the organ's deterministic fleet-blackout jitter (rotation_jitter_s)
    into the decision core so a busy repo that stales every organ at once
    spreads their rotations instead of stacking them (t376 reconciliation
    rule 2). The organ name is the agent id: distinct seats/organ-kinds get
    distinct crc32-derived delays in [0,120)s."""
    try:
        facts = gather(agent)
        reason = should_restart(stamped_sha=facts["stamped_sha"],
                                head_sha=facts["head_sha"],
                                commits_behind=facts["commits_behind"],
                                uptime_s=uptime_s(), in_flight=in_flight,
                                jitter_s=rotation_jitter_s(agent))
        if not reason:
            return None
        if not respawn_self():
            return None                    # spawn failed -> keep running, stay loud
        try:
            from core.comm import liveness
            liveness.worklive(agent).set("restarting", detail=reason[:100])
        except Exception:
            pass
        print(f"[self-restart] {agent}: {reason} -- fresh process launched; "
              f"standing down via runner-lock takeover", flush=True)
        return reason
    except Exception:
        return None
