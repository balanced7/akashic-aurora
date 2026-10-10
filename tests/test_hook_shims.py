"""PIN: scripts/hooks/*.py are policy-free shims onto agent/harness/hooks/, the one hook tree.

The two trees drifted twice as full copies -- features written into the copy nobody registered.
Older user-level registrations still point at scripts/hooks/, so those paths stay, but only as
shims that runpy their canonical twin. check_wiring.py fails the gate on the same rule; this pin
also runs one shim as a real process to prove the hand-off works.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))

import check_wiring  # noqa: E402  # sys.path bootstrap


def test_every_scripts_hook_is_a_shim():
    assert check_wiring.hook_shim_violations() == []


def test_every_canonical_claude_hook_has_a_shim():
    canon = {f for f in os.listdir(os.path.join(ROOT, "agent", "harness", "hooks")) if f.startswith("claude_")}
    shims = {f for f in os.listdir(os.path.join(ROOT, "scripts", "hooks")) if f.endswith(".py")}
    assert {f for f in canon if f.endswith(".py")} <= shims


def test_a_shim_flags_a_policy_bearing_file(tmp_path):
    (tmp_path / "claude_trace.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    assert [n for n, _ in check_wiring.hook_shim_violations(str(tmp_path))] == ["claude_trace.py"]


def test_the_shim_runs_the_canonical_hook():
    payload = json.dumps(
        {"tool_name": "mcp__Claude_Browser__navigate", "tool_input": {"url": "https://www.shadertoy.com/view/x"}}
    )
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "hooks", "claude_browser_guard.py")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert '"deny"' in r.stdout, f"the shim did not reach the canonical guard: {r.stdout!r}"
