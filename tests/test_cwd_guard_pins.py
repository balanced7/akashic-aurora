"""PIN: the cwd-guard (_cwd_drift) in the LIVE PreToolUse hook, scripts/hooks/claude_pretooluse.py.

Defer 21f178ad26 (claude, 2026-09-01): "write the RED pin for _cwd_drift ... drift speaks, anchored
stays guard-quiet, in-repo untouched -- the 3-case stdin drill from 2026-09-01 is the spec". The
guard shipped in b095caa5 (out-of-scope branch) and 5b65b7ab (in-scope-by-text branch) with stdin
drill receipts but no committed pin; M3 wants the acceptance durable in the suite.

THE MECHANISM. The harness shell resets to E:\\ whenever it rebuilds. A repo-shaped command
(scripts/, core/, agent_cli.py ...) issued from that drifted cwd either FALSE-CLEANS (grep over
absent dirs reports zero hits) or dies file-not-found (py agent_cli.py). Before b095caa5 the
out-of-scope branch of main() was a silent no-op by design (user-level registration must stay
quiet outside this repo), so the reset was invisible. _cwd_drift is ORTHOGONAL to scope: it emits
one loud additionalContext line -- never a deny -- on BOTH scope branches (out-of-scope: the line
alone; in-scope: folded in FRONT of recall), and stays quiet for anchored commands
(cd /e/AI-Setup && ..., absolute repo paths), for a cwd already inside E:\\AI-Setup, and for
non-repo work that mentions no repo marker.

WHICH FILE. The hook exists twice: agent/harness/hooks/claude_pretooluse.py (what the sibling pins
import) and scripts/hooks/claude_pretooluse.py (what the user-level registration runs). Only the
scripts/ copy carries the guard. This pin loads the LIVE copy by path under a unique module name;
a pin written by copying the sibling pins' import would test the wrong file and stay green while
the live guard regressed. RED against b095caa5~1 (the tree before the guard existed); GREEN at HEAD.

Recall is replaced by a sentinel at the hook's own seam (_recall_context), so every case is
Redis-free by construction and the FOLD ORDER (drift line first, recall after) is pinned rather
than assumed. scope.py roots itself at the checkout it lives in, so the one case that needs the
in-scope-BY-CWD branch pins that root to the production topology (E:\\AI-Setup); a worktree would
otherwise route it through the out-of-scope branch and certify nothing.

Run: py -m pytest tests/test_cwd_guard_pins.py -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import uuid
from contextlib import redirect_stdout

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

LIVE_HOOK = os.path.join(ROOT, "scripts", "hooks", "claude_pretooluse.py")
SENTINEL = "SENTINEL-RECALL-AT-ACTION"
DRIFTED = "E:\\"            # where the harness shell lands after a rebuild
REPO = "E:\\AI-Setup"       # the production topology the guard is written against


@pytest.fixture(scope="module")
def hook():
    """The LIVE hook, loaded by path under a unique module name so it never aliases
    agent.harness.hooks.claude_pretooluse (test_git_guard / test_locks) or the top-level
    `claude_pretooluse` that test_k0_gauge_truth imports.

    main() imports its policy modules lazily. The first import under agent.* in a process
    resolves the Redis endpoint transitively, and in a checkout that declares no world (a
    worktree; .aurora-world is instance-local) core/foundation/redis_connection.py:87 prints a
    `[world] UNKNOWN checkout` line ON STDOUT, once. In-process that line would land inside
    whichever captured main() happens to import first -- an order-dependent red about the
    environment, not the guard -- so those imports are warmed here, outside every capture.
    The per-call contract below (exactly one JSON line) stays strict."""
    spec = importlib.util.spec_from_file_location("_cwd_guard_pin_live_pretooluse", LIVE_HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    import agent.harness.scope      # noqa: F401  -- _in_scope
    import agent.harness.guards     # noqa: F401  -- _check_bash
    import agent.policy.git_guard   # noqa: F401  -- git_veto
    return mod


@pytest.fixture
def quiet_recall(hook, monkeypatch):
    """Recall swapped for a sentinel at the hook's own seam. The pin is about the guard and how
    it COMPOSES with recall, never about what recall says -- and never about Redis."""
    monkeypatch.setattr(hook, "_recall_context", lambda data: SENTINEL)


def _payload(cmd: str, cwd: str, tool: str = "Bash") -> dict:
    # A FRESH session id per payload: main()'s O_EXCL dedup marker (K0/C8-3) keys on
    # (session, tool, payload) and would silently skip a repeated case as a double-fire.
    return {"session_id": uuid.uuid4().hex, "tool_name": tool,
            "tool_input": {"command": cmd}, "cwd": cwd}


def _run(hook, payload: dict):
    """Drive main() the way the harness does: JSON on stdin, JSON (or nothing) on stdout."""
    src, out = io.StringIO(json.dumps(payload)), io.StringIO()
    real = sys.stdin
    sys.stdin = src
    try:
        with redirect_stdout(out):
            rc = hook.main()
    finally:
        sys.stdin = real
    return rc, out.getvalue()


def _context(out: str) -> str:
    """The one hookSpecificOutput the hook printed -- a context line, never a decision."""
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected exactly one JSON line on stdout, got: {out!r}"
    hso = json.loads(lines[0])["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert "permissionDecision" not in hso, (
        f"the cwd-guard is a loud LINE, never a deny -- but the hook decided: {hso!r}")
    return hso["additionalContext"]


# ------------------------------------------------------------- _cwd_drift, the pure function
# Pinned directly as well as through main() so the contract survives a future reshuffle of
# main()'s branches (the 5b65b7ab class: a guard that exists but is not wired on one branch).

@pytest.mark.parametrize("tool, cwd, cmd", [
    ("Bash", DRIFTED, "grep -rn foo scripts/ core/"),               # false-clean class (b095caa5)
    ("Bash", DRIFTED, "py agent_cli.py boot claude"),                # in scope by text (5b65b7ab)
    ("PowerShell", DRIFTED, "py agent_cli.py status"),               # the PRIMARY shell on Windows
    ("Bash", "C:\\Users\\someone", "py -m pytest tests/test_x.py"),  # any non-repo cwd, not only E:\
], ids=["grep-false-clean", "agent_cli-in-scope-by-text", "powershell", "home-cwd"])
def test_drift_speaks(hook, tool, cwd, cmd):
    line = hook._cwd_drift({"tool_name": tool, "tool_input": {"command": cmd}, "cwd": cwd})
    assert line.startswith("[cwd-guard]"), line
    assert cwd in line and "cd /e/AI-Setup" in line     # names the drift AND the remedy
    assert "\n" not in line                              # ONE loud line


@pytest.mark.parametrize("tool, cwd, cmd", [
    ("Bash", DRIFTED, "cd /e/AI-Setup && grep -rn foo scripts/"),               # anchored, git-bash
    ("Bash", DRIFTED, "py E:/AI-Setup/agent_cli.py status"),                    # anchored, absolute
    ("PowerShell", DRIFTED, "Set-Location E:\\AI-Setup; py agent_cli.py status"),  # anchored, win
    ("Bash", REPO, "grep -rn foo scripts/"),                                     # cwd IS the repo
    ("Bash", "e:/ai-setup/", "grep -rn foo scripts/"),                           # ... any spelling
    ("Bash", REPO + "\\tests", "py agent_cli.py status"),                        # ... or inside it
    ("Bash", DRIFTED, "ls"),                                                     # non-repo work
    ("Edit", DRIFTED, "grep -rn foo scripts/"),                                  # file tools: by path
], ids=["anchored-cd", "anchored-abs-path", "anchored-powershell", "in-repo", "in-repo-spelling",
        "in-repo-subdir", "no-marker", "file-tool"])
def test_guard_stays_quiet(hook, tool, cwd, cmd):
    assert hook._cwd_drift({"tool_name": tool, "tool_input": {"command": cmd}, "cwd": cwd}) == ""


def test_guard_fails_open_on_odd_payloads(hook):
    """A bare-string tool_input (the 674f498b crash class) and a missing cwd must never raise --
    a guard that can brick the hook is worse than a silent one."""
    assert hook._cwd_drift({"tool_name": "Bash", "tool_input": "grep -rn foo scripts/",
                            "cwd": DRIFTED}) == ""
    assert isinstance(hook._cwd_drift({"tool_name": "Bash", "tool_input": {"command": "ls"}}), str)


# ------------------------------------------------------- main(): the 2026-09-01 stdin drill

def test_drift_speaks_on_the_out_of_scope_branch(hook, quiet_recall):
    """Case 1 (b095caa5): repo-shaped command, drifted cwd, OUT of scope by text. The line is the
    WHOLE output: the out-of-scope branch still runs no recall (user-level registration stays safe
    outside this repo) -- it just stopped being silent about the drift."""
    rc, out = _run(hook, _payload("grep -rn foo scripts/ core/", DRIFTED))
    assert rc == 0
    ctx = _context(out)
    assert ctx.startswith("[cwd-guard]"), ctx
    assert SENTINEL not in ctx


def test_drift_speaks_on_the_in_scope_by_text_branch(hook, quiet_recall):
    """Case 2 (5b65b7ab): `py agent_cli.py ...` is IN scope by its text (agent/harness/scope.py)
    while its cwd is drifted -> file-not-found. Found live minutes after b095caa5 shipped, because
    the first cut spoke only on the out-of-scope branch. Folded in FRONT of recall."""
    rc, out = _run(hook, _payload("py agent_cli.py boot claude", DRIFTED))
    assert rc == 0
    ctx = _context(out)
    assert ctx.startswith("[cwd-guard]"), ctx
    assert ctx.endswith("\n" + SENTINEL), ctx           # drift first, recall after, nothing lost


def test_anchored_command_stays_guard_quiet(hook, quiet_recall):
    """Case 3: the remedy the guard prescribes must not trip the guard. Anchored -> in scope by
    text -> recall exactly as before, and the context carries NO drift line."""
    rc, out = _run(hook, _payload("cd /e/AI-Setup && grep -rn foo scripts/", DRIFTED))
    assert rc == 0
    assert _context(out) == SENTINEL


def test_in_repo_call_is_untouched(hook, quiet_recall, monkeypatch):
    """Case 4: cwd inside the repo, plain repo-relative command -- in scope BY CWD. scope.py roots
    itself at the checkout it lives in, so from a worktree this case would silently take the
    out-of-scope branch; pin the root to the production topology so the in-scope path is the one
    under test wherever the suite runs."""
    import agent.harness.scope as scope
    monkeypatch.setattr(scope, "_ROOT", os.path.normcase(REPO))
    rc, out = _run(hook, _payload("grep -rn foo scripts/", REPO))
    assert rc == 0
    assert _context(out) == SENTINEL                      # byte-for-byte the pre-guard context


def test_non_repo_work_stays_silent(hook, quiet_recall):
    """Case 5: `ls` from E:\\ names no repo marker. The silent out-of-scope no-op that makes
    user-level registration safe is preserved byte-for-byte: EMPTY stdout, not an empty JSON."""
    rc, out = _run(hook, _payload("ls", DRIFTED))
    assert rc == 0
    assert out == ""


def test_guard_never_changes_the_decision(hook, quiet_recall):
    """A loud line, never a deny -- and never an allow either: the blanket-staging veto still
    fires on a drifted, in-scope-by-text command. The guard informs; it does not decide."""
    rc, out = _run(hook, _payload("py agent_cli.py status && git add -A", DRIFTED))
    assert rc == 0
    hso = json.loads(out)["hookSpecificOutput"]
    assert hso["permissionDecision"] == "deny"
    assert "BLOCKED" in hso["permissionDecisionReason"]
