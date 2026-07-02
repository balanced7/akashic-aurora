"""Git-safety policy + hook adapters (Concurrency design C0).

The rule: block blanket git staging so one agent can't bundle the other's unreviewed
work (FM1). One rulebook (agent/policy/git_guard) consulted by both hooks.

Run: py -m pytest tests/test_git_guard.py -q
"""
import io
import json
import os
import sys
from contextlib import redirect_stdout

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.policy.git_guard import check_git_command
from scripts.hooks import claude_pretooluse, cursor_beforeshell


# --------------------------------------------------------------- policy: blocked
@pytest.mark.parametrize("cmd", [
    "git add -A",
    "git add .",
    "git add --all",
    "git add -A .",
    "git add :/",
    "cd subdir && git add -A",
    "git status && git add . && git commit -m x",
    "git commit -am 'wip'",
    "git commit -a",
    "git commit -a -m 'wip'",
])
def test_blocks_blanket_staging(cmd):
    allowed, reason = check_git_command(cmd)
    assert allowed is False
    assert "BLOCKED" in reason
    assert "mirror.py" in reason          # tells the agent the correct next action


# --------------------------------------------------------------- policy: allowed
@pytest.mark.parametrize("cmd", [
    "git add foo.py",
    "git add path/to/file.py tests/test_x.py",
    "git add -p",                         # interactive patch is selective, not blanket
    "git commit -m 'msg'",
    "git commit -m 'msg with a in it'",   # -m, not -a
    "git status",
    "git diff --cached",
    "git push origin master",
    "py scripts/mirror.py 'msg' a.py",
    "ls && echo add -A",                  # not a git command
    "",
])
def test_allows_safe_commands(cmd):
    allowed, reason = check_git_command(cmd)
    assert allowed is True
    assert reason == ""


def test_never_raises_on_garbage():
    for junk in [None, "git add '", "\x00\x00", "git add " + "x" * 10000]:
        allowed, _ = check_git_command(junk)  # must not raise
        assert isinstance(allowed, bool)


# --------------------------------------------------------- Claude hook adapter
def _run_claude(payload):
    src, out = io.StringIO(json.dumps(payload)), io.StringIO()
    real = sys.stdin
    sys.stdin = src
    try:
        with redirect_stdout(out):
            rc = claude_pretooluse.main()
    finally:
        sys.stdin = real
    return rc, out.getvalue()


def test_claude_hook_denies_blanket_add():
    rc, out = _run_claude({"tool_name": "Bash", "tool_input": {"command": "git add -A"}})
    assert rc == 0                         # exit 0 + JSON, NOT exit 1 (footgun)
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "BLOCKED" in decision["permissionDecisionReason"]


def test_claude_hook_allows_pathspec_add():
    rc, out = _run_claude({"tool_name": "Bash", "tool_input": {"command": "git add foo.py"}})
    assert rc == 0
    assert out.strip() == ""               # silent allow


def test_claude_hook_guards_powershell_like_bash():
    """PowerShell is the harness's PRIMARY shell tool on Windows -- a Bash-only filter would route
    every shell command around the git guard (the 2026-07-02 blindspot). Same rulebook, both shells."""
    rc, out = _run_claude({"tool_name": "PowerShell", "tool_input": {"command": "git add -A"}})
    assert rc == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_claude_hook_ignores_non_bash_tool():
    rc, out = _run_claude({"tool_name": "Edit", "tool_input": {"file_path": "x"}})
    assert rc == 0
    assert out.strip() == ""


def test_claude_hook_ignores_unknown_tool():
    rc, out = _run_claude({"tool_name": "Glob", "tool_input": {"command": "git add -A"}})
    assert rc == 0
    assert out.strip() == ""


def test_claude_hook_fails_open_on_bad_input():
    src, out = io.StringIO("not json"), io.StringIO()
    real = sys.stdin
    sys.stdin = src
    try:
        with redirect_stdout(out):
            rc = claude_pretooluse.main()
    finally:
        sys.stdin = real
    assert rc == 0 and out.getvalue().strip() == ""   # unparseable -> allow, never block by accident


# --------------------------------------------------------- Cursor hook adapter
def _run_cursor(payload):
    src, out = io.StringIO(json.dumps(payload)), io.StringIO()
    real = sys.stdin
    sys.stdin = src
    try:
        with redirect_stdout(out):
            cursor_beforeshell.main()
    finally:
        sys.stdin = real
    return json.loads(out.getvalue())


def test_cursor_hook_denies_blanket_add():
    res = _run_cursor({"command": "git add ."})
    assert res["permission"] == "deny"
    assert "BLOCKED" in res["agentMessage"]


def test_cursor_hook_allows_pathspec():
    res = _run_cursor({"command": "git add foo.py"})
    assert res["permission"] == "allow"


def test_both_hooks_share_one_rulebook():
    # same command -> same verdict in both adapters (no drift)
    cmd = "git commit -am wip"
    _, claude_out = _run_claude({"tool_name": "Bash", "tool_input": {"command": cmd}})
    cursor_res = _run_cursor({"command": cmd})
    assert json.loads(claude_out)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert cursor_res["permission"] == "deny"
