"""Probe: the Built!=Wired gate PASSES on reality (known-standalone modules frozen) and FAILS on a
NEW unwired core module. Membrane slice 2 proof."""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import check_wiring as w

_, reachable, unwired = w.analyze()
assert reachable, "reachability graph should find SOME wired modules"
new = [u for u in unwired if u not in w.EXCEPTIONS]
assert not new, ("every unwired module must be a documented exception", new)
print(f"[PASS] passes on reality; {len(unwired)} unwired module(s), all documented as exceptions/backlog")

# every exception must actually be unwired (no stale entries)
stale = [e for e in w.EXCEPTIONS if e not in unwired]
assert not stale, ("EXCEPTIONS must not name a now-wired/gone module", stale)
print(f"[PASS] no stale exceptions ({len(w.EXCEPTIONS)} all genuinely unwired)")

# a brand-new unwired module must FAIL the gate
orig = w.analyze
w.analyze = lambda: (set(), {"x"}, sorted(list(orig()[2]) + ["core/comm/__probe_unwired__.py"]))
assert w.main() == 1, "a new unwired core module must FAIL the gate"
w.analyze = orig
print("[PASS] a new unwired module FAILS the gate (latent capability can't accumulate)")
print("\nWIRING GATE VERIFIED.")
