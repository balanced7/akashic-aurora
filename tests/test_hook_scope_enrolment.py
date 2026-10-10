"""PIN: enrolled projects (agent/harness/scope.py) and the installer's launcher form.

An installed Aurora runs from a release bundle nobody works in, so the hooks' "inside the repo"
test would match nothing. Enrolment names the projects that count as inside: an enrolled root
behaves exactly like the repo, nothing else changes, and `--everywhere` opts every directory in.
Under the launcher, hook commands call it by its stable path, so an upgrade keeps them working.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.harness import install as inst
from agent.harness import scope


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "data"))
    monkeypatch.delenv("AURORA_LAUNCHER", raising=False)
    proj = tmp_path / "proj"
    (proj / "src").mkdir(parents=True)
    return proj


def test_enrolment_round_trip(data):
    proj = data
    assert not scope.under_root(str(proj / "src" / "a.py"))
    assert "enrolled" in inst.enroll(proj)
    assert scope.under_root(str(proj))
    assert scope.under_root(str(proj / "src" / "a.py"))
    assert scope.session_in_scope(str(proj / "src"))
    assert not scope.under_root(str(proj) + "-sibling"), "a prefix is not a parent"
    assert "already" in inst.enroll(proj)
    assert "unenrolled" in inst.unenroll(proj)
    assert not scope.under_root(str(proj / "src"))


def test_everywhere(data):
    inst.enroll(everywhere=True)
    assert scope.under_root(os.path.abspath(os.sep))
    inst.unenroll(everywhere=True)
    assert not scope.under_root(str(data))


def test_dry_run_and_unreadable_file(data):
    inst.enroll(data, dry_run=True)
    assert not scope.under_root(str(data))
    path = scope.enrolled_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    assert scope.enrolled() == {"roots": [], "everywhere": False}, "unreadable means nothing enrolled"


def test_an_aurora_command_is_in_scope_anywhere():
    assert scope.shell_in_scope("/elsewhere", "aurora recall x")
    assert scope.shell_in_scope("/elsewhere", "cd /x && aurora boot me")
    assert not scope.shell_in_scope("/elsewhere", "ls aurora-notes")


def test_launcher_hook_command(data, monkeypatch):
    monkeypatch.setenv("AURORA_LAUNCHER", "/home/u/.local/bin/aurora")
    monkeypatch.setattr(inst, "_repo", lambda: data.parent / "bundle")
    cmd = inst.hook_command("claude", "claude_trace.py", "user", os_name="posix")
    assert cmd == '"/home/u/.local/bin/aurora" agent/harness/hooks/claude_trace.py'
    assert inst.script_of(cmd) == "claude_trace.py", "the installer still recognises its own entry"
    monkeypatch.setenv("AURORA_LAUNCHER_GUI", "C:/u/.local/bin/auroraw.exe")
    assert inst.hook_command("claude", "claude_stop.py", "user", os_name="nt").startswith(
        '"C:/u/.local/bin/auroraw.exe"'
    )
    assert inst.hook_command("cursor", "cursor_stop.py", "user", os_name="nt").startswith('"/home/u/.local/bin/aurora"')


def test_project_install_enrols_under_the_launcher(data, tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("AURORA_LAUNCHER", "/home/u/.local/bin/aurora")
    monkeypatch.setattr(inst, "_repo", lambda: tmp_path / "bundle")
    monkeypatch.setattr(inst, "sidecar_path", lambda: tmp_path / "sidecar.json")
    res = inst.install("claude", "project", project=data)
    assert any("enrolled" in n for n in res.notes)
    assert str(data.resolve()) in inst.enrolled_roots()
