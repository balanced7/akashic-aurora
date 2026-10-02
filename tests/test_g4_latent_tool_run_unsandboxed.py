"""G4.P2 latent ADV-033: `tool run --no-sandbox` passed an undefined `REPO` as the child's cwd.

Every unsandboxed run crashed with NameError before launching the tool. The sandboxed path runs
the tool from the repo root (play_sandbox.ROOT), so the unsandboxed override must as well.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("REDIS_DB", "15")

import agent_cli
from core import paths
from core.toolbelt import play_sandbox


def test_tool_run_no_sandbox_runs_from_repo_root(monkeypatch, tmp_path):
    marker = tmp_path / "cwd.txt"
    script = tmp_path / "probe.py"
    script.write_text(
        f"import os, pathlib\npathlib.Path({str(marker)!r}).write_text(os.getcwd(), encoding='utf-8')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(play_sandbox, "find_tool", lambda ref: ("claude", "probe", str(script)))
    args = argparse.Namespace(ref="claude/probe", timeout=0, no_sandbox=True, args=None)

    assert agent_cli.cmd_tool_run(args) == 0

    assert Path(marker.read_text(encoding="utf-8")).resolve() == paths.repo_root().resolve()
