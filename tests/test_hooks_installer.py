"""PIN: `agent_cli.py hooks` (agent/harness/install.py) -- the harness hook installer.

Contract: our entries only (foreign hooks and keys survive), idempotent install, a reversible
disable, one surface per Claude hook (C8-3: a double registration double-fires and double-counts
recall), and commands that run from any cwd. Every case runs against a throwaway HOME, repo and
project, so nothing here reads or writes a real settings file.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.harness import install as inst
from agent.harness.registry import HOOK_SPECS

FOREIGN = {"type": "command", "command": "echo not-ours"}


@pytest.fixture
def env(tmp_path, monkeypatch):
    home, repo, proj = tmp_path / "home", tmp_path / "repo", tmp_path / "proj"
    for d in (home, repo, proj):
        d.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.chdir(proj)
    monkeypatch.setattr(inst, "_repo", lambda: repo.resolve())
    monkeypatch.setattr(inst, "sidecar_path", lambda: tmp_path / "sidecar.json")
    return home, repo, proj


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def _seed(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_install_writes_every_spec_and_is_idempotent(env):
    _, _, proj = env
    res = inst.install("claude", "project", project=proj)
    assert res.path == proj / ".claude" / "settings.local.json"
    assert len(res.added) == len(HOOK_SPECS["claude"])
    first = res.path.read_bytes()
    again = inst.install("claude", "project", project=proj)
    assert (again.added, again.removed, again.changed) == ([], [], False)
    assert res.path.read_bytes() == first


def test_foreign_hooks_and_keys_survive_install_and_uninstall(env):
    _, _, proj = env
    path = proj / ".claude" / "settings.local.json"
    _seed(path, {"model": "opus", "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [FOREIGN]}]}})
    inst.install("claude", "project", project=proj)
    assert _load(path)["model"] == "opus"
    inst.uninstall("claude", "project", project=proj)
    assert _load(path) == {"model": "opus", "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [FOREIGN]}]}}
    assert (path.parent / "settings.local.json.bak").exists()


def test_disable_then_enable_restores_the_file_exactly(env):
    _, _, proj = env
    inst.install("claude", "project", project=proj)
    path = proj / ".claude" / "settings.local.json"
    doc = _load(path)
    doc["hooks"]["Stop"][0]["matcher"] = "hand-edited"  # a user tweak must survive the round trip
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    before = _load(path)
    d = inst.disable("claude", "project", project=proj)
    assert d.removed
    assert "hooks" not in _load(path)
    inst.enable("claude", "project", project=proj)
    after = _load(path)
    for event, groups in before["hooks"].items():
        assert sorted(json.dumps(g, sort_keys=True) for g in groups) == sorted(
            json.dumps(g, sort_keys=True) for g in after["hooks"][event]
        )
    assert not inst.sidecar_path().exists(), "enable must clear the disabled record"


def test_enable_without_a_disable_says_how_to_install(env):
    res = inst.enable("claude", "user")
    assert not res.changed
    assert "hooks install" in res.notes[0]


def test_one_surface_per_claude_hook(env):
    home, repo, _ = env
    shared = repo / ".claude" / "settings.json"
    cmd = '"$CLAUDE_PROJECT_DIR/agent/harness/hooks/claude_pretooluse.py"'
    _seed(shared, {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": cmd}]}]}})
    res = inst.install("claude", "user")
    assert any("PreToolUse:claude_pretooluse.py" in s for s in res.skipped)
    user_cmds = [
        h["command"] for g in _load(home / ".claude" / "settings.json")["hooks"]["PreToolUse"] for h in g["hooks"]
    ]
    assert not any("claude_pretooluse.py" in c for c in user_cmds)


def test_commands_run_from_any_cwd(env, monkeypatch):
    _, repo, proj = env
    monkeypatch.setattr(inst.shutil, "which", lambda _b: "/usr/bin/uv")
    user = inst.hook_command("claude", "claude_trace.py", "user")
    assert f'--project "{inst._posix(repo.resolve())}"' in user
    assert "/agent/harness/hooks/claude_trace.py" in user
    in_repo = inst.hook_command("claude", "claude_trace.py", "project", project=repo)
    assert "$CLAUDE_PROJECT_DIR" in in_repo
    elsewhere = inst.hook_command("cursor", "cursor_posttooluse.py --event x", "project", project=proj)
    assert elsewhere.endswith('cursor_posttooluse.py" --event x')


def test_windows_form_uses_the_windowless_launcher(env, monkeypatch):
    monkeypatch.setattr(inst.shutil, "which", lambda _b: None)
    cmd = inst.hook_command("claude", "claude_stop.py", "user", os_name="nt")
    assert "command -v uvw" in cmd
    assert "--gui-script" in cmd


def test_cursor_shape_and_fail_closed_guard(env):
    _, _, proj = env
    inst.install("cursor", "project", project=proj)
    doc = _load(proj / ".cursor" / "hooks.json")
    assert doc["version"] == 1
    guard = doc["hooks"]["beforeShellExecution"][0]
    assert guard["failClosed"] is True
    assert "cursor_beforeshell.py" in guard["command"]


def test_a_broken_file_is_never_overwritten(env):
    _, _, proj = env
    path = proj / ".claude" / "settings.local.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        inst.install("claude", "project", project=proj)
    assert path.read_text(encoding="utf-8") == "{not json"


def test_status_flags_the_old_shim_path(env):
    home, _, _ = env
    old = "pyw /old/checkout/scripts/hooks/claude_stop.py"
    _seed(
        home / ".claude" / "settings.json",
        {"hooks": {"Stop": [{"matcher": "*", "hooks": [{"type": "command", "command": old}]}]}},
    )
    row = next(r for r in inst.status() if r["harness"] == "claude" and r["scope"] == "user")
    assert row["stale"] == ["Stop:claude_stop.py"]
    assert any("scripts/hooks/ shim path" in line for line in inst.status_lines())
