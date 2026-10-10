"""
K0 · true the denominator (C8-3) — the Crucible's first slice.
Cites docs/library/design/20260701_institutional-knowledge-arc-reconciled-d_27e77b.md (K0) + failure-ledger C8-3.

The scar: claude_pretooluse.py was registered on TWO surfaces (project-relative +
user-absolute); both fired per call, log_injection() counted twice, and the funnel's
`surfaced` denominator ran ~2x hot — the quantifier was gauging the gauge.

Laws pinned:
  1. SINGLE SURFACE — the hook appears in AT MOST ONE of the settings files in play
     (user, project shared, project local); agent/harness/install.py enforces it at install.
  2. ATOMIC DEDUP BACKSTOP — even if double-registration ever returns, an identical
     payload within the window is a silent no-op (O_EXCL marker; no load-then-mark race).
Run: py -m pytest tests/test_k0_gauge_truth.py -q
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _hook_count(settings_path) -> int:
    if not os.path.exists(settings_path):
        return 0
    doc = json.loads(Path(settings_path).read_text(encoding="utf-8"))
    blocks = (doc.get("hooks") or {}).get("PreToolUse") or []
    n = 0
    for b in blocks:
        for h in b.get("hooks", []):
            if "claude_pretooluse.py" in str(h.get("command", "")):
                n += 1
    return n


def test_single_registration_surface():
    """C8-3 root cause pinned: the recall hook lives on exactly ONE settings surface.

    Which surface is the installer's choice now (`agent_cli.py hooks install --scope user|project`);
    the invariant is that it is never two -- and the installer refuses to make it two."""
    surfaces = (
        os.path.join(REPO, ".claude", "settings.json"),
        os.path.join(REPO, ".claude", "settings.local.json"),
        os.path.join(os.path.expanduser("~"), ".claude", "settings.json"),
    )
    with_hook = [p for p in surfaces if _hook_count(p) > 0]
    assert len(with_hook) <= 1, (
        "claude_pretooluse.py registered on MORE THAN ONE settings surface -- every matched "
        f"call double-fires and the funnel denominator lies (C8-3): {with_hook}. "
        "Run `agent_cli.py hooks status`, then `hooks uninstall` on all but one scope."
    )


def test_dedup_guard_is_atomic_and_window_bound(tmp_path, monkeypatch):
    """The backstop: first fire passes, identical payload within the window skips, and a
    DIFFERENT payload never skips. Atomic O_EXCL -- no load-then-mark race to lose."""
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    import importlib

    from agent.harness.hooks import claude_pretooluse as hook

    importlib.reload(hook)
    payload = {"session_id": "s1", "tool_name": "Bash", "tool_input": {"command": "ls"}}
    assert hook._dedup_should_skip(payload) is False, "first fire must pass"
    assert hook._dedup_should_skip(payload) is True, "identical second fire must skip"
    other = {"session_id": "s1", "tool_name": "Bash", "tool_input": {"command": "pwd"}}
    assert hook._dedup_should_skip(other) is False, "a different payload never skips"
