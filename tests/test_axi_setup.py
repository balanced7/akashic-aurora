"""Pins for `setup` after the AXI conversion: an agent never meets a question, and gets the run as
data; a person keeps the narrated, question-by-question tutorial.

Every case runs against a throwaway HOME and repo with the installer and subprocess faked, so
nothing here touches a real settings file, git hook or MCP registration.

Run: uv run pytest tests/test_axi_setup.py -q
"""

import subprocess
from argparse import Namespace

import pytest

import agent_cli
import core.paths
from agent.harness import install as inst
from agent.harness import onboard


class _FakeInst:
    Result = inst.Result
    read_config = staticmethod(inst.read_config)
    write_config = staticmethod(inst.write_config)

    def __init__(self, tmp):
        self.tmp = tmp
        self.installs = []

    def install(self, h, scope, project=None, dry_run=False):
        self.installs.append((h, scope, dry_run))
        return inst.Result(path=self.tmp / f"{h}-{scope}.json", action="install", added=["a", "b"])

    def status(self, project=None):
        return [
            {"harness": "claude", "scope": "user", "path": "/h/settings.json", "exists": True,
             "installed": ["x", "y"], "stale": [], "disabled": 0},
            {"harness": "codex", "scope": "user", "path": "/h/hooks.json", "exists": False,
             "installed": [], "stale": [], "disabled": 0},
        ]  # fmt: skip

    def status_lines(self, project=None):
        return ["status-line-1"]


@pytest.fixture
def world(tmp_path, monkeypatch):
    home, repo = tmp_path / "home", tmp_path / "repo"
    home.mkdir()
    repo.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.setattr(core.paths, "repo_root", lambda *a, **k: repo)
    monkeypatch.setattr(core.paths, "launcher", lambda: None)
    monkeypatch.setattr(core.paths, "cli_command", lambda: "AUR")
    monkeypatch.setattr(onboard, "_launcher", lambda: "PYL")
    monkeypatch.setattr(onboard, "detect_harnesses", list)
    monkeypatch.setattr(onboard, "_git_user", lambda cwd: "Test Op <op@example.com>")
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("input() called in agent mode"))
    fake = _FakeInst(tmp_path)
    monkeypatch.setattr(onboard, "inst", fake)
    calls = []

    def fake_run(cmd, **kw):
        calls.append((cmd, kw))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(onboard.subprocess, "run", fake_run)
    return Namespace(tmp=tmp_path, inst=fake, calls=calls)


def _args(**kw):
    base = {"yes": True, "dry_run": True, "harness": ["claude"], "scope": None, "project": None,
            "agent_id": "seat-1", "operator": None}  # fmt: skip
    base.update(kw)
    return Namespace(**base)


def test_agent_mode_without_yes_refuses_instead_of_asking(world, capsys):
    code = agent_cli.cmd_setup(_args(yes=False))
    text = capsys.readouterr().out
    assert code == 2
    assert "code: INTERACTIVE" in text
    assert "setup --yes --dry-run --harness claude --agent-id seat-1" in text
    assert world.inst.installs == []


def test_agent_mode_prints_the_run_as_one_document(world, capsys):
    code = agent_cli.cmd_setup(_args())
    text = capsys.readouterr().out
    assert code == 0
    assert text.startswith("dry_run: true\nsteps[")
    assert '2/5,"claude hooks: user"' in text
    assert "AKASHIC_AGENT_ID=seat-1 would be set" in text
    assert "later[" in text
    assert "{command,does}:" in text
    assert "hooks[1]{harness,scope,installed,path}:" in text
    assert "claude,user,2,/h/settings.json" in text
    # the dry run's next step is the same run for real
    assert "setup --yes --harness claude --agent-id seat-1" in text
    # nothing narrated around the document: no banner, no echoed defaults
    assert "Akashic Aurora setup" not in text
    assert " -> " not in text


def test_a_real_agent_run_captures_child_output(world, capsys):
    agent_cli.cmd_setup(_args(dry_run=False, harness=None))
    text = capsys.readouterr().out
    assert "5/5,git hooks installed" in text
    githook = [kw for cmd, kw in world.calls if isinstance(cmd, list)]
    assert githook == [{"check": False, "capture_output": True, "text": True}]
    assert onboard._report is None  # collecting never outlives the run


def test_human_mode_keeps_the_narrated_tutorial(world, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    assert agent_cli.cmd_setup(_args()) == 0
    text = capsys.readouterr().out
    assert "Akashic Aurora setup." in text
    assert "[2/5] claude hooks: user" in text
    assert "-> later: AUR hooks install --harness claude --scope user" in text
    assert "  status-line-1" in text
