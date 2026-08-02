"""L1 proof: worklive round-trips, since_ts semantics, turn count, and a stuck-timer that
can BOTH rise (wedge visible) and reset on a phase change (metric not pinned)."""
import os, ast, sys, time

# Root DERIVED from this file, never hardcoded: the literal pinned one machine's disk,
# so a copy of the repo anywhere else resolved every path under it to nothing.
import os as _os, pathlib as _pl
_here = _pl.Path(__file__).resolve()
ROOT = str(next((p for p in (_here, *_here.parents)
                 if (p / 'agent_cli.py').exists() and (p / 'core').is_dir()), _here.parent))
for f in ("core/comm/liveness.py", "scripts/bifrost_runner_deepseek.py"):
    ast.parse(open(os.path.join(ROOT, f), encoding="utf-8").read()); print(f"parse OK: {f}")

sys.path.insert(0, ROOT)
from core.comm import liveness

A = "l1_probe_agent"
wl = liveness.worklive(A)

wl.set("idle")
r = liveness.read(A); assert r and r["phase"] == "idle", r
since1 = r["since_ts"]; print(f"idle -> phase={r['phase']} since_ts={since1} turn={r['turn']}")

time.sleep(0.05)
wl.set("idle")  # same phase again
r = liveness.read(A); assert r["since_ts"] == since1, ("same-phase must keep since_ts", r["since_ts"], since1)
assert r["beat_ts"] > since1, "beat_ts must move on every stamp"
print(f"same-phase re-stamp -> since_ts unchanged ({r['since_ts']}), beat_ts moved ({r['beat_ts']})  [PASS]")

time.sleep(0.05)
wl.set("thinking")
r = liveness.read(A); assert r["phase"] == "thinking" and r["since_ts"] > since1, r
print(f"phase change -> since_ts advanced to {r['since_ts']}  [PASS]")

t0 = wl._turn
wl.set("handling", detail="claude:request", new_turn=True)
r = liveness.read(A); assert r["turn"] == t0 + 1, ("turn must increment", r["turn"], t0)
print(f"new_turn -> turn {t0} -> {r['turn']} detail={r['detail']!r}  [PASS]")

# stuck-timer RISES within a phase (this is what a watchdog reads)
wl.set("thinking")
s1 = liveness.stuck_seconds(A); time.sleep(0.3)
liveness.worklive(A).refresh()  # heartbeat keeps it alive without moving since_ts
s2 = liveness.stuck_seconds(A)
assert s2 > s1 + 0.2, ("stuck timer must rise across a wedge", s1, s2)
print(f"stuck-in-phase rises: {s1:.3f}s -> {s2:.3f}s across a refresh (wedge stays visible)  [PASS]")

# ...and RESETS on a phase change (metric is not pinned -- it can fall)
wl.set("idle")
s3 = liveness.stuck_seconds(A)
assert s3 < 0.1, ("stuck timer must reset on phase change", s3)
print(f"stuck resets on phase change: {s2:.3f}s -> {s3:.3f}s  [PASS -- metric can fall]")

# fail-open sanity: read of an unknown agent is None, never raises
assert liveness.read("no_such_agent_xyz") is None
print("read(unknown) -> None (fail-safe)  [PASS]")

# cleanup
c = liveness._client()
if c:
    c.delete(liveness.WORKLIVE_PREFIX + A)
print("\nL1 VERIFIED.")
