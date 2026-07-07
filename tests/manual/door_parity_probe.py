"""Probe: the door-parity guard PASSES on reality and FAILS on drift (new unclassified verb /
shared regression). The first membrane slice's proof."""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tests/manual -> ROOT
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import check_door_parity as c

fails, gaps, cli, mcp = c.check()
assert not fails, ("must PASS on current reality", fails)
assert len(gaps) >= 1, "should be tracking known CLI<->MCP gaps as debt"
print(f"[PASS] passes on reality; tracking {len(gaps)} known gaps as debt")

orig = c.cli_verbs
c.cli_verbs = lambda: sorted(set(orig()) | {"zznewverb"})
f2, _, _, _ = c.check()
assert any("zznewverb" in x for x in f2), "must FAIL on a new unclassified verb"
print("[PASS] fails on a new unclassified verb (ratchet stops new drift)")

c.cli_verbs = lambda: sorted(set(orig()) - {"boot"})
f3, _, _, _ = c.check()
assert any("boot" in x for x in f3), "must FAIL when a shared verb regresses off a door"
print("[PASS] fails on a shared-verb regression")

c.cli_verbs = orig
print("\nDOOR-PARITY GUARD VERIFIED.")
