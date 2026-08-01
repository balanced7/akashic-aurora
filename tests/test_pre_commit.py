"""Git pre-commit backstop (Concurrency design C4).

Rejects a commit that stages a file a peer holds an advisory lock on; fail-open for
human commits (no AKASHIC_AGENT_ID). Hermetic: monkeypatch the lock check.

Run: py -m pytest tests/test_pre_commit.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.githooks import pre_commit
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


def test_fails_closed_without_agent_id_when_locked(monkeypatch):
    # RC-01 fix: an unset id must NOT silently disable the backstop -- a staged peer-locked file
    # fails closed with a teaching message instead of fail-open.
    _patch_locks(monkeypatch, {"agent_cli.py": "cursor"})
    ok, reason = pre_commit.check_staged(["agent_cli.py"], agent=None)
    assert ok is False and "AKASHIC_AGENT_ID" in reason


def test_allows_without_agent_id_when_nothing_locked(monkeypatch):
    _patch_locks(monkeypatch, {})               # no locks -> a human commit is never blocked
    ok, reason = pre_commit.check_staged(["agent_cli.py"], agent=None)
    assert ok is True and reason == ""


# --- the guard must actually be able to RUN the thing it guards with -------------------------
# T104 moved check_comprehensibility.py into scripts/checkers/ and this hook's invocation was
# not updated. Python then exits rc=2 ("can't open file"), which is NOT the rc==1 the hook
# blocks on and NOT an exception the fail-open except can catch -- so the comprehensibility
# gate silently no-opped on every commit from the move until 2026-08-01, reporting green while
# doing nothing. Fail-open on a guard CRASH is deliberate policy; fail-open on a guard that
# ISN'T THERE is a wiring defect, and it is invisible precisely because it looks like success.

def test_comprehensibility_gate_actually_runs_in_this_repo():
    """BEHAVIOURAL, not shape-coupled: the gate must really execute against the live tree.

    An earlier version of this pin regex-matched the invocation in the source and broke on a
    correct refactor -- a pin that fails on the fix is worse than no pin.
    """
    rc, out = pre_commit._comprehensibility_fast()
    assert "MISSING" not in out, (
        "the comprehensibility gate cannot find its checker, so it is not protecting anything:\n" + out
    )
    assert rc in (0, 1), (
        f"gate returned rc={rc}; only 0 (clean) and 1 (drift) mean it ran. Anything else is wiring:\n{out}"
    )


def test_missing_checker_is_loud_and_distinguishable_from_clean(monkeypatch):
    """Absence must never present as success -- the entire cost of this defect was its silence."""
    monkeypatch.setattr(pre_commit.os.path, "exists", lambda p: False)
    rc, out = pre_commit._comprehensibility_fast()
    assert rc != 0, "a MISSING checker returned rc=0, indistinguishable from a clean pass"
    assert rc != 1, "a MISSING checker must not masquerade as real drift"
    assert "MISSING" in out, "the operator gets no signal that the gate is dead"


def test_dead_gate_warns_but_does_not_block(monkeypatch, capsys):
    """Fail-open on a non-working guard is standing policy; silence is not."""
    monkeypatch.setattr(pre_commit, "_staged_files", lambda: [])
    monkeypatch.setattr(pre_commit, "check_staged", lambda *a, **k: (True, ""))
    monkeypatch.setattr(pre_commit, "_comprehensibility_fast", lambda: (2, "checker MISSING at X"))
    assert pre_commit.main() == 0, "a dead gate must not brick every commit in the repo"
    assert "WARNING" in capsys.readouterr().err, "a dead gate must be LOUD about being dead"
