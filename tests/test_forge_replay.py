"""Forge F0 replay harness (core/recall/replay.py) -- characterization.

The discipline this must prove:
  - credited/surfaced context reconstruction from durable flip events + the injection
    ledger, keyed by lesson source, deduped per target,
  - target inversion is the exact inverse of normalize_target's shapes ('p:'/'c:'),
  - replay() runs the LIVE matcher pipeline (query builder + floor) with no session state,
  - fidelity_check agrees with a freshly-made ledger entry by construction,
  - audit() verdicts move with the data (PASS/FAIL/NA + the pre-registered fallback),
  - everything FAILS SOFT (bad events, empty stores -> empty results, never raises).

Injected fakes only -- never touches canonical Redis or the real event log.
"""
import os
import sys
import tempfile

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.replay import (flip_events, credited_contexts, surfaced_contexts,
                                parse_target, replay, fidelity_check, audit)


class _FakeStore:
    def __init__(self, recs):
        self._recs = recs
    def load_all_learnings_from_store(self):
        return list(self._recs)


_STORE = _FakeStore([
    {"experiment_name": "spine1_unify", "success": "yes",
     "recommendation": "the consolidator is the one seam; route every source through it"},
    {"experiment_name": "redis_probe", "success": "no",
     "recommendation": "probe reachability first; a filtered port hangs connect for 48s"},
])

_EVENTS = [
    {"kind": "flip", "at": "2026-07-08T10:00:00",
     "detail": {"target": "p:e:\\ai-setup\\core\\primitives\\consolidator.py",
                "credited": 2, "sources": ["learn:experiment:spine1_unify"]}},
    {"kind": "flip", "at": "2026-07-08T11:00:00",
     "detail": {"target": "c:py probe redis port", "credited": 1,
                "sources": ["learn:experiment:redis_probe"]}},
    {"kind": "flip", "at": "2026-07-08T12:00:00",   # corpus-gap flip: credited 0 -> not a context
     "detail": {"target": "p:e:\\ai-setup\\docs\\roadmap.md", "credited": 0, "sources": []}},
    {"kind": "command", "at": "2026-07-08T12:30:00", "detail": {"target": "ignored"}},
    {"kind": "flip", "at": "2026-07-08T13:00:00",   # duplicate target for the same source -> dedup
     "detail": {"target": "p:e:\\ai-setup\\core\\primitives\\consolidator.py",
                "credited": 1, "sources": ["learn:experiment:spine1_unify"]}},
]

_INJECTIONS = [
    {"at": 1.0, "alt": "action", "t": "p:e:\\ai-setup\\core\\primitives\\consolidator.py",
     "s": ["learn:experiment:spine1_unify"], "chars": 300},
    {"at": 2.0, "alt": "action", "t": "c:py probe redis port",
     "s": ["learn:experiment:redis_probe"], "chars": 200},
]


def test_flip_events_filters_and_normalizes():
    out = flip_events(events=_EVENTS)
    assert len(out) == 4 and all(f["target"] for f in out)
    assert out[0]["credited"] == 2 and out[0]["sources"] == ["learn:experiment:spine1_unify"]
    assert flip_events(events=[]) == [] and flip_events(events=[{"bad": 1}]) == []
    print("\n--- flip events ---\n  4 flips kept, non-flips dropped, fail-soft OK")


def test_credited_contexts_dedup_and_zero_credit_excluded():
    ctx = credited_contexts(events=_EVENTS)
    assert set(ctx) == {"learn:experiment:spine1_unify", "learn:experiment:redis_probe"}
    # two flips on the same target for spine1_unify -> ONE deduped context
    assert ctx["learn:experiment:spine1_unify"] == ["p:e:\\ai-setup\\core\\primitives\\consolidator.py"]
    print("--- credited contexts ---\n  keyed by source, deduped, credited=0 excluded OK")


def test_surfaced_contexts_from_ledger():
    surf = surfaced_contexts(injections=_INJECTIONS)
    assert surf["learn:experiment:spine1_unify"] == ["p:e:\\ai-setup\\core\\primitives\\consolidator.py"]
    assert surfaced_contexts(injections=[]) == {}
    print("--- surfaced contexts ---\n  ledger entries keyed by source OK")


def test_parse_target_inverts_normalize_target():
    from core.recall.at_action import normalize_target
    t = normalize_target(path="core/primitives/consolidator.py")
    p, c = parse_target(t)
    assert p and c is None and p.endswith("consolidator.py")
    t2 = normalize_target(command="PY   probe  Redis")
    p2, c2 = parse_target(t2)
    assert p2 is None and c2 == "py probe redis"
    assert parse_target("") == (None, None) and parse_target("x:weird") == (None, None)
    print("--- parse target ---\n  p:/c: inverted; unknown shapes unreplayable OK")


def test_replay_runs_live_pipeline_sessionless():
    items = replay("p:core/primitives/consolidator.py", learning_store=_STORE, min_relevance=0.0)
    srcs = [i.get("source") for i in items]
    assert "learn:experiment:spine1_unify" in srcs, f"replay should surface the matching lesson, got {srcs}"
    assert replay("", learning_store=_STORE) == []
    assert replay("p:zzz/qqq/bbb.xyz", learning_store=_STORE, min_relevance=0.99) == []
    print("--- replay ---\n  live pipeline over a historical target; floor honored; fail-soft OK")


def test_fidelity_check_agrees_by_construction():
    fid = fidelity_check(sample=_INJECTIONS, learning_store=_STORE)
    assert fid["checked"] == 2, fid
    assert fid["agreed"] == 2 and fid["rate"] == 1.0, \
        f"fresh ledger entries must re-surface on replay (same pipeline!), got {fid}"
    empty = fidelity_check(sample=[], learning_store=_STORE)
    assert empty["checked"] == 0 and empty["rate"] is None
    print("--- fidelity ---\n  2/2 ledgered sources re-surface; empty sample -> NA OK")


def test_audit_verdicts_move_with_data():
    rep = audit(events=_EVENTS, injections=_INJECTIONS, learning_store=_STORE)
    assert rep["flips"] == 4 and rep["credited_lessons"] == 2
    assert rep["flip_targets_replayable_share"] == 1.0
    assert rep["verdicts"]["c1_fidelity"] == "PASS", rep["verdicts"]
    assert rep["verdicts"]["c5_no_go"] == "clear"
    # both credited lessons hold exactly 1 credited context -> criterion 3 coverage 0% -> FAIL
    assert rep["credited_context_histogram"][">=2"] == 0
    assert rep["verdicts"]["c3_credited_coverage"] == "FAIL"
    # no rehab candidates under the fake store (no counters) -> NA, and fallback not forced
    assert rep["verdicts"]["c2_rehab_coverage"] == "NA"
    print("--- audit ---\n  numbers + verdicts consistent with injected data OK")


def test_audit_no_go_on_unreplayable_targets():
    bad = [{"kind": "flip", "at": "2026-07-08T10:00:00",
            "detail": {"target": "weird-shape-no-prefix", "credited": 1,
                       "sources": ["learn:experiment:spine1_unify"]}}] * 3
    rep = audit(events=bad, injections=[], learning_store=_STORE)
    assert rep["flip_targets_replayable_share"] == 0.0
    assert rep["verdicts"]["c5_no_go"] == "TRIGGERED", rep["verdicts"]
    print("--- no-go ---\n  majority-unreplayable targets trigger criterion 5 OK")


if __name__ == "__main__":
    print("=" * 60)
    print("FORGE F0 REPLAY HARNESS")
    print("=" * 60)
    test_flip_events_filters_and_normalizes()
    test_credited_contexts_dedup_and_zero_credit_excluded()
    test_surfaced_contexts_from_ledger()
    test_parse_target_inverts_normalize_target()
    test_replay_runs_live_pipeline_sessionless()
    test_fidelity_check_agrees_by_construction()
    test_audit_verdicts_move_with_data()
    test_audit_no_go_on_unreplayable_targets()
    print("\nALL FORGE F0 TESTS PASSED")
