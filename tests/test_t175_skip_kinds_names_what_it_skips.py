"""PRE-REGISTERED ACCEPTANCE (T175) -- one identifier may not mean two things.

SKIP_KINDS was defined twice, with eight members of disagreement:

    scripts/bifrost_wake.py:45              {ledger_update, resolved, steer, trace}
    scripts/checkers/check_bus_atom_pointers.py:49
        {halt, heartbeat, interrupt, ledger_update, nudge, pause, presence, resume, steer, trace}

They are not drifted copies of one idea -- they answer DIFFERENT QUESTIONS. The wake set means
"must not wake an idle seat" (an agent's plan-wall budget is spent per wake). The checker's set
means, in its own comment, "telemetry or control -- never cargo that needs a library home". The
corpus already has the name for this failure: one_word_two_meanings_is_how_gauges_lie.

WHICH ONE MOVES, and why it is the cheaper one rather than the symmetrical one. bifrost_wake's
SKIP_KINDS is load-bearing: parity pin L7 in bifrost_api, two T045 cutover test files, and ~20
library documents that are historical record and must NOT be rewritten (the substrate is
append-only). The checker's copy is referenced in exactly one function in one file, and its own
comment already supplies the truthful name. Minimum blast radius wins.

  K1  no two files in the tree define the same *KINDS identifier with different membership
  K2  the checker's set is named for what it actually excludes -- cargo, not waking
  K3  classify_body still skips telemetry/control bodies (behaviour unchanged by the rename)
  K4  bifrost_wake's SKIP_KINDS and the L7 parity relationship are untouched

Run: py -m pytest tests/test_t175_skip_kinds_names_what_it_skips.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.checkers import check_kind_policy as KP  # noqa: E402


def test_k1_no_identifier_means_two_things_in_this_tree():
    conflicts = KP.duplicate_identifier_conflicts(KP.discover_kind_sets(ROOT))
    assert conflicts == [], (
        f"one identifier, two memberships: {conflicts}. A reader who greps the name gets a "
        f"different answer depending on which file they landed in.")


def test_k2_the_checkers_set_is_named_for_what_it_excludes():
    from scripts.checkers import check_bus_atom_pointers as CB
    assert hasattr(CB, "NON_CARGO_KINDS"), (
        "the checker excludes telemetry and control because they are not CARGO needing a "
        "library home -- the name must say that, not the unrelated word 'skip'")
    assert not hasattr(CB, "SKIP_KINDS"), "the colliding name must be gone, not aliased"
    assert {"trace", "heartbeat", "presence"} <= CB.NON_CARGO_KINDS


def test_k3_behaviour_is_unchanged_by_the_rename():
    from scripts.checkers import check_bus_atom_pointers as CB
    design_shaped = "Proposal:\n- one\n- two\n- three\n- four\n"
    assert CB.classify_body(design_shaped, kind="trace") is None, "telemetry is still not cargo"
    assert CB.classify_body(design_shaped, kind="heartbeat") is None
    assert CB.classify_body("", kind="handoff") is None, "empty body is still clean"


def test_k4_the_wake_side_is_untouched():
    """The rename must not disturb the set that IS load-bearing, nor the L7 relationship."""
    from core.comm import bifrost_api
    from scripts import bifrost_wake as bw
    assert bw.SKIP_KINDS == {"trace", "steer", "resolved", "ledger_update"}
    assert bw.SKIP_KINDS_LANE == bw.SKIP_KINDS | {"note", "status"}
    assert bifrost_api.PENDING_SKIP_KINDS == bw.SKIP_KINDS_LANE, "L7 parity still holds"
