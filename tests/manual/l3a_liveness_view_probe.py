"""L3a proof: observe-only wedge_view + launcher.registry() carries per-agent liveness."""

import ast
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
from core.comm import liveness
from core.comm.launcher import get_launcher

_here = _pl.Path(__file__).resolve()
ROOT = str(
    next((p for p in (_here, *_here.parents) if (p / "agent_cli.py").exists() and (p / "core").is_dir()), _here.parent)
)
for f in ("core/comm/liveness.py", "core/comm/launcher.py"):
    ast.parse(_pl.Path(os.path.join(ROOT, f)).read_text(encoding="utf-8"))
    print("parse OK:", f)

A = "l3a_probe"
c = liveness._client()
if c:
    c.delete(liveness._worklive_prefix() + A)

assert liveness.wedge_view(A) is None
print("[PASS] no record -> None (fail-safe)")

wl = liveness.worklive(A)
wl.set("idle")
v = liveness.wedge_view(A, wedge_s=0)  # even at threshold 0...
assert v, v
assert v["wedged"] is False, v  # ...idle is never a wedge
print(f"[PASS] idle never wedged (thr=0): phase={v['phase']} wedged={v['wedged']}")

wl.set("thinking")
time.sleep(0.15)
hot = liveness.wedge_view(A, wedge_s=0.1)  # threshold BELOW time-in-phase -> wedged
cold = liveness.wedge_view(A, wedge_s=1000)  # threshold ABOVE time-in-phase -> not wedged
assert hot["wedged"] is True, (hot, cold)
assert cold["wedged"] is False, (hot, cold)
print(f"[PASS] thinking stuck={hot['stuck_seconds']}s -> wedged@0.1s=True, wedged@1000s=False (flag flips both ways)")

# registry() exposes liveness per agent
liveness.worklive("deepseek").set("reading", "somefile.py")
reg = get_launcher().registry()
entry = next((r for r in reg if r["agent_id"] == "deepseek"), None)
assert entry, "registry entry must carry a liveness field"
assert "liveness" in entry, "registry entry must carry a liveness field"
assert entry["liveness"], entry["liveness"]
assert entry["liveness"]["phase"] == "reading", entry["liveness"]
print(f"[PASS] registry() carries liveness: {entry['liveness']}")

if c:
    for k in (A, "deepseek"):
        c.delete(liveness._worklive_prefix() + k)
print("\nL3a VERIFIED.")
