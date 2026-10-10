"""PIN: `agent_cli.py setup` (agent/harness/onboard.py) -- the onboarding sequence.

Contract: each step asks one question (or takes its default under --yes), does the thing,
and prints the `-> later:` command that does the same later; --dry-run writes nothing; a
failing installer stops only that harness. Every case runs against a throwaway HOME and repo,
with the installer, subprocess and core.paths lookups faked, so nothing here touches a real
settings file, git hook or MCP registration.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.paths
from agent.harness import install as inst
from agent.harness import onboard

# -- Asker ------------------------------------------------------------------------------------


def test_asker_assume_yes_returns_default_without_input(monkeypatch, capsys):
    """--yes answers with the default and echoes the question, never calling input()."""
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("input() called under --yes"))
    ans = onboard.Asker(True).ask("scope?", "user", ("user", "project"))
    assert ans == "user"
    assert "scope? [user/project] -> user" in capsys.readouterr().out


def test_asker_reprompts_until_answer_is_a_choice(monkeypatch, capsys):
    """An answer outside the choices is refused and asked again; blank means the default."""
    answers = iter(["bogus", "project"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    assert onboard.Asker(False).ask("scope?", "user", ("user", "project")) == "project"
    assert "please answer one of: user, project" in capsys.readouterr().out
    monkeypatch.setattr("builtins.input", lambda *_: "   ")
    assert onboard.Asker(False).ask("scope?", "user", ("user", "project")) == "user"


def test_asker_free_text_and_yes_helper(monkeypatch):
    """With no choices any answer is accepted; yes() maps y/n to a bool."""
    monkeypatch.setattr("builtins.input", lambda *_: "/some/dir")
    assert onboard.Asker(False).ask("dir?", "here") == "/some/dir"
    monkeypatch.setattr("builtins.input", lambda *_: "n")
    assert onboard.Asker(False).yes("ok?", True) is False
    assert onboard.Asker(True).yes("ok?", True) is True
    assert onboard.Asker(True).yes("ok?", False) is False


# -- small helpers ----------------------------------------------------------------------------


def test_detect_harnesses_by_binary_or_dot_dir(tmp_path, monkeypatch):
    """A harness counts as present if any of its binaries is on PATH or ~/.<harness> exists."""
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".codex").mkdir()
    monkeypatch.setattr(onboard.shutil, "which", lambda b: "/bin/x" if b == "cursor-agent" else None)
    assert onboard.detect_harnesses() == ["codex", "cursor"]


def test_launcher_falls_back_when_core_paths_raises(monkeypatch):
    """_launcher uses core.paths.python_launcher, and a broken lookup degrades to python3/py."""
    monkeypatch.setattr(core.paths, "python_launcher", lambda: "uv run")
    assert onboard._launcher() == "uv run"

    def boom():
        raise RuntimeError("no")

    monkeypatch.setattr(core.paths, "python_launcher", boom)
    assert onboard._launcher() == ("py" if os.name == "nt" else "python3")


def test_print_result_reports_added_skipped_notes_or_up_to_date(tmp_path, capsys):
    """_print_result names each kind of outcome, and says 'already up to date' when there is none."""
    p = tmp_path / "settings.json"
    onboard._print_result(inst.Result(path=p, action="install", added=["a", "b"], skipped=["s"], notes=["n1"]))
    out = capsys.readouterr().out
    assert f"2 hook(s) registered in {p}" in out
    assert "skipped s -- one surface per hook" in out
    assert "[hooks] n1" in out
    onboard._print_result(inst.Result(path=p, action="install"))
    assert f"{p} already up to date" in capsys.readouterr().out


def test_skills_link_ok_only_for_symlink_to_agents_skills(tmp_path):
    """The skills check passes only when .claude/skills is a symlink resolving to .agents/skills."""
    (tmp_path / ".agents" / "skills").mkdir(parents=True)
    (tmp_path / ".claude").mkdir()
    assert onboard._skills_link_ok(tmp_path) is False
    (tmp_path / ".claude" / "skills").symlink_to(tmp_path / ".agents" / "skills")
    assert onboard._skills_link_ok(tmp_path) is True


def _write_mcp_register(repo: Path, body: str) -> None:
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    (repo / "scripts" / "mcp_register.py").write_text(body, encoding="utf-8")


def test_mcp_command_loads_registration_command_from_repo_script(tmp_path):
    """_mcp_command imports scripts/mcp_register.py from the repo and returns its command."""
    _write_mcp_register(tmp_path, "def registration_command(repo):\n    return f'claude mcp add x {repo.name}'\n")
    assert onboard._mcp_command(tmp_path) == f"claude mcp add x {tmp_path.name}"


def test_mcp_command_is_none_when_script_missing_or_broken(tmp_path):
    """A missing or raising mcp_register.py yields None rather than an error."""
    assert onboard._mcp_command(tmp_path) is None
    _write_mcp_register(tmp_path, "raise ImportError('broken')\n")
    assert onboard._mcp_command(tmp_path) is None


# -- run() ------------------------------------------------------------------------------------


class FakeInst:
    """Records installer calls; claude installs target a settings file under tmp."""

    Result = inst.Result
    read_config = staticmethod(inst.read_config)
    write_config = staticmethod(inst.write_config)

    def __init__(self, tmp: Path, fail: tuple[str, ...] = ()):
        self.tmp = tmp
        self.fail = fail
        self.installs: list[tuple[Any, ...]] = []
        self.enrolls: list[dict[str, Any]] = []

    def install(self, h, scope, project=None, dry_run=False):
        self.installs.append((h, scope, project, dry_run))
        if h in self.fail:
            raise ValueError(f"{h} broken")
        return inst.Result(path=self.tmp / f"{h}-{scope}.json", action="install", added=["x"])

    def enroll(self, project=None, everywhere=False, dry_run=False):
        self.enrolls.append({"project": project, "everywhere": everywhere, "dry_run": dry_run})
        return "enrolled"

    def status_lines(self, project=None):
        return ["status-line-1"]


@pytest.fixture
def world(tmp_path, monkeypatch):
    home, repo = tmp_path / "home", tmp_path / "repo"
    home.mkdir()
    repo.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("AURORA_CLI_VERSION", raising=False)
    monkeypatch.setattr(core.paths, "repo_root", lambda *a, **k: repo)
    monkeypatch.setattr(core.paths, "launcher", lambda: None)
    monkeypatch.setattr(core.paths, "cli_command", lambda: "AUR")
    monkeypatch.setattr(onboard, "_launcher", lambda: "PYL")
    monkeypatch.setattr(onboard, "detect_harnesses", list)
    fake = FakeInst(tmp_path)
    monkeypatch.setattr(onboard, "inst", fake)
    calls: list[Any] = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(onboard.subprocess, "run", fake_run)
    return SimpleNamespace(home=home, repo=repo, tmp=tmp_path, inst=fake, calls=calls, mp=monkeypatch)


def _args(**kw):
    base = {"yes": True, "dry_run": False, "harness": None, "scope": None, "project": None, "agent_id": None}
    base.update(kw)
    return SimpleNamespace(**base)


def test_run_no_harness_warns_and_installs_git_hooks(world, capsys):
    """With no harness found, setup says how to pick one, warns about the skills link, and installs git hooks."""
    assert onboard.run(_args()) == 0
    out = capsys.readouterr().out
    assert "harnesses found: none" in out
    assert "no harness detected; pass --harness" in out
    assert "WARNING: .claude/skills is not a symlink" in out
    assert "agent id: skipped (no Claude hooks set up)" in out
    assert world.inst.installs == []
    assert world.calls == [[sys.executable, str(world.repo / "scripts" / "githooks" / "install_git_hooks.py")]]
    assert "-> later: PYL scripts/githooks/install_git_hooks.py" in out
    assert "  status-line-1" in out
    assert "AUR hooks status" in out


def test_run_claude_user_sets_agent_id_and_registers_mcp(world, capsys):
    """A claude user install writes AKASHIC_AGENT_ID into its settings and runs the MCP registration."""
    _write_mcp_register(world.repo, "def registration_command(repo):\n    return 'claude mcp add aurora'\n")
    assert onboard.run(_args(harness=["claude"], agent_id="seat-1", dry_run=False)) == 0
    out = capsys.readouterr().out
    target = world.tmp / "claude-user.json"
    assert world.inst.installs == [("claude", "user", None, False)]
    assert json.loads(target.read_text())["env"]["AKASHIC_AGENT_ID"] == "seat-1"
    assert "AKASHIC_AGENT_ID=seat-1 set in" in out
    assert "-> later: AUR hooks install --harness claude --scope user" in out
    # mcp is asked with default False in a checkout, so --yes does not register it
    assert "claude mcp add aurora" not in world.calls
    assert "-> later: PYL scripts/mcp_register.py   # prints: claude mcp add aurora" in out


def test_run_existing_agent_id_is_left_alone(world, capsys):
    """If the settings already carry the same AKASHIC_AGENT_ID, setup says so and does not rewrite."""
    target = world.tmp / "claude-user.json"
    target.write_text(json.dumps({"env": {"AKASHIC_AGENT_ID": "seat-1"}}))
    before = target.stat().st_mtime_ns
    onboard.run(_args(harness=["claude"], agent_id="seat-1"))
    assert "AKASHIC_AGENT_ID already 'seat-1'" in capsys.readouterr().out
    assert target.stat().st_mtime_ns == before


def test_run_dry_run_writes_nothing(world, capsys):
    """--dry-run passes dry_run to the installer, leaves settings unwritten and runs no subprocess."""
    assert onboard.run(_args(harness=["claude"], dry_run=True, agent_id="seat-1")) == 0
    out = capsys.readouterr().out
    assert "DRY RUN: nothing will be written." in out
    assert world.inst.installs == [("claude", "user", None, True)]
    assert not (world.tmp / "claude-user.json").exists()
    assert "AKASHIC_AGENT_ID=seat-1 would be set" in out
    assert "would run scripts/githooks/install_git_hooks.py" in out
    assert world.calls == []


def test_run_skip_scope_and_project_scope_flags(world, capsys):
    """'skip' installs nothing but prints the later command; a foreign project dir lands in --project."""
    other = world.tmp / "elsewhere"
    other.mkdir()
    onboard.run(_args(harness=["claude", "codex"], scope=None, project=str(other)))
    out = capsys.readouterr().out
    # claude defaults to user, codex to project
    assert world.inst.installs == [("claude", "user", None, False), ("codex", "project", str(other), False)]
    assert f'AUR hooks install --harness codex --scope project --project "{other}"' in out

    world.inst.installs.clear()
    onboard.run(_args(harness=["codex"], scope="skip"))
    out = capsys.readouterr().out
    assert world.inst.installs == []
    assert "codex hooks: skip" in out
    assert "-> later: AUR hooks install --harness codex --scope user" in out


def test_run_installer_failure_stops_only_that_harness(world, capsys):
    """An installer exception is reported as STOPPED for that harness and setup carries on."""
    world.inst.fail = ("claude",)
    assert onboard.run(_args(harness=["claude", "cursor"], project=str(world.repo))) == 0
    out = capsys.readouterr().out
    assert "STOPPED for claude: ValueError: claude broken" in out
    assert ("cursor", "project", str(world.repo), False) in world.inst.installs
    assert "agent id: skipped" in out


def _installed(world):
    world.mp.setattr(core.paths, "launcher", lambda: "/opt/aurora/bin/aurora")
    world.mp.setenv("AURORA_CLI_VERSION", "9.9")
    here = world.tmp / "proj"
    here.mkdir()
    world.mp.chdir(here)
    return here.resolve()


def test_run_installed_enrolls_cwd_and_registers_mcp(world, capsys):
    """Installed: a user-scope install asks enrolment once (default: here), MCP is registered, git hooks skipped."""
    here = _installed(world)
    _write_mcp_register(world.repo, "def registration_command(repo):\n    return 'claude mcp add aurora'\n")
    assert onboard.run(_args(harness=["claude", "codex"], scope="user")) == 0
    out = capsys.readouterr().out
    assert "Aurora 9.9 installed at" in out
    assert "WARNING" not in out
    assert world.inst.enrolls == [{"project": here, "everywhere": False, "dry_run": False}]
    assert "[2/5] enrolled" in out
    assert world.calls == ["claude mcp add aurora"]
    assert "[4/5] registered" in out
    assert "git hooks: skipped" in out
    assert "install_git_hooks" not in out


def test_run_installed_mcp_failure_and_dry_run(world, capsys):
    """A failing `claude mcp add` reports its exit code; under --dry-run it is only described."""
    _installed(world)
    _write_mcp_register(world.repo, "def registration_command(repo):\n    return 'claude mcp add aurora'\n")
    world.mp.setattr(onboard.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 3))
    onboard.run(_args(harness=["claude"]))
    assert "`claude mcp add` exited 3" in capsys.readouterr().out
    onboard.run(_args(harness=["claude"], dry_run=True))
    assert "would run: claude mcp add aurora" in capsys.readouterr().out


def test_ask_enrolment_choices(world, monkeypatch, capsys):
    """Enrolment: 'everywhere' enrolls globally, 'none' enrolls nothing; home defaults to none."""
    here = world.tmp
    answers = iter(["everywhere"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    onboard._ask_enrolment(onboard.Asker(False), here, "AUR", False)
    assert world.inst.enrolls == [{"project": None, "everywhere": True, "dry_run": False}]
    world.inst.enrolls.clear()
    onboard._ask_enrolment(onboard.Asker(True), world.home.resolve(), "AUR", True)
    out = capsys.readouterr().out
    assert "-> none" in out
    assert world.inst.enrolls == []
    assert "AUR hooks enroll --project <dir>" in out
