"""
Tests for the Distiller shared primitive.

Run: py tests/test_distiller.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.primitives.distiller import Distiller, Distillation


def test_distills_within_budget():
    d = Distiller()
    items = [
        {"recommendation": "trust the file fallback", "source": "learn_1"},
        {"decision": "append-and-replay over raw redis", "source": "ADR_2"},
        {"description": "GPU allocation pending", "source": "blk_3", "relationship_type": "prevents"},
    ]
    out = d.distill(items, token_budget=9000)
    assert isinstance(out, Distillation)
    assert out.critic_ok and out.approx_tokens <= 9000
    assert out.included_sources == ["learn_1", "ADR_2", "blk_3"] and out.dropped_sources == []
    # every entry keeps a source pointer (lossless-pointer rule)
    assert all(e["source"] for e in out.entries)
    # skeleton is human-readable and carries the sources + a relates tag
    assert "trust the file fallback" in out.skeleton
    assert "(source: blk_3)" in out.skeleton and "[relates: prevents]" in out.skeleton
    print("\n--- distill within budget ---\n  compact skeleton + source pointers + critic OK")


def test_drops_to_fit_budget_but_keeps_pointers():
    d = Distiller()
    items = [{"recommendation": "x" * 80, "source": f"s{i}"} for i in range(10)]
    out = d.distill(items, token_budget=40)   # only a few fit
    assert out.approx_tokens <= 40, "must respect the budget"
    assert out.dropped_sources, "over-budget items are dropped"
    # dropped items are still recoverable via their pointers (lossy view + lossless pointer)
    assert set(out.included_sources) | set(out.dropped_sources) == {f"s{i}" for i in range(10)}
    assert out.critic_ok, "dropping to fit is allowed (not a failure)"
    print("\n--- budget trim ---\n  drops to fit, all sources accounted (recoverable) OK")


def test_skips_source_less_items():
    d = Distiller()
    out = d.distill([{"recommendation": "no pointer here"},          # no source/id -> skipped
                     {"recommendation": "keep me", "source": "s1"}], token_budget=9000)
    assert out.skipped_no_source == 1, "source-less item must be skipped (not traceable)"
    assert [e["source"] for e in out.entries] == ["s1"], "only traceable entries kept"
    assert any("no source pointer" in n for n in out.critic_notes)
    print("\n--- source-less ---\n  items without a source pointer are skipped (lossless-pointer rule) OK")


def test_llm_writer_seam():
    # an injected writer is honored (the LLM seam)
    def fake_writer(items, budget, instruction):
        return Distillation(skeleton="LLM SUMMARY", entries=[], included_sources=["x"],
                            dropped_sources=[], approx_tokens=2, critic_ok=True, critic_notes=[])
    d = Distiller(writer=fake_writer)
    out = d.distill([{"text": "anything", "source": "x"}], token_budget=9000)
    assert out.skeleton == "LLM SUMMARY", "injected writer should be used"
    print("\n--- writer seam ---\n  injected (LLM) writer honored OK")


if __name__ == "__main__":
    print("=" * 60)
    print("DISTILLER TESTS")
    print("=" * 60)
    test_distills_within_budget()
    test_drops_to_fit_budget_but_keeps_pointers()
    test_skips_source_less_items()
    test_llm_writer_seam()
    print("\n" + "=" * 60)
    print("ALL DISTILLER TESTS PASSED")
    print("=" * 60)
