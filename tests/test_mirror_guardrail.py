"""
Mirror guardrail: the door (boot/handoff) warns when there is uncommitted/unpushed
work -- a slice isn't done until it's mirrored. Enforces in code what AGENTS.md only
states, because agents skip docs.

Run: py -m pytest tests/test_mirror_guardrail.py -q
"""
import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli


def _warn(monkeypatch, status, *, soft=False):
    """Drive _warn_unmirrored against a faked git status; return (returned, stdout)."""
    monkeypatch.setattr(agent_cli, "_working_tree_status", lambda: status)
    buf = io.StringIO()
    with redirect_stdout(buf):
        ret = agent_cli._warn_unmirrored(soft=soft)
    return ret, buf.getvalue()


def test_warns_loud_on_dirty_tree(monkeypatch):
    # W35/B5 contract: bucketed label from porcelain lines (modified-tracked vs untracked),
    # never the old flat "N uncommitted file(s)" sweep imperative.
    ret, out = _warn(monkeypatch,
                     {"ok": True, "dirty": 3, "ahead": 0, "branch": "master",
                      "summary": "AGENTS.md, a.py, b.py",
                      "lines": [" M AGENTS.md", "?? a.py", "?? b.py"]})
    assert ret is True
    assert "UNMIRRORED WORK" in out
    assert "1 modified (tracked), 2 untracked" in out
    assert "mirror.py" in out          # tells the agent exactly what to run


def test_warns_on_unpushed_commits(monkeypatch):
    ret, out = _warn(monkeypatch,
                     {"ok": True, "dirty": 0, "ahead": 2, "branch": "master", "summary": ""})
    assert ret is True
    assert "2 unpushed commit(s)" in out


def test_soft_is_gentle_heads_up(monkeypatch):
    # W35/B5: soft renders the sibling-safe "[i] Unmirrored" block (BY-NAME guidance),
    # never the loud UNMIRRORED WORK nag and never a sweep imperative.
    ret, out = _warn(monkeypatch,
                     {"ok": True, "dirty": 1, "ahead": 0, "branch": "master",
                      "summary": "x.py", "lines": ["?? x.py"]},
                     soft=True)
    assert ret is True
    assert "[i] Unmirrored" in out
    assert "1 untracked" in out
    assert "UNMIRRORED WORK" not in out          # soft != loud
    assert "BY NAME" in out                      # the sibling-safe imperative


def test_silent_when_clean(monkeypatch):
    ret, out = _warn(monkeypatch,
                     {"ok": True, "dirty": 0, "ahead": 0, "branch": "master", "summary": ""})
    assert ret is False
    assert out.strip() == ""


def test_silent_when_git_unavailable(monkeypatch):
    # not a repo / git missing -> ok=False -> never warn (fail-soft, never block the door)
    ret, out = _warn(monkeypatch,
                     {"ok": False, "dirty": 0, "ahead": 0, "branch": "", "summary": ""})
    assert ret is False
    assert out.strip() == ""


def test_status_helper_never_raises(monkeypatch):
    # Even if git itself blows up, the helper returns a safe 'nothing to warn' shape.
    import subprocess

    def _boom(*a, **k):
        raise OSError("git not found")

    monkeypatch.setattr(subprocess, "run", _boom)
    s = agent_cli._working_tree_status()
    assert s == {"ok": False, "dirty": 0, "ahead": 0, "branch": "", "summary": ""}
