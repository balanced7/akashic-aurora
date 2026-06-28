"""Git pre-commit backstop (Concurrency design C4).

Rejects a commit that stages a file a peer holds an advisory lock on; fail-open for
human commits (no AKASHIC_AGENT_ID). Hermetic: monkeypatch the lock check.

Run: py -m pytest tests/test_pre_commit.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.hooks import pre_commit
import core.comm.locks as L


def _patch_locks(monkeypatch, locked_by):
    """Fake: any path in `locked_by` is held by that peer; others are free."""
    def fake(path, agent, client=None):
        who = locked_by.get(path)
        if who and who != agent:
            return {"conflict": True, "held_by": who, "reason": f"locked by {who}"}
        return {"conflict": False, "held_by": None, "reason": ""}
    monkeypatch.setattr(L, "path_conflict", fake)


def test_blocks_commit_of_peer_locked_file(monkeypatch):
    _patch_locks(monkeypatch, {"scripts/gemini_web.py": "cursor"})
    ok, reason = pre_commit.check_staged(
        ["scripts/gemini_web.py", "agent_cli.py"], agent="claude")
    assert ok is False
    assert "scripts/gemini_web.py -> locked by cursor" in reason
    assert "agent_cli.py" not in reason          # only the conflicting file is named


def test_allows_when_no_peer_lock(monkeypatch):
    _patch_locks(monkeypatch, {})
    ok, reason = pre_commit.check_staged(["agent_cli.py"], agent="claude")
    assert ok is True and reason == ""


def test_allows_own_locked_file(monkeypatch):
    _patch_locks(monkeypatch, {"agent_cli.py": "claude"})   # I hold it -> fine to commit
    ok, _ = pre_commit.check_staged(["agent_cli.py"], agent="claude")
    assert ok is True


def test_fail_open_without_agent_id(monkeypatch):
    _patch_locks(monkeypatch, {"agent_cli.py": "cursor"})   # would conflict...
    ok, reason = pre_commit.check_staged(["agent_cli.py"], agent=None)   # ...but no agent id
    assert ok is True and reason == ""          # never block a human commit
