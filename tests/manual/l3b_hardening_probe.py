"""L3b-auto hardening proof: armed set PERSISTS in Redis (survives restart + shared), storm-disarm
persists, jitter doesn't break the flow. _bus_note mocked so no test notes hit the live bus."""
import os, ast, sys, time

# Root DERIVED from this file, never hardcoded: the literal pinned one machine's disk,
# so a copy of the repo anywhere else resolved every path under it to nothing.
import os as _os, pathlib as _pl
_here = _pl.Path(__file__).resolve()
ROOT = str(next((p for p in (_here, *_here.parents)
                 if (p / 'agent_cli.py').exists() and (p / 'core').is_dir()), _here.parent))
ast.parse(open(os.path.join(ROOT, "core/comm/launcher.py"), encoding="utf-8").read()); print("parse OK: launcher.py")

sys.path.insert(0, ROOT)
import core.comm.launcher as LM
from core.comm.launcher import Launcher, AgentSpec, AUTO_REVIVE_KEY, _bus_redis

r = _bus_redis()
for k in ("deepseek", "l3bh_probe"):
    r.srem(AUTO_REVIVE_KEY, k)

L = Launcher(); L._bus_note = lambda *a, **k: None

# arm persists to Redis
assert L.arm_revive("deepseek", True)["auto_revive"] is True
assert "deepseek" in r.smembers(AUTO_REVIVE_KEY), "arm must write to Redis"
print("[PASS] arm persists to Redis")

# a FRESH Launcher (simulates a UI/supervisor RESTART) still sees it
L2 = Launcher()
assert "deepseek" in L2._armed_set(), "armed state must survive a restart"
assert next(x for x in L2.registry() if x["agent_id"] == "deepseek")["auto_revive"] is True
print("[PASS] armed state survives a restart (persisted, read-through)")

# disarm persists
L.arm_revive("deepseek", False)
assert "deepseek" not in Launcher()._armed_set()
print("[PASS] disarm persists")

# storm-disarm persists to Redis (not just in-memory)
LM.RESTART_MAX_ATTEMPTS = 2; LM.RESTART_BACKOFF_BASE = 0.01; LM.AUTO_REVIVE_JITTER = 0
tag = aid = "l3bh_probe"
L._specs[tag] = AgentSpec(agent_id=aid, runtime="python_runner", description="t", command=["x"])
L._reload = lambda: None
L._set_armed(aid, True); L._auto_attempts.pop(aid, None); L._auto_last.pop(aid, None)
revives = []
L.revive = lambda t, reason="manual": (revives.append(t), {"ok": True})[1]
for _ in range(4):
    L._reviving.discard(aid)
    L._auto_revive_run(tag, aid, {"phase": "thinking", "stuck_seconds": 400})
assert len(revives) == 2, ("revive up to cap then stop", revives)
assert aid not in L._armed_set(), "storm-disarm must PERSIST (removed from the shared Redis set)"
print(f"[PASS] storm-disarm persists: {len(revives)} revives then disarmed in Redis")

# jitter applied, revive still fires (flow not broken)
LM.AUTO_REVIVE_JITTER = 0.1; LM.RESTART_MAX_ATTEMPTS = 5
L._set_armed(aid, True); L._auto_attempts.pop(aid, None); L._auto_last.pop(aid, None); revives.clear()
L._reviving.discard(aid)
t0 = time.time(); L._auto_revive_run(tag, aid, {"phase": "thinking", "stuck_seconds": 400}); dt = time.time() - t0
assert len(revives) == 1 and dt < 5, (revives, dt)
print(f"[PASS] jitter applied, revive still fires (dt={dt:.2f}s)")

for k in ("deepseek", "l3bh_probe"):
    r.srem(AUTO_REVIVE_KEY, k)
print("\nL3b-auto HARDENING VERIFIED.")
