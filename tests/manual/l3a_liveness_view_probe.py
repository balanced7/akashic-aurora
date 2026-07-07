"""L3a proof: observe-only wedge_view + launcher.registry() carries per-agent liveness."""
import os, ast, sys, time

ROOT = r"E:/AI-Setup"
for f in ("core/comm/liveness.py", "core/comm/launcher.py"):
    ast.parse(open(os.path.join(ROOT, f), encoding="utf-8").read()); print("parse OK:", f)

sys.path.insert(0, ROOT)
from core.comm import liveness
from core.comm.launcher import get_launcher

A = "l3a_probe"
c = liveness._client()
if c:
    c.delete(liveness.WORKLIVE_PREFIX + A)

assert liveness.wedge_view(A) is None
print("[PASS] no record -> None (fail-safe)")

wl = liveness.worklive(A)
wl.set("idle")
v = liveness.wedge_view(A, wedge_s=0)          # even at threshold 0...
assert v and v["wedged"] is False, v            # ...idle is never a wedge
print(f"[PASS] idle never wedged (thr=0): phase={v['phase']} wedged={v['wedged']}")

wl.set("thinking")
time.sleep(0.15)
hot = liveness.wedge_view(A, wedge_s=0.1)        # threshold BELOW time-in-phase -> wedged
cold = liveness.wedge_view(A, wedge_s=1000)      # threshold ABOVE time-in-phase -> not wedged
assert hot["wedged"] is True and cold["wedged"] is False, (hot, cold)
print(f"[PASS] thinking stuck={hot['stuck_seconds']}s -> wedged@0.1s=True, wedged@1000s=False (flag flips both ways)")

# registry() exposes liveness per agent
liveness.worklive("deepseek").set("reading", "somefile.py")
reg = get_launcher().registry()
entry = next((r for r in reg if r["agent_id"] == "deepseek"), None)
assert entry and "liveness" in entry, "registry entry must carry a liveness field"
assert entry["liveness"] and entry["liveness"]["phase"] == "reading", entry["liveness"]
print(f"[PASS] registry() carries liveness: {entry['liveness']}")

if c:
    for k in (A, "deepseek"):
        c.delete(liveness.WORKLIVE_PREFIX + k)
print("\nL3a VERIFIED.")
