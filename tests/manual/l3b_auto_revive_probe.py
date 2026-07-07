"""L3b-auto proof: monitor auto-revives ARMED + wedged agents (opt-in), with a storm guard that
disarms after the cap. No real processes: revive() is stubbed."""
import os, ast, sys, json, time

ROOT = r"E:/AI-Setup"
ast.parse(open(os.path.join(ROOT, "core/comm/launcher.py"), encoding="utf-8").read()); print("parse OK: launcher.py")

sys.path.insert(0, ROOT)
import core.comm.launcher as LM
from core.comm.launcher import Launcher, AgentSpec, AgentProcess
from core.comm import liveness

LM.RESTART_MAX_ATTEMPTS = 3; LM.RESTART_BACKOFF_BASE = 0.05; LM.RESTART_RESET_S = 300

L = Launcher()
tag = aid = "l3ba_probe"
L._specs[tag] = AgentSpec(agent_id=aid, runtime="python_runner", description="t", command=["x"])
L._reload = lambda: None   # keep the synthetic spec (registry() would otherwise reload real specs over it)
L._procs[aid] = AgentProcess(agent_id=aid, pid=111, handle=None, status="running", started_at="")
c = liveness._client()

def set_worklive(phase, age):
    c.set(liveness.WORKLIVE_PREFIX + aid, json.dumps(
        {"phase": phase, "since_ts": time.time() - age, "beat_ts": time.time(), "turn": 1, "detail": "", "seq": 1}), ex=45)

revives = []
L.revive = lambda t, reason="manual": (revives.append((t, reason)), {"ok": True})[1]

# arm/disarm plumbing + registry reflects it
assert L.arm_revive(tag, True)["auto_revive"] is True
assert next(r for r in L.registry() if r["agent_id"] == aid)["auto_revive"] is True
print("[PASS] arm_revive + registry expose the armed flag")

# NOT wedged (fresh phase) -> no auto-revive even though armed
set_worklive("thinking", 5)
L._check_auto_revive(); time.sleep(0.2)
assert revives == [], ("armed but not wedged must NOT revive", revives)
print("[PASS] armed + NOT wedged -> no auto-revive (observe-only)")

# wedged past threshold -> auto-revive fires
set_worklive("thinking", 400)   # 400s > 300 default
L._reviving.discard(aid)
L._check_auto_revive(); time.sleep(0.25)
assert len(revives) == 1 and revives[0][1] == "auto-wedge", ("armed + wedged must auto-revive", revives)
print(f"[PASS] armed + wedged -> auto-revive fired ({revives[0]})")

# NOT armed -> no auto-revive even when wedged
L.arm_revive(tag, False); revives.clear()
L._reviving.discard(aid)
L._check_auto_revive(); time.sleep(0.2)
assert revives == [], ("disarmed must NOT auto-revive", revives)
print("[PASS] disarmed -> no auto-revive")

# storm guard: keeps reviving up to the cap, then DISARMS + escalates
revives.clear(); L._auto_attempts.pop(aid, None); L._auto_last.pop(aid, None); L._auto_revive.add(aid)
for _ in range(5):
    L._reviving.discard(aid)
    L._auto_revive_run(tag, aid, {"phase": "thinking", "stuck_seconds": 400})
assert len(revives) == LM.RESTART_MAX_ATTEMPTS, ("must revive up to the cap then stop", len(revives))
assert aid not in L._auto_revive, "must DISARM after the cap (break the loop)"
print(f"[PASS] storm guard: {len(revives)} auto-revives then DISARMED at cap {LM.RESTART_MAX_ATTEMPTS}")

c.delete(liveness.WORKLIVE_PREFIX + aid)
print("\nL3b-auto BACKEND VERIFIED.")
