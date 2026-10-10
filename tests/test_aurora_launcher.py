"""PIN: the installed `aurora` launcher (aurora-cli/) -- routing, environment, and bundle fetch.

Contract: `aurora <verb>` runs agent_cli.py <verb>; `aurora mcp` runs the MCP server; scripts and
-m/-c run as Aurora's Python (so every command Aurora prints for an agent still resolves); a
bundle keeps its state OUTSIDE the versioned code (an upgrade never touches memory) and names a
world (an undeclared bundle would resolve to `unknown`, which refuses writes); a checkout gets
nothing added. A bundle is unpacked only after its published sha256 matches.
"""

import hashlib
import io
import json
import os
import sys
import tarfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_cli import bundle, launcher


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "aurora-home"
    monkeypatch.setenv("AURORA_HOME", str(h))
    for var in ("AKASHIC_WORLD", "AI_SETUP", "AKASHIC_PYTHON", "AURORA_REPO", "AURORA_RELEASE_BASE"):
        monkeypatch.delenv(var, raising=False)
    return h


def _fake_tree(root):
    (root / "core").mkdir(parents=True)
    (root / "agent_cli.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "x.py").write_text("", encoding="utf-8")
    return root


def test_routing(tmp_path):
    root = _fake_tree(tmp_path / "b")
    assert launcher.command_for(["boot", "me"], root) == [str(root / "agent_cli.py"), "boot", "me"]
    assert launcher.command_for([], root) == [str(root / "agent_cli.py")]
    assert launcher.command_for(["mcp"], root) == [str(root / "ai_setup_mcp.py")]
    # printed commands (`<launcher> agent_cli.py ...`, `<launcher> scripts/x.py`) resolve in the tree
    assert launcher.command_for(["agent_cli.py", "recall", "q"], root) == [str(root / "agent_cli.py"), "recall", "q"]
    assert launcher.command_for(["scripts/x.py", "--a"], root) == [str(root / "scripts" / "x.py"), "--a"]
    assert launcher.command_for(["elsewhere.py"], root) == ["elsewhere.py"], "a script not in the tree is the user's"
    assert launcher.command_for(["-m", "pytest", "-q"], root) == ["-m", "pytest", "-q"]
    assert launcher._python_route(["-c", "print(1)"])
    assert not launcher._python_route(["boot"])


def test_bundle_env_keeps_state_outside_code_and_names_a_world(home, tmp_path, monkeypatch):
    root = _fake_tree(tmp_path / "b")
    monkeypatch.setattr(launcher, "_launcher_path", lambda: "/opt/bin/aurora")
    env = launcher.program_env(root, "bundle")
    assert env["AI_SETUP"] == str(home / "data")
    assert env["AKASHIC_EMBEDDED_REDIS_DIR"] == str(home / "data" / "state" / "redis-embedded")
    assert env["AKASHIC_WORLD"] == "prod"
    assert env["AURORA_LAUNCHER"] == "/opt/bin/aurora"
    assert env["AKASHIC_PYTHON"] in ("aurora", "/opt/bin/aurora")
    (home).mkdir(exist_ok=True)
    (home / "world").write_text("alpha\n", encoding="utf-8")
    assert launcher.program_env(root, "bundle")["AKASHIC_WORLD"] == "alpha"
    monkeypatch.setenv("AKASHIC_WORLD", "beta")
    monkeypatch.setenv("AI_SETUP", "/my/data")
    env = launcher.program_env(root, "bundle")
    assert (env["AKASHIC_WORLD"], env["AI_SETUP"]) == ("beta", "/my/data"), "an explicit env always wins"


def test_checkout_env_adds_nothing(home, tmp_path):
    root = _fake_tree(tmp_path / "repo")
    env = launcher.program_env(root, "checkout")
    for var in ("AI_SETUP", "AKASHIC_WORLD", "AURORA_LAUNCHER", "AKASHIC_PYTHON"):
        assert var not in env, f"`uv run aurora` in a checkout must behave as the checkout does ({var})"


def test_aurora_repo_must_be_a_checkout(home, tmp_path, monkeypatch):
    monkeypatch.setenv("AURORA_REPO", str(tmp_path / "nope"))
    with pytest.raises(SystemExit, match="not an Aurora checkout"):
        launcher.resolve_root()
    root = _fake_tree(tmp_path / "mine")
    monkeypatch.setenv("AURORA_REPO", str(root))
    assert launcher.resolve_root() == (root.resolve(), "repo")


def _release(dirpath, version, sha=None):
    """A minimal release: aurora-<v>.tar.gz (+ .sha256) holding one tree with the markers."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in (
            (f"aurora-{version}/agent_cli.py", b""),
            (f"aurora-{version}/AURORA_BUNDLE.json", json.dumps({"version": version}).encode()),
            (f"aurora-{version}/core/__init__.py", b""),
        ):
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            tar.addfile(ti, io.BytesIO(data))
    blob = buf.getvalue()
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / f"aurora-{version}.tar.gz").write_bytes(blob)
    digest = sha or hashlib.sha256(blob).hexdigest()
    (dirpath / f"aurora-{version}.tar.gz.sha256").write_text(f"{digest}  aurora-{version}.tar.gz\n", encoding="utf-8")


def test_bundle_fetch_verifies_then_unpacks(home, tmp_path, monkeypatch):
    rel = tmp_path / "rel" / "9.9.9"
    _release(rel, "9.9.9")
    monkeypatch.setenv("AURORA_RELEASE_BASE", str(tmp_path / "rel" / "{version}"))
    root = bundle.ensure_bundle("9.9.9")
    assert root == home / "versions" / "9.9.9"
    assert (root / "agent_cli.py").is_file()
    assert bundle.installed_versions() == ["9.9.9"]
    assert bundle.ensure_bundle("9.9.9") == root, "a second call reuses the unpacked bundle"


def test_bundle_with_a_bad_checksum_is_refused(home, tmp_path, monkeypatch):
    _release(tmp_path / "rel", "9.9.8", sha="0" * 64)
    monkeypatch.setenv("AURORA_RELEASE_BASE", str(tmp_path / "rel"))
    with pytest.raises(SystemExit, match="checksum"):
        bundle.ensure_bundle("9.9.8")
    assert bundle.installed_versions() == []
