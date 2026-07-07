"""L3b backend proof: revive() orchestration (kill -> free lock -> launch, in order, lock free at
launch time) and _restart() exponential backoff with a hard cap. No real processes spawned:
launch()/kill() are stubbed to record calls."""
import os, ast, sys, json, time

ROOT = r"E:/AI-Setup"
for f in ("core/comm/launcher.py", "core/comm/runner_lock.py"):
    ast.parse(open(os.path.join(ROOT, f), encoding="utf-8").read()); print("parse OK:", f)

sys.path.insert(0, ROOT)
import core.comm.launcher as LM
from core.comm.launcher import Launcher, AgentSpec, AgentProcess
from core.comm import runner_lock

# --- clear_if_pid: frees only the matching pid, never a different holder ---
A = "l3b_probe"
c = runner_lock._client()
c.set(runner_lock._key(A), json.dumps({"token": "t", "pid": 99999, "ts": "x"}), ex=20)
assert runner_lock.clear_if_pid(A, 12345) is False and runner_lock.holder(A), "must NOT clear a different pid"
assert runner_lock.clear_if_pid(A, 99999) is True and runner_lock.holder(A) is None, "must clear the matching pid"
print("[PASS] clear_if_pid: leaves a different holder, frees the matching pid")

# --- revive(): kill -> lock free -> launch, in that order ---
L = Launcher()
tag = "l3b_probe"; aid = "l3b_probe"
L._specs[tag] = AgentSpec(agent_id=aid, runtime="python_runner", description="t", command=["x"])
L._procs[aid] = AgentProcess(agent_id=aid, pid=99999, handle=None, status="running", started_at="")
# simulate a HARD kill: the lock lingers (finally didn't run)
c.set(runner_lock._key(aid), json.dumps({"token": "t", "pid": 99999, "ts": "x"}), ex=20)

calls = []
def fake_kill(t):
    calls.append(("kill", t)); L._procs[aid].status = "killed"; return {"ok": True}
def fake_launch(t, **k):
    calls.append(("launch", t, runner_lock.holder(aid))); return {"ok": True, "pid": 12345}
L.kill, L.launch = fake_kill, fake_launch

res = L.revive(tag)
assert [x[0] for x in calls] == ["kill", "launch"], calls
assert calls[1][2] is None, ("lock MUST be free when launch runs", calls[1][2])
assert res.get("killed_pid") == 99999 and res.get("revived") is True, res
print(f"[PASS] revive(): kill -> freed lock -> launch (killed_pid={res['killed_pid']}, lock free at launch)")

# --- _restart(): exponential backoff, hard cap, then stop (no more launches) ---
LM.RESTART_BACKOFF_BASE = 0.01; LM.RESTART_MAX_ATTEMPTS = 3; LM.RESTART_RESET_S = 300
launches = []
L.launch = lambda t, **k: (launches.append(t), {"ok": True})[1]
L._free_lock_for_relaunch = lambda a, p: None
for _ in range(5):
    L._restart(tag)
assert len(launches) == 3, ("must launch up to the cap then stop", launches)
print(f"[PASS] _restart(): {len(launches)} launches then capped at {LM.RESTART_MAX_ATTEMPTS} (storm stopped)")

# reset window: after RESET_S, the counter clears and restarts resume
L._restart_last[aid] = time.time() - (LM.RESTART_RESET_S + 1)
L._restart(tag)
assert len(launches) == 4, ("reset window must allow a fresh restart", launches)
print("[PASS] _restart(): reset window re-enables restarts after a healthy period")

c.delete(runner_lock._key(A)); c.delete(runner_lock._key(aid))
print("\nL3b BACKEND VERIFIED.")
