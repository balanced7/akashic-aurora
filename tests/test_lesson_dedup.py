"""Write-time near-duplicate detection (ce-compound's 5-dimension overlap, field-survey C5):
deterministic, advisory-only -- the door warns, it never blocks (append-only ethos)."""
import io
import os
import sys
import tempfile
import types
from contextlib import redirect_stdout

import isolate_canonical  # noqa: F401

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.learning.learning_store import LearningStore, find_related


def _sig(**kw):
    base = {"experiment_name": "new_one",
            "what_tried": "monkeypatch aa._FLIP_DIR in tests/test_stats.py for hermeticity",
            "expected_outcome": "", "actual_outcome": "tests hermetic",
            "recommendation": "Use when adding a session state dir, before shipping: "
                              "update prune_state in core/recall/at_action.py and every dir-swapping test",
            "root_cause": "state dir not swapped in tests", "category": "testing",
            "anti_pattern": ""}
    base.update(kw)
    return base


def _rec(name, **kw):
    r = _sig(experiment_name=name, **kw)
    return {"experiment_name": name, "what_tried": r["what_tried"], "expected": r["expected_outcome"],
            "actual": r["actual_outcome"], "recommendation": r["recommendation"],
            "root_cause": r["root_cause"], "category": r["category"], "anti_pattern": r["anti_pattern"]}


def test_find_related_flags_a_near_duplicate():
    got = find_related(_sig(), [_rec("existing_twin")])
    assert got and got[0]["experiment_name"] == "existing_twin"
    assert got[0]["dims"] >= 4, f"a same-story lesson matches most dimensions: {got[0]}"


def test_find_related_ignores_unrelated_and_excluded():
    unrelated = _rec("other", what_tried="wire redis sentinel failover",
                     recommendation="Use when redis master dies: promote the replica",
                     root_cause="single point of failure", category="infrastructure")
    assert find_related(_sig(), [unrelated]) == []
    assert find_related(_sig(), [_rec("new_one")], exclude_name="new_one") == []


def test_find_related_empty_dims_never_match():
    sparse = _rec("sparse", what_tried="", recommendation="", root_cause="", actual="",
                  category="", anti_pattern="")
    sparse["expected"] = ""
    assert find_related(_sig(), [sparse]) == []


def test_cmd_learn_prints_near_duplicate_advisory(monkeypatch):
    import agent_cli
    import core.learning.learning_store as lsmod
    ls = LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(), "l.json")))
    twin = _sig(experiment_name="existing_twin")
    ls.record_learning({**twin, "expected_outcome": twin["expected_outcome"]})
    monkeypatch.setattr(lsmod, "get_learning_store", lambda *a, **k: ls)
    s = _sig()
    args = types.SimpleNamespace(agent_id="claude", experiment=s["experiment_name"],
                                 tried=s["what_tried"], result=s["actual_outcome"],
                                 expected="", recommend=s["recommendation"],
                                 category=s["category"], success="yes", confidence="high",
                                 anti_pattern="", json=False)
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert agent_cli.cmd_learn(args) == 0
    out = buf.getvalue()
    assert "[OK] recorded lesson 'new_one'" in out, "the write always lands (advisory never blocks)"
    assert "near-duplicate: overlaps 'existing_twin'" in out
    assert "--experiment existing_twin" in out, "teaches the update-instead path"


def test_cmd_learn_no_advisory_when_updating_same_name(monkeypatch):
    import agent_cli
    import core.learning.learning_store as lsmod
    ls = LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(), "l.json")))
    s = _sig()
    ls.record_learning(s)
    monkeypatch.setattr(lsmod, "get_learning_store", lambda *a, **k: ls)
    args = types.SimpleNamespace(agent_id="claude", experiment=s["experiment_name"],
                                 tried=s["what_tried"], result="updated", expected="",
                                 recommend=s["recommendation"], category=s["category"],
                                 success="yes", confidence="high", anti_pattern="", json=False)
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert agent_cli.cmd_learn(args) == 0
    assert "near-duplicate" not in buf.getvalue(), "a re-record IS the update path -- no nag"
