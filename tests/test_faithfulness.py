"""Characterization tests for the FAITH-1 faithfulness critic (core/primitives/faithfulness.py).

Run: py tests/test_faithfulness.py   (or via pytest)

The critic's mandate (per the adversarial review): VALIDATE before you gate. These tests
characterize the critic's behavior on the signals it claims to judge:
  - NO false-positives on real extractive output (the dangerous error: blocking real knowledge),
  - it CATCHES a fabricated/unresolvable source pointer (GhostCite: ~50% LLM citation hallucination),
  - it CATCHES a fabricated number (FactCC's own negative recipe; NLI models miss these),
  - it REGRESSION-guards the old paren bug (a source containing ')'),
  - low grounding overlap is SOFT (reported, never fails the verdict -- the ROUGE/FP trap).
"""
import os
import sys
import tempfile

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.primitives.consolidator import Consolidator
from core.primitives.distiller import Distiller
from core.primitives.faithfulness import faithfulness_critic, faithfulness_report

# Representative real records (mirrors the learning/memory items consolidation projects).
_ITEMS = [
    Consolidator.item(text="probe reachability first; a filtered port hangs connect for 48s",
                      source="learn:experiment:redis_probe", importance=4),
    Consolidator.item(text="use the node manager to install custom nodes",
                      source="mem:exp:comfyui_install", importance=3),
    Consolidator.item(text="memoization gave a 52% speedup; loop unrolling only 2%",
                      source="learn:experiment:perf(prior art)", importance=4),  # source HAS parens
]


def _real_skeleton():
    d = Distiller(max_chars_per_entry=170).distill(_ITEMS, token_budget=4000)
    return d.skeleton


def test_no_false_positive_on_real_output():
    """The key validation: the extractive heuristic writer copies each item's source verbatim,
    so a faithful distillation must NEVER be flagged. A false-positive here blocks real knowledge."""
    skeleton = _real_skeleton()
    ok, notes = faithfulness_critic(_ITEMS, skeleton)
    assert ok is True, f"false-positive on faithful output! notes={notes}"
    rep = faithfulness_report(_ITEMS, skeleton)
    assert rep["unresolved"] == 0 and rep["untraceable"] == 0 and rep["number_fail"] == 0
    print(f"\n--- no false-positive ---\n  faithful real output passes (conf={rep['confidence']}) OK")


def test_source_with_parens_resolves():
    """Regression for the old false-positive bug: a source like '...perf(prior art)' must be
    captured WHOLE (to the line-final ')'), not truncated -- so it resolves and stays faithful."""
    skeleton = _real_skeleton()
    rep = faithfulness_report(_ITEMS, skeleton)
    paren_lines = [p for p in rep["per_line"] if p.get("src", "").endswith("(prior art)")]
    assert paren_lines and all(p["resolves"] for p in paren_lines), \
        f"paren source was truncated/unresolved: {paren_lines}"
    print("--- paren-safe ---\n  source containing ')' resolves whole OK")


def test_catches_fabricated_pointer():
    """An LLM writer that cites a source not among the inputs must be caught (citation hallucination)."""
    bad = "- some plausible but invented lesson  (source: learn:experiment:ghost_999)"
    ok, notes = faithfulness_critic(_ITEMS, bad)
    assert ok is False and any("fabricated" in n or "unresolvable" in n for n in notes), notes
    print("--- fabricated pointer ---\n  unresolvable source -> unfaithful OK")


def test_catches_fabricated_number():
    """A line citing a real source but introducing a number absent from it = fabricated figure."""
    bad = "- probe reachability first; a filtered port hangs connect for 999s  (source: learn:experiment:redis_probe)"
    ok, notes = faithfulness_critic(_ITEMS, bad)
    assert ok is False and any("number" in n for n in notes), notes
    print("--- fabricated number ---\n  number absent from source -> unfaithful OK")


def test_untraceable_line_caught():
    """A content claim with no source pointer can't be traced -> unfaithful."""
    ok, notes = faithfulness_critic(_ITEMS, "- a claim with no pointer at all")
    assert ok is False and any("no source pointer" in n for n in notes), notes
    print("--- untraceable ---\n  claim without a pointer -> unfaithful OK")


def test_low_grounding_is_soft():
    """Low overlap to the cited source is REPORTED (paraphrase/drift) but does NOT fail the verdict
    when the pointer resolves and no number is fabricated -- avoids the ROUGE/NLI false-positive trap."""
    paraphrase = "- check the host responds before dialing  (source: learn:experiment:redis_probe)"
    rep = faithfulness_report(_ITEMS, paraphrase)
    ok, notes = faithfulness_critic(_ITEMS, paraphrase)
    assert ok is True, f"low grounding must not hard-fail: {notes}"
    assert rep["low_grounding"] >= 1, "weak grounding should be observed in the report"
    print(f"--- soft grounding ---\n  paraphrase observed not gated (conf={rep['confidence']}) OK")


def test_consolidator_wires_the_gate():
    """The default Consolidator distiller carries the faithfulness critic (one seam, every consumer)."""
    d = Consolidator().consolidate(_ITEMS, instruction="lessons")
    assert d.critic_ok is True
    assert any("faithful" in n for n in d.critic_notes), d.critic_notes
    print("--- wired ---\n  Consolidator default carries the faithfulness gate OK")


if __name__ == "__main__":
    print("=" * 60)
    print("FAITHFULNESS CRITIC (FAITH-1) CHARACTERIZATION")
    print("=" * 60)
    test_no_false_positive_on_real_output()
    test_source_with_parens_resolves()
    test_catches_fabricated_pointer()
    test_catches_fabricated_number()
    test_untraceable_line_caught()
    test_low_grounding_is_soft()
    test_consolidator_wires_the_gate()
    print("\n" + "=" * 60)
    print("ALL FAITHFULNESS TESTS PASSED")
    print("=" * 60)
