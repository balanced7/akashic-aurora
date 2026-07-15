"""fence workspace (R2 / T053) -- the structure IS the enforcement, pre-registered.

A fence today is 3-4 files bound by naming convention; the r2 round died when a half
confabulated the filenames. The workspace makes that failure class UNREPRESENTABLE:
slot paths are DERIVED by the tool (never typed by an agent), and the method contract's
mechanical checks (M1-BRIEF sections, M1-CF verdict tags, M1-PV citation verification,
seal ordering, author independence) run AT SEAL TIME, not at post-mortem time.

Kill conditions pinned here:
  1. unknown slot -> hard refusal (the confabulated-filename class);
  2. brief missing an M1-BRIEF section -> seal refused;
  3. a half with an untagged verdict -> seal refused (M1-CF);
  4. reconciliation sealed before both halves + PV -> refused (order is the fence);
  5. PV flags a fabricated citation; reconciliation must ACKNOWLEDGE it to seal (M1-PV
     is section-scoped invalidation, not a hard block -- but silent omission is);
  6. same author on both halves -> reconciliation refused (independence is the point).
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["AKASHIC_FENCE_ROOT"] = tempfile.mkdtemp(prefix="fences_")

from core.coord.fence_workspace import (
    open_fence, slot_path, write_slot, seal, run_pv, fence_status,
)

BRIEF_OK = """# fence brief
## 1. CHARTER
Design review: does the walk terminate?
## 2. INPUTS
- core/recall/lookback.py
## 3. RULES OF ENGAGEMENT
Blind halves; deliverables into slots.
## 4. THE QUESTION
Does build_map terminate on cyclic edges?
## 5. OUTPUT CONTRACT
Verdict-per-item with M1-CF tags, into your half slot.
"""

HALF_TAGGED = """# half
V1. [CERTAIN] The walk terminates: seen-set guards re-entry (core/recall/lookback.py:23).
V2. [INFERRED] Cycle depth never exceeds one hop by construction.
"""


def _mk(fid, brief=BRIEF_OK):
    open_fence(fid, question="does the walk terminate?", tier="full", by="cursor")
    write_slot(fid, "brief", brief, by="cursor")
    ok, problems = seal(fid, "brief", by="cursor")
    return ok, problems


def test_unknown_slot_is_unrepresentable():
    open_fence("f_slots", question="q", tier="full", by="cursor")
    for bad in ("half-C", "reconcilation", "notes", "../escape"):
        try:
            slot_path("f_slots", bad)
            raise AssertionError(f"slot_path must refuse unknown slot {bad!r}")
        except (KeyError, ValueError):
            pass
        try:
            write_slot("f_slots", bad, "text", by="a")
            raise AssertionError(f"write_slot must refuse unknown slot {bad!r}")
        except (KeyError, ValueError):
            pass
    print("--- slot law ---\n  unknown/confabulated slot names refused everywhere OK")


def test_brief_seal_requires_m1_brief_sections():
    ok, problems = _mk("f_brief_bad", brief="# brief\n## 1. CHARTER\nonly a charter\n")
    assert not ok and any("INPUTS" in p or "QUESTION" in p or "OUTPUT" in p for p in problems), \
        f"missing sections must be named, got {problems}"
    ok, problems = _mk("f_brief_ok")
    assert ok, f"a five-section brief must seal, got {problems}"
    print("--- brief gate ---\n  M1-BRIEF sections enforced at seal OK")


def test_half_seal_requires_cf_tags():
    _mk("f_cf")
    write_slot("f_cf", "half_a", "V1. the walk terminates, trust me\n", by="claude")
    ok, problems = seal("f_cf", "half_a", by="claude")
    assert not ok and any("tag" in p.lower() for p in problems), \
        f"an untagged verdict must refuse seal with a tag complaint, got {problems}"
    write_slot("f_cf", "half_a", HALF_TAGGED, by="claude")
    ok, problems = seal("f_cf", "half_a", by="claude")
    assert ok, f"tagged verdicts must seal, got {problems}"
    print("--- M1-CF gate ---\n  untagged verdict refused; tagged half seals OK")


def test_reconciliation_order_and_pv_are_mandatory():
    _mk("f_order")
    write_slot("f_order", "half_a", HALF_TAGGED, by="claude")
    seal("f_order", "half_a", by="claude")
    write_slot("f_order", "reconciliation", "## M1-PV verification pass\nnone missing\n", by="cursor")
    ok, problems = seal("f_order", "reconciliation", by="cursor")
    assert not ok, f"reconciliation must not seal with half_b open + no PV, got {problems}"
    write_slot("f_order", "half_b", HALF_TAGGED, by="deepseek")
    seal("f_order", "half_b", by="deepseek")
    ok, problems = seal("f_order", "reconciliation", by="cursor")
    assert not ok and any("pv" in p.lower() for p in problems), \
        f"PV must be required before reconciliation seals, got {problems}"
    run_pv("f_order")
    ok, problems = seal("f_order", "reconciliation", by="cursor")
    assert ok, f"order satisfied -> seal, got {problems}"
    print("--- seal order ---\n  reconciliation gated on both halves + PV OK")


def test_pv_flags_fabricated_citation_and_demands_acknowledgement():
    _mk("f_pv")
    fabricated = "V1. [CERTAIN] handled in core/comm/ghost_module.py:44 by the retry loop.\n"
    write_slot("f_pv", "half_a", fabricated, by="claude")
    seal("f_pv", "half_a", by="claude")
    write_slot("f_pv", "half_b", HALF_TAGGED, by="deepseek")
    seal("f_pv", "half_b", by="deepseek")
    report = run_pv("f_pv")
    assert any("ghost_module" in m for m in report["missing"]), \
        f"the fabricated path must be flagged MISSING, got {report}"
    write_slot("f_pv", "reconciliation", "## M1-PV verification pass\nall good\n", by="cursor")
    ok, problems = seal("f_pv", "reconciliation", by="cursor")
    assert not ok and any("ghost_module" in p for p in problems), \
        f"an unacknowledged MISSING citation must block the seal BY NAME, got {problems}"
    write_slot("f_pv", "reconciliation",
               "## M1-PV verification pass\nINVALIDATED: core/comm/ghost_module.py:44 "
               "does not exist -- V1 section retired.\n", by="cursor")
    ok, problems = seal("f_pv", "reconciliation", by="cursor")
    assert ok, f"acknowledged invalidation -> seal (section-scoped, not a hard block), got {problems}"
    print("--- M1-PV ---\n  fabricated citation flagged + acknowledgement demanded OK")


def test_author_independence():
    _mk("f_authors")
    write_slot("f_authors", "half_a", HALF_TAGGED, by="claude")
    seal("f_authors", "half_a", by="claude")
    write_slot("f_authors", "half_b", HALF_TAGGED, by="claude")
    seal("f_authors", "half_b", by="claude")
    run_pv("f_authors")
    write_slot("f_authors", "reconciliation", "## M1-PV verification pass\nnone missing\n", by="claude")
    ok, problems = seal("f_authors", "reconciliation", by="claude")
    assert not ok and any("author" in p.lower() or "independen" in p.lower() for p in problems), \
        f"same author on both halves must refuse, got {problems}"
    st = fence_status("f_authors")
    assert st["seals"].get("half_a", {}).get("by") == "claude"
    print("--- independence ---\n  one-author fence refused at reconciliation OK")


if __name__ == "__main__":
    print("=" * 60)
    print("FENCE WORKSPACE -- structure is enforcement (T053 / R2)")
    print("=" * 60)
    test_unknown_slot_is_unrepresentable()
    test_brief_seal_requires_m1_brief_sections()
    test_half_seal_requires_cf_tags()
    test_reconciliation_order_and_pv_are_mandatory()
    test_pv_flags_fabricated_citation_and_demands_acknowledgement()
    test_author_independence()
    print("\nALL FENCE-WORKSPACE TESTS PASSED")
