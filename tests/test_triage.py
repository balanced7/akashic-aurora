"""Sharpening-loop S1: the value-rate triage (core/recall/funnel.triage) -- read-only
buckets over the recall:use:* counters. Injectable fakes, same pattern as snapshot();
the report proposes, a human disposes (F2 Goodhart guard: no auto-pruning path exists)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.funnel import triage


class _FakeStore:
    def __init__(self, use):
        self._d = {f"recall:use:{k}": json.dumps(v) for k, v in use.items()}

    def keys(self, pattern):
        return list(self._d)

    def get(self, k):
        return self._d.get(k)


class _FakeLearning:
    def __init__(self, n):
        self._n = n

    def load_all_learnings_from_store(self):
        return [{"experiment_name": f"l{i}"} for i in range(self._n)]


def _t(use, n_corpus=10, injections=(), **kw):
    return triage(store=_FakeStore(use), learning_store=_FakeLearning(n_corpus),
                  injections=list(injections), **kw)


def test_buckets_route_correctly():
    t = _t({
        "learn:experiment:hero":    {"surfaced": 9, "useful": 1, "noise": 0, "helped": 2},
        "learn:experiment:freeload": {"surfaced": 8, "useful": 0, "noise": 0, "helped": 0},
        "learn:experiment:noisy":   {"surfaced": 3, "useful": 0, "noise": 2, "helped": 0},
        "learn:experiment:young":   {"surfaced": 2, "useful": 0, "noise": 0, "helped": 0},
    })
    assert [r["source"] for r in t["protect"]] == ["learn:experiment:hero"]
    assert [r["source"] for r in t["cost_no_return"]] == ["learn:experiment:freeload"]
    assert [r["source"] for r in t["noise_voted"]] == ["learn:experiment:noisy"]
    assert t["watch_count"] == 1
    assert t["dormant_count"] == 6, "corpus 10 - tracked 4"


def test_credit_shields_from_cost_bucket():
    """One helped credit outweighs any surfaced count -- proven value is never listed
    as cost, no matter how often it's shown."""
    t = _t({"learn:experiment:workhorse": {"surfaced": 50, "useful": 0, "noise": 1, "helped": 1}})
    assert t["cost_no_return"] == [] and t["noise_voted"] == []
    assert t["protect"][0]["source"] == "learn:experiment:workhorse"


def test_min_surfaced_threshold_moves_the_line():
    use = {"learn:experiment:x": {"surfaced": 3, "useful": 0, "noise": 0, "helped": 0}}
    assert _t(use)["cost_no_return"] == []                     # default 5: too early
    assert len(_t(use, min_surfaced=3)["cost_no_return"]) == 1  # lowered: now costs


def test_cost_bucket_ranked_by_surfaced_desc():
    t = _t({
        "learn:experiment:a": {"surfaced": 6, "useful": 0, "noise": 0, "helped": 0},
        "learn:experiment:b": {"surfaced": 12, "useful": 0, "noise": 0, "helped": 0},
    })
    assert [r["source"] for r in t["cost_no_return"]] == ["learn:experiment:b", "learn:experiment:a"]


def test_window_token_cost_attributed_per_source():
    inj = [{"s": ["learn:experiment:a", "learn:experiment:b"], "chars": 800},
           {"s": ["learn:experiment:a"], "chars": 400}]
    t = _t({"learn:experiment:a": {"surfaced": 6, "useful": 0, "noise": 0, "helped": 0},
            "learn:experiment:b": {"surfaced": 6, "useful": 0, "noise": 0, "helped": 0}},
           injections=inj)
    by = {r["source"]: r["window_tokens_approx"] for r in t["cost_no_return"]}
    assert by["learn:experiment:a"] == 200 and by["learn:experiment:b"] == 100
    assert t["window_injected_tokens_approx"] == 300


class _BrokenStore:
    def keys(self, pattern):
        raise RuntimeError("store down")


def test_fail_soft_on_broken_backend():
    """A dead store yields an empty report, never a raise (and never a silent fallback
    to the real store -- that's why this passes a BROKEN fake, not None)."""
    t = triage(store=_BrokenStore(), learning_store=_FakeLearning(0), injections=[])
    assert t["tracked"] == 0 and t["protect"] == [] and t["dormant_count"] == 0
