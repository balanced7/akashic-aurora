"""W0.3 pins: the bench must be harder to fool than the thing it grades.

SPEC: W0.3 of `fences/context-system/reconciliation.md`. SET: `tests/fixtures/recall_eval/moments.json`.

A bench that cannot be wrong is a demo. These pins are about the three ways this one could lie:
by filling in an answer key it does not have, by rewarding a surface that always speaks, and by
reporting a share of nothing as zero. The engine is injected, so none of this touches the corpus.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall import bench as B  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def engine(mapping):
    """A fake recall: trigger -> list of lesson sources."""
    def fn(*, path=None, command=None, limit=5):
        key = path or command or ""
        return {"lessons": [{"source": s, "text": "x" * 100} for s in mapping.get(key, [])],
                "verbs": []}
    return fn


M_HIT = {"id": "A", "trigger": {"path": "p"}, "expect": "learn:experiment:right"}
M_ABSTAIN = {"id": "B", "trigger": {"path": "q"}, "expect": "ABSTAIN"}
M_UNRESOLVED = {"id": "C", "trigger": {"path": "r"}, "expect": "UNRESOLVED"}


def test_a_hit_at_one_counts_as_a_hit_at_k_too():
    d = B.score([M_HIT], engine({"p": ["learn:experiment:right", "learn:experiment:other"]}))
    assert d["recall_at_1"] == 1.0 and d["recall_at_k"] == 1.0 and d["scored"] == 1


def test_a_hit_below_rank_one_is_not_a_hit_at_one():
    d = B.score([M_HIT], engine({"p": ["learn:experiment:other", "learn:experiment:right"]}))
    assert d["recall_at_1"] == 0.0 and d["recall_at_k"] == 1.0


def test_an_also_acceptable_answer_counts():
    m = {**M_HIT, "also_acceptable": ["learn:experiment:sibling"]}
    d = B.score([m], engine({"p": ["learn:experiment:sibling"]}))
    assert d["recall_at_1"] == 1.0


# ---------------------------------------------------------------- the three ways it could lie
def test_an_unresolved_moment_is_excluded_and_counted_never_guessed_at():
    """An answer key filled in by guessing measures the guesser. M3 of the seeded set is exactly
    this: the dossier claims a lesson exists for it and the corpus does not contain one."""
    d = B.score([M_HIT, M_UNRESOLVED], engine({"p": ["learn:experiment:right"], "r": ["anything"]}))
    assert d["excluded"] == ["C"]
    assert d["scored"] == 1, "an excluded moment must not inflate or deflate the denominator"


def test_silence_is_the_right_answer_on_an_abstain_moment():
    d = B.score([M_ABSTAIN], engine({}))
    assert d["abstention"] == {"total": 1, "correct": 1, "rate": 1.0}


def test_speaking_on_an_abstain_moment_is_a_failure_however_topical():
    # Without this, a surface that always fires scores the same as one that fires correctly, and
    # "it said something" becomes indistinguishable from "it was right".
    d = B.score([M_ABSTAIN], engine({"q": ["learn:experiment:about_the_right_topic"]}))
    assert d["abstention"]["correct"] == 0
    assert d["rows"][0]["verdict"] == "SPOKE-WHEN-SILENT"


def test_an_abstain_moment_never_enters_the_recall_denominator():
    d = B.score([M_ABSTAIN], engine({}))
    assert d["scored"] == 0 and d["recall_at_1"] is None


def test_a_rate_over_nothing_is_unknown_not_zero():
    d = B.score([], engine({}))
    assert d["recall_at_1"] is None and d["chrome_share"] is None
    assert d["abstention"]["rate"] is None


def test_precision_is_named_uncheckable_with_its_reason_not_estimated():
    d = B.score([M_HIT], engine({"p": ["learn:experiment:right"]}))
    assert d["precision_at_3"] == B.UNCHECKABLE
    assert "relevant-set" in d["precision_why"]


# ---------------------------------------------------------------- chrome
def test_chrome_share_counts_everything_pushed_that_is_not_a_lesson():
    def fn(*, path=None, command=None, limit=5):
        return {"lessons": [{"source": "learn:experiment:right", "text": "a" * 75}],
                "verbs": ["b" * 25]}
    d = B.score([M_HIT], fn)
    assert d["chrome_share"] == pytest.approx(0.25)


# ---------------------------------------------------------------- the committed set itself
def test_the_committed_set_loads_and_declares_its_own_shortfall():
    meta = B.load()
    assert meta["schema"] == B.SCHEMA
    assert meta["seeded"] == len(meta["moments"]) < meta["target"]
    assert meta["why_not_forty_yet"], "a partial set must say it is partial, in the file"


def test_every_seeded_moment_names_a_trigger_and_a_verdictable_expectation():
    for m in B.load()["moments"]:
        assert m.get("trigger", {}).get("path") or m.get("trigger", {}).get("command")
        assert m.get("expect"), m["id"]


def test_a_set_with_the_wrong_schema_is_refused_rather_than_read_hopefully(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"schema": "something.else", "moments": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        B.load(str(p))
