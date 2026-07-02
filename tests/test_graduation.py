"""Lesson graduation (2026-07-02, Greptile-informed): a lesson whose rule is now ENFORCED by
automation stops competing for recall surface slots but keeps its history. Hermetic: every
store here is an isolated FileStore; the recall cache warm is monkeypatched to a no-op."""
import io
import os
import sys
import tempfile
import types
from contextlib import redirect_stdout

import isolate_canonical  # noqa: F401 -- isolate file store + Redis db BEFORE foundation import

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.learning.learning_store import LearningStore, is_graduated


def _isolated_ls():
    return LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(), "l.json")))


def _lesson(name="git_blanket", **kw):
    return {"experiment_name": name, "agent_id": "claude", "what_tried": "git add -A",
            "recommendation": "never blanket-stage in a shared tree", "success": "yes", **kw}


def test_mark_graduated_roundtrip_and_undo():
    ls = _isolated_ls()
    ls.record_learning(_lesson())
    rec = ls._load_experiment("git_blanket")
    assert not is_graduated(rec)

    assert ls.mark_graduated("git_blanket", "git-guard PreToolUse hook (C0)") is True
    rec = ls._load_experiment("git_blanket")
    assert is_graduated(rec) and rec["enforced_by"] == "git-guard PreToolUse hook (C0)"

    assert ls.mark_graduated("git_blanket", undo=True) is True
    assert not is_graduated(ls._load_experiment("git_blanket"))


def test_mark_graduated_unknown_lesson_is_false():
    assert _isolated_ls().mark_graduated("does_not_exist", "anything") is False


def test_re_record_does_not_clear_graduation():
    """PIN the hset-merge property: updating a lesson via record_learning must never blank
    graduation state (record_learning coerces unset fields to '' -- only for ITS OWN fields)."""
    ls = _isolated_ls()
    ls.record_learning(_lesson())
    ls.mark_graduated("git_blanket", "git-guard hook")
    ls.record_learning(_lesson(recommendation="updated wording"))
    rec = ls._load_experiment("git_blanket")
    assert is_graduated(rec) and rec["recommendation"] == "updated wording"


def test_graduated_lesson_never_enters_the_recall_cache():
    from core.recall.at_action import _project_items
    recs = [_lesson("live_one"),
            {**_lesson("graduated_one"), "graduated": "2026-07-02T01:00:00", "enforced_by": "hook"}]
    sources = [it["source"] for it in _project_items(recs)]
    assert "learn:experiment:live_one" in sources
    assert "learn:experiment:graduated_one" not in sources


def test_boot_learning_loader_excludes_graduated():
    from context.learning_loader import load_learnings_ranked_by_relevance
    ls = _isolated_ls()
    ls.record_learning(_lesson("live_git_lesson"))
    ls.record_learning(_lesson("graduated_git_lesson"))
    ls.mark_graduated("graduated_git_lesson", "git-guard hook")
    got = [r["source"] for r in load_learnings_ranked_by_relevance(
        "git staging shared tree", top_k=8, learning_store=ls)]
    assert "live_git_lesson" in got and "graduated_git_lesson" not in got


def _run_cmd(monkeypatch, ls, **argv):
    import agent_cli
    import core.learning.learning_store as lsmod
    import core.recall.at_action as aa
    monkeypatch.setattr(lsmod, "get_learning_store", lambda *a, **k: ls)
    monkeypatch.setattr(aa, "warm_cache", lambda *a, **k: 0)   # never touch the real tempdir cache
    defaults = {"agent_id": "claude", "experiment": None, "enforced_by": None,
                "undo": False, "json": False}
    args = types.SimpleNamespace(**{**defaults, **argv})
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = agent_cli.cmd_graduate(args)
    return rc, buf.getvalue()


def test_cmd_graduate_errors_teach(monkeypatch):
    rc, out = _run_cmd(monkeypatch, _isolated_ls())                     # no experiment
    assert rc == 2 and "Example:" in out
    rc, out = _run_cmd(monkeypatch, _isolated_ls(), experiment="nope", enforced_by="hook")
    assert rc == 1 and "list" in out                                    # unknown -> points at list


def test_cmd_graduate_and_list_tag(monkeypatch):
    ls = _isolated_ls()
    ls.record_learning(_lesson())
    rc, out = _run_cmd(monkeypatch, ls, experiment="git_blanket", enforced_by="git-guard hook (C0)")
    assert rc == 0 and "[OK] graduated 'git_blanket'" in out
    # the full-corpus view keeps it, wearing the tag (history preserved, reason visible)
    import agent_cli
    args = types.SimpleNamespace(query="", json=False, full=None)
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert agent_cli.cmd_recall(args) == 0
    listing = buf.getvalue()
    assert "git_blanket [graduated]" in listing


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
