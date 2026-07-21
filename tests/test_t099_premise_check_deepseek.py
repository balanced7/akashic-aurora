"""premise-check belt entry — deepseek lane pins (C2-1 suffix: _deepseek).

Born 2026-07-21 tools-hunt #1 pick: doctor→delta→inbox = cross-check the system's beliefs
against its actual state. SENTINEL because it guards against false premises — you can't
build on a lie. Kills C9-1 (system confidently wrong about itself) and C6-4 (message/lane
integrity drift).

Pins (RED-first, method baseline):
  P1  premise-check resolves to 3 steps: doctor, delta deepseek, bifrost-inbox
  P2  family = SENTINELS (the caste: verbs that guard)
  P3  resolve_and_run executes all 3 steps in order via the injected runner
  P4  evidence upgrades GUESS→VERIFIED, tested_against records this pin suite

After GREEN: upgrade the deepseek.json belt entry evidence to VERIFIED.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REGISTRY_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "verb-registry"
)


def _load_deepseek_registry():
    """Read the durable registry file (truth)."""
    path = os.path.join(REGISTRY_ROOT, "deepseek.json")
    if not os.path.exists(path):
        pytest.skip("deepseek.json registry not found — run from project root")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _get_entry(name):
    doc = _load_deepseek_registry()
    entries = doc.get("entries", {})
    e = entries.get(name)
    if not e or e.get("status", "active") != "active":
        pytest.skip(f"no active belt entry {name!r}")
    return e


# ═══════════════════════════════════════════════════════════════ P1: step resolution
def test_p1_resolves_to_three_correct_steps():
    """premise-check = doctor → delta deepseek → bifrost-inbox"""
    from core.toolbelt.registry import Toolbelt
    tb = Toolbelt("deepseek", root=REGISTRY_ROOT)
    steps = tb.resolve("premise-check")
    assert len(steps) == 3, f"expected 3 steps, got {len(steps)}: {steps}"
    assert steps[0] == ["doctor"], f"step 0: {steps[0]}"
    assert steps[1] == ["delta", "deepseek"], f"step 1: {steps[1]}"
    assert steps[2] == ["bifrost-inbox"], f"step 2: {steps[2]}"


# ═══════════════════════════════════════════════════════════════ P2: family tag
def test_p2_family_is_sentinels():
    """premise-check guards against false premises → SENTINELS caste"""
    e = _get_entry("premise-check")
    fam = e.get("family", "UNSORTED")
    assert fam == "SENTINELS", (
        f"premise-check family must be SENTINELS (guards against false premises), "
        f"got {fam}. SENTINELS = verbs that guard. premise-check guards the system's "
        f"beliefs against its actual state — you can't build on a lie."
    )


# ═══════════════════════════════════════════════════════════════ P3: execution order
def test_p3_resolve_and_run_executes_all_three_steps_in_order():
    """The injected runner sees doctor, delta deepseek, bifrost-inbox in sequence."""
    from core.toolbelt.registry import Toolbelt
    tb = Toolbelt("deepseek", root=REGISTRY_ROOT)
    trace = []
    rc = tb.resolve_and_run("premise-check", runner=lambda argv: (trace.append(list(argv)) or 0))
    assert rc == 0, f"all steps should succeed, got rc={rc}"
    assert len(trace) == 3, f"expected 3 invocations, got {len(trace)}: {trace}"
    assert trace[0] == ["doctor"], f"invocation 0: {trace[0]}"
    assert trace[1] == ["delta", "deepseek"], f"invocation 1: {trace[1]}"
    assert trace[2] == ["bifrost-inbox"], f"invocation 2: {trace[2]}"


# ═══════════════════════════════════════════════════════════════ P4: evidence upgrade
def test_p4_evidence_upgrades_guess_to_verified():
    """After this pin suite passes, the belt entry evidence should be VERIFIED
    with tested_against pointing at this file."""
    e = _get_entry("premise-check")
    evidence = e.get("evidence", "GUESS")
    tested = e.get("tested_against")
    # This pin is ADVISORY — it asserts the TARGET state. When the belt entry is
    # GUESS, this pin FAILS (RED), teaching "unpinned sugar confesses untested."
    # When we upgrade to VERIFIED, the same pin PASSES (GREEN), proving the
    # evidence contract: no VERIFIED entry lacks a tested_against anchor.
    assert evidence == "VERIFIED", (
        f"premise-check evidence is {evidence}, not VERIFIED. "
        f"Run: the belt entry upgrade step (mint with evidence=VERIFIED, "
        f"tested_against='test_t099_premise_check_deepseek.py') after P1-P3 pass."
    )
    assert tested is not None, (
        "VERIFIED entries must carry tested_against pointing at their pin suite. "
        "Set tested_against='test_t099_premise_check_deepseek.py' on mint."
    )
    assert "premise_check_deepseek" in str(tested), (
        f"tested_against={tested!r} should reference this pin file"
    )
