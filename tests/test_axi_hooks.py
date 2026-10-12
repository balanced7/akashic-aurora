"""Pins for `hooks` after the AXI conversion: what an agent and a person see.

Every case runs against a throwaway HOME, repo, project, sidecar and enrolment file, so nothing
here reads or writes a real settings file.

Run: uv run pytest tests/test_axi_hooks.py -q
"""

import argparse

import pytest

import agent_cli
from agent.harness import install as inst
from agent.harness import scope


@pytest.fixture
def env(tmp_path, monkeypatch):
    home, repo, proj = tmp_path / "home", tmp_path / "repo", tmp_path / "proj"
    for d in (home, repo, proj):
        d.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.chdir(proj)
    monkeypatch.setattr(inst, "_repo", lambda: repo.resolve())
    monkeypatch.setattr(inst, "sidecar_path", lambda: tmp_path / "sidecar.json")
    monkeypatch.setattr(scope, "enrolled_file", lambda: str(tmp_path / "scope.json"))
    return proj


def _hooks(capsys, action, project, **kw):
    ns = argparse.Namespace(
        action=action,
        harness="claude",
        scope="project",
        project=str(project),
        everywhere=False,
        shared=False,
        dry_run=False,
        all=False,
        json=False,
    )
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_hooks(ns)
    return code, capsys.readouterr().out


def test_status_is_one_row_per_hooked_file_with_a_state(env, capsys):
    inst.install("claude", "project", project=env)
    inst.install("codex", "project", project=env)
    inst.disable("codex", "project", project=env)
    code, text = _hooks(capsys, "status", env)
    assert code == 0
    assert "hooked_files: 2" in text
    assert "files[2]{harness,scope,state,installed,disabled,path}:" in text
    assert "claude,project,on," in text
    assert "codex,project,off,0," in text
    assert "enrolled: none -- the hooks speak up only in the Aurora repo" in text
    # the fix names the project this output describes, not the cwd's
    assert f"hooks enable --harness codex --scope project --project {env}" in text


def test_nothing_registered_is_said_outright(env, capsys):
    code, text = _hooks(capsys, "status", env)
    assert code == 0
    assert "hooked_files: 0\nfiles: []" in text
    assert "agent_cli.py setup" in text


def test_dry_run_says_nothing_was_written_and_gives_the_real_command(env, capsys):
    code, text = _hooks(capsys, "install", env, harness="cursor", dry_run=True)
    assert code == 0
    assert "dry_run: true\nwritten: false" in text
    assert "added[" in text
    assert f"hooks install --harness cursor --scope project --project {env}" in text
    assert not (env / ".cursor" / "hooks.json").exists()


def test_a_second_install_is_already_up_to_date(env, capsys):
    _hooks(capsys, "install", env)
    code, text = _hooks(capsys, "install", env)
    assert code == 0
    assert "written: false" in text
    assert "result: already up to date" in text


def test_an_unreadable_file_is_a_structured_error(env, capsys):
    bad = env / ".claude" / "settings.local.json"
    bad.parent.mkdir()
    bad.write_text("{not json", encoding="utf-8")
    code, text = _hooks(capsys, "install", env)
    assert code == 2
    assert "code: UNREADABLE_CONFIG" in text
    assert bad.read_text(encoding="utf-8") == "{not json"


def test_human_view_is_a_table_with_states(env, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "200")
    inst.install("claude", "project", project=env)
    _, text = _hooks(capsys, "status", env)
    assert "Aurora harness hooks" in text
    assert "claude" in text
    assert " on " in text
    assert "Enrolled: none" in text
