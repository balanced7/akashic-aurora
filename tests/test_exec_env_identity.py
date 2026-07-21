"""Exec-door identity propagation pin â€” allowlisted children run AS the calling agent.

Live incident 2026-07-21 (deepseek's FIRST self-serve commit): mirror.py's pre-commit
lock hook failed closed on the caller's OWN locks because the subprocess inherited the
LAUNCHING session's AKASHIC_AGENT_ID (=claude -- the runner was spawned from claude's
harness, whose settings export it). The ToolBox knows exactly who is calling
(self.agent_id, ACL-verified at the door); the child env must carry THAT identity,
overriding any inherited value. Lesson: deepseek_mirror_commit_env_var_gap.

  P1  the allowlisted subprocess env carries AKASHIC_AGENT_ID = the door's agent_id,
      OVERRIDING an inherited conflicting value
  P2  no agent identity (interactive/local use) -> env untouched (legacy exact)
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.comm.toolbox as tbmod

REPO = Path(__file__).resolve().parent.parent


class _Stub:
    returncode = 0
    stdout = "ok"
    stderr = ""


def _capture_run(store):
    def fake_run(argv, **kw):
        store["argv"] = argv
        store["env"] = kw.get("env")
        return _Stub()
    return fake_run


@pytest.fixture()
def box(monkeypatch):
    class _Trust:
        def has(self, cap):
            return True
    monkeypatch.setattr("core.trust.registry.resolve", lambda a: _Trust())
    return tbmod.ToolBox(REPO,
                         allow_exec=True, trust=True, allow_secrets=False,
                         confirm=lambda _p: False, agent_id="deepseek")


def test_p1_identity_overrides_inherited_env(box, monkeypatch):
    seen = {}
    monkeypatch.setattr(tbmod.subprocess, "run", _capture_run(seen))
    monkeypatch.setenv("AKASHIC_AGENT_ID", "claude")   # the inherited-launcher value
    out = box.run_command("py agent_cli.py status")
    assert "REFUSED" not in out and seen.get("env") is not None
    assert seen["env"]["AKASHIC_AGENT_ID"] == "deepseek", \
        "the door's verified identity beats the launching session's inherited one"


def test_p2_no_agent_id_leaves_env_alone(monkeypatch):
    class _Trust:
        def has(self, cap):
            return True
    monkeypatch.setattr("core.trust.registry.resolve", lambda a: _Trust())
    b = tbmod.ToolBox(REPO,
                      allow_exec=True, trust=True, allow_secrets=False,
                      confirm=lambda _p: False, agent_id="")
    seen = {}
    monkeypatch.setattr(tbmod.subprocess, "run", _capture_run(seen))
    monkeypatch.setenv("AKASHIC_AGENT_ID", "claude")
    b.run_command("py agent_cli.py status")
    assert seen["env"].get("AKASHIC_AGENT_ID") == "claude", \
        "identity-less use (interactive/local) stays byte-identical"
