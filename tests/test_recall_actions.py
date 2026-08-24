"""Contract tests for the importable external recall contract (core/recall/actions.py).

This is the executable spec a dsh-posttool (cordis) plugin mirrors against: the function's
return shape, the ONE kill switch, and the fail-open / error-distinguished semantics. If the
plugin pins `recall_context(session_key, path, command)` and these tests hold, a consumer and
the repo cannot drift.

Run: py tests/test_recall_actions.py   (or via pytest)

Uses an injected fake learning store (the same seam test_recall_at.py uses) so it never touches
canonical Redis; `command=` (not `path=`) keeps it off the lock/bus layer.
"""
import os
import sys
import tempfile

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.actions import recall_context, _EMPTY
from core.recall.at_action import recall_at as _engine


class _FakeStore:
    def __init__(self, recs):
        self._recs = recs
    def load_all_learnings_from_store(self):
        return list(self._recs)


_STORE = _FakeStore([
    {"experiment_name": "spine1_unify", "success": "yes",
     "recommendation": "the consolidator is the one seam; route every source through it"},
])


def test_kill_switch_returns_empty_shape_without_error(monkeypatch):
    """AKASHIC_RECALL_AT_ACTION=0 -> the EMPTY shape, NO error key: 'off' is a chosen normal
    state, not a malfunction, so the plugin must render silence, not 'unavailable'."""
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "0")
    monkeypatch.setattr("core.recall.actions._engine", None)  # ensure engine is never reached
    res = recall_context("deepseek", command="touch the consolidator")
    assert res["shown"] == 0
    assert res["lessons"] == []
    assert "error" not in res


def test_enabled_delegates_to_engine_and_returns_contract_keys(monkeypatch):
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "1")
    monkeypatch.setattr("core.recall.actions._engine", lambda **kw: {"path": None, "command": "x", "query": "x",
                                      "lessons": [{"text": "t", "source": "s"}], "locks": [],
                                      "counter": None, "verbs": [], "shown": 1, "total": 1,
                                      "faithful": True, "confidence": 1.0})
    res = recall_context("deepseek", command="x")
    for key in ("path", "command", "query", "lessons", "locks", "counter", "verbs",
                "shown", "total", "faithful", "confidence"):
        assert key in res
    assert res["shown"] == 1


def test_session_key_maps_to_agent_id(monkeypatch):
    """session_key is a plain agent id and must be forwarded AS the engine's agent_id."""
    seen = {}
    def _fake_engine(**kw):
        seen.update(kw)
        return dict(_EMPTY)
    monkeypatch.setattr("core.recall.actions._engine", _fake_engine)
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "1")
    recall_context("deepseek", command="x")
    assert seen.get("agent_id") == "deepseek"


def test_missing_session_key_fails_loud_not_attrs_to_env(monkeypatch):
    """DSH identity finding: an external harness may inherit a WRONG AKASHIC_AGENT_ID (the DSH
    seat inherits Claude Code's). recall_context must NOT fall back to env -- it fails loud with
    error=MissingSessionKey so attribution never silently lands on a foreign agent."""
    monkeypatch.setenv("AKASHIC_AGENT_ID", "claude")     # the inherited, WRONG value
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "1")
    monkeypatch.setattr("core.recall.actions._engine", None)  # engine must never be reached
    res = recall_context(None, command="x")              # session_key explicitly missing
    assert res["error"] == "MissingSessionKey"
    assert res["shown"] == 0


def test_engine_exception_fails_open_with_error_key(monkeypatch):
    """ANY engine exception -> empty shape but WITH error/error_detail (never raises): the plugin
    must distinguish 'unavailable' from 'nothing relevant', and must never block on this call."""
    def _boom(**kw):
        raise RuntimeError("store down")
    monkeypatch.setattr("core.recall.actions._engine", _boom)
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "1")
    res = recall_context("deepseek", command="x")
    assert res["shown"] == 0
    assert res["error"] == "RuntimeError"
    assert "store down" in res["error_detail"]
