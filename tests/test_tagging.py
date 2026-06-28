"""
Tag governance G0 -- tag-history + confidence schema.

Bar: Beat gains a tag-history; current = highest-confidence non-superseded; basis->confidence.
Invariants exercised here: I3 (append-only), I4 (reversible). Plus worst-cases:
empty history, confidence ties, corrupt entries, no tag.

Run: py -m pytest tests/test_tagging.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.narrative.tagging import (
    TagEntry, TagHistory, confidence_for, BASIS_CONFIDENCE, _as_unit_confidence,
)
from core.narrative.schema import Beat

INF, NINF, NAN = float("inf"), float("-inf"), float("nan")


def test_basis_confidence():
    assert confidence_for("path") == 0.95 > confidence_for("category") == 0.6 > confidence_for("persist")
    assert confidence_for("human") == 1.0
    assert confidence_for("totally_unknown_source") == 0.5   # neutral default, no crash


def test_current_is_highest_confidence():
    h = TagHistory()
    h.add("ai-setup", source="persist", at="2026-01-01T00:00:00")     # 0.3
    h.add("stemroller", source="generic", at="2026-01-02T00:00:00")   # 0.4
    h.add("ai-setup", source="path", at="2026-01-03T00:00:00")        # 0.95 -> current
    assert h.current_value() == "ai-setup" and h.current_confidence() == 0.95


def test_tiebreaks_confirmed_then_recency():
    h = TagHistory()
    h.add("vision", source="path", at="2026-01-01T00:00:00")          # 0.95, not confirmed
    h.add("ai-setup", confirmed=True, at="2026-01-02T00:00:00")       # 1.0, confirmed -> wins
    assert h.current_value() == "ai-setup"
    # among equal confidence + both unconfirmed, the more RECENT wins
    g = TagHistory()
    g.add("a", source="category", at="2026-01-01T00:00:00")           # 0.6
    g.add("b", source="category", at="2026-01-05T00:00:00")           # 0.6, later -> current
    assert g.current_value() == "b"


def test_append_only_and_rollback_reversible():
    h = TagHistory()
    h.add("ai-setup", source="path", at="2026-01-01T00:00:00")
    h.add("stemroller", source="strong", at="2026-01-02T00:00:00")    # would be 0.85 < 0.95? no: 0.85<0.95 so ai-setup still current
    # force a (wrong) higher-confidence override, then roll back -- WITHOUT losing history
    h.add("stemroller", source="human", at="2026-01-03T00:00:00")     # confirmed-ish 1.0 -> current
    assert h.current_value() == "stemroller"
    before_len = len(h.entries)
    h.rollback_to("ai-setup", at="2026-01-04T00:00:00")               # re-assert prior (append)
    assert h.current_value() == "ai-setup", "rollback re-asserts the prior tag"
    assert len(h.entries) == before_len + 1, "I3: rollback APPENDS, never deletes"
    # every prior opinion is still in the audit trail (I3/I4)
    assert [e["value"] for e in h.to_list()] == ["ai-setup", "stemroller", "stemroller", "ai-setup"]


def test_worstcase_empty_and_corrupt():
    assert TagHistory().current() is None
    assert TagHistory().current_value() == "unknown" and TagHistory().current_confidence() == 0.1
    # a corrupt entry (bad confidence / missing value) is SKIPPED, not fatal
    raw = [{"value": "ai-setup", "confidence": 0.95, "at": "t"},
           {"value": "x", "confidence": "not-a-number"},   # corrupt -> skipped
           {"confidence": 0.9}]                             # missing value -> ignored by current()
    h = TagHistory.from_list(raw)
    assert h.current_value() == "ai-setup", "valid entries survive a corrupt neighbour"


def test_d3_unit_confidence_helper():
    """The D3 guard in isolation: non-finite -> None (drop), finite out-of-range -> clamp."""
    assert _as_unit_confidence(INF) is None and _as_unit_confidence(NINF) is None
    assert _as_unit_confidence(NAN) is None
    assert _as_unit_confidence("not-a-number") is None and _as_unit_confidence(None) is None
    assert _as_unit_confidence(5.0) == 1.0 and _as_unit_confidence(-3.0) == 0.0   # clamp
    assert _as_unit_confidence(0.95) == 0.95 and _as_unit_confidence(0) == 0.0     # in-range kept


def test_d3_nonfinite_confidence_cannot_hijack_resolver():
    """The probe-E defect: an injected inf-confidence opinion must NOT beat a real tag.
    On load it's dropped entirely (an untrusted vote), so current() is unchanged."""
    base = TagHistory()
    base.add("ai-setup", source="path", at="2026-01-01T00:00:00")          # 0.95, the real tag
    for bad in (INF, NINF, NAN):
        raw = base.to_list() + [{"value": "stemroller", "confidence": bad,
                                 "source": "x", "at": "2026-01-09T00:00:00", "confirmed": False}]
        h = TagHistory.from_list(raw)
        assert h.current_value() == "ai-setup", f"{bad!r} confidence must not win"
        assert all(_as_unit_confidence(e.confidence) is not None for e in h.entries), \
            "no non-finite confidence survives a load"


def test_d3_out_of_range_finite_is_clamped_on_load():
    raw = [{"value": "ai-setup", "confidence": 0.6, "at": "2026-01-01T00:00:00"},
           {"value": "research", "confidence": 5.0, "at": "2026-01-02T00:00:00"}]  # tampered high
    h = TagHistory.from_list(raw)
    cur = h.current()
    assert cur.value == "research" and cur.confidence == 1.0, "finite out-of-range clamped to 1.0, not dropped"


def test_d3_add_sanitizes_nonfinite_input():
    """Our own write path never STORES a non-finite confidence -- it falls back to the basis default."""
    h = TagHistory()
    e = h.add("ai-setup", source="generic", confidence=INF, at="2026-01-01T00:00:00")
    assert e.confidence == confidence_for("generic"), "inf input -> basis default, not stored as inf"
    import math
    assert math.isfinite(e.confidence)


def test_roundtrip_and_beat_backward_compat():
    h = TagHistory()
    h.add("ai-setup", source="path", at="2026-01-01T00:00:00")
    assert TagHistory.from_list(h.to_list()).current_value() == "ai-setup"
    e = TagEntry("research", 0.6, "category", "t")
    assert TagEntry.from_dict(e.to_dict()) == e
    # a Beat dict from BEFORE G0 (no tag_history) still loads -> default []
    old = {"id": "b", "at": "t", "kind": "note", "summary": "s", "source": "ledger:x"}
    b = Beat.from_dict(old)
    assert b.tag_history == [] and Beat.from_dict(b.to_dict()) == b


if __name__ == "__main__":
    for fn in [test_basis_confidence, test_current_is_highest_confidence,
               test_tiebreaks_confirmed_then_recency, test_append_only_and_rollback_reversible,
               test_worstcase_empty_and_corrupt, test_d3_unit_confidence_helper,
               test_d3_nonfinite_confidence_cannot_hijack_resolver,
               test_d3_out_of_range_finite_is_clamped_on_load, test_d3_add_sanitizes_nonfinite_input,
               test_roundtrip_and_beat_backward_compat]:
        fn()
    print("ALL TAG GOVERNANCE G0 TESTS PASSED")
