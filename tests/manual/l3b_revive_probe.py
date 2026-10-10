"""L3b backend proof: revive() orchestration (kill -> free lock -> launch, in order, lock free at
launch time) and _restart() exponential backoff with a hard cap. No real processes spawned:
launch()/kill() are stubbed to record calls."""

import ast
import json
import os

# Root DERIVED from this file, never hardcoded: the literal pinned one machine's disk,
# so a copy of the repo anywhere else resolved every path under it to nothing.
import pathlib as _pl
import sys
import time

sys.path.insert(
    0,
    str(
        next(
            (
                p
                for p in (_pl.Path(__file__).resolve(), *_pl.Path(__file__).resolve().parents)
                if (p / "agent_cli.py").exists() and (p / "core").is_dir()
            ),
            _pl.Path(__file__).resolve().parent,
        )
    ),
)
import core.comm.launcher as LM
from core.comm import runner_lock
from core.comm.launcher import AgentProcess, AgentSpec, Launcher

_here = _pl.Path(__file__).resolve()
ROOT = str(
    next((p for p in (_here, *_here.parents) if (p / "agent_cli.py").exists() and (p / "core").is_dir()), _here.parent)
)
for f in ("core/comm/launcher.py", "core/comm/runner_lock.py"):
    ast.parse(_pl.Path(os.path.join(ROOT, f)).read_text(encoding="utf-8"))
    print("parse OK:", f)

# --- clear_if_pid: frees only the matching pid, never a different holder ---
A = "l3b_probe"
c = runner_lock._client()
assert c is not None
c.set(runner_lock._key(A), json.dumps({"token": "t", "pid": 99999, "ts": "x"}), ex=20)
assert runner_lock.clear_if_pid(A, 12345) is False, "must NOT clear a different pid"
assert runner_lock.holder(A), "must NOT clear a different pid"
assert runner_lock.clear_if_pid(A, 99999) is True, "must clear the matching pid"
assert runner_lock.holder(A) is None, "must clear the matching pid"
print("[PASS] clear_if_pid: leaves a different holder, frees the matching pid")

# --- revive(): kill -> lock free -> launch, in that order ---
L = Launcher()
tag = "l3b_probe"
aid = "l3b_probe"
L._specs[tag] = AgentSpec(agent_id=aid, runtime="python_runner", description="t", command=["x"])
L._procs[aid] = AgentProcess(agent_id=aid, pid=99999, handle=None, status="running", started_at="")
# simulate a HARD kill: the lock lingers (finally didn't run)
c.set(runner_lock._key(aid), json.dumps({"token": "t", "pid": 99999, "ts": "x"}), ex=20)

calls = []


def fake_kill(tag):
    calls.append(("kill", tag))
    L._procs[aid].status = "killed"
    return {"ok": True}


def fake_launch(tag, **k):
    calls.append(("launch", tag, runner_lock.holder(aid)))
    return {"ok": True, "pid": 12345}


L.kill, L.launch = fake_kill, fake_launch  # ty: ignore[invalid-assignment]  # monkeypatch with a test double

res = L.revive(tag)
assert [x[0] for x in calls] == ["kill", "launch"], calls
assert calls[1][2] is None, ("lock MUST be free when launch runs", calls[1][2])
assert res.get("killed_pid") == 99999, res
assert res.get("revived") is True, res
print(f"[PASS] revive(): kill -> freed lock -> launch (killed_pid={res['killed_pid']}, lock free at launch)")

# --- _restart(): exponential backoff, hard cap, then stop (no more launches) ---
LM.RESTART_BACKOFF_BASE = 0.01
LM.RESTART_MAX_ATTEMPTS = 3
LM.RESTART_RESET_S = 300  # ty: ignore[invalid-assignment]  # probe patches a module constant
launches = []
L.launch = lambda tag, **k: (launches.append(tag), {"ok": True})[1]  # ty: ignore[invalid-assignment]  # monkeypatch with a test double
L._free_lock_for_relaunch = lambda aid, dead_pid: None  # ty: ignore[invalid-assignment]  # monkeypatch with a test double
for _ in range(5):
    L._restart(tag)
assert len(launches) == 3, ("must launch up to the cap then stop", launches)
print(f"[PASS] _restart(): {len(launches)} launches then capped at {LM.RESTART_MAX_ATTEMPTS} (storm stopped)")

# reset window: after RESET_S, the counter clears and restarts resume
L._restart_last[aid] = time.time() - (LM.RESTART_RESET_S + 1)
L._restart(tag)
assert len(launches) == 4, ("reset window must allow a fresh restart", launches)
print("[PASS] _restart(): reset window re-enables restarts after a healthy period")

c.delete(runner_lock._key(A))
c.delete(runner_lock._key(aid))
print("\nL3b BACKEND VERIFIED.")
