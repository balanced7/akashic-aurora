"""Pre-registered pins for T385's Discord production-world migration.

These tests intentionally precede the implementation.  The incident was possible because
the checkout marker implicitly selected the runtime bus at process import time.  The new
contract makes the service world explicit, visible, and earlier than every Aurora import.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "run_aurora_service.py"
INSTALLER = ROOT / "scripts" / "install_sunshine_discord_tasks.ps1"


def _load_launcher():
    assert LAUNCHER.is_file(), "production services still have no explicit world launcher"
    spec = importlib.util.spec_from_file_location("run_aurora_service", LAUNCHER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_p1_all_four_tasks_launch_through_an_explicit_prod_pin():
    text = INSTALLER.read_text(encoding="utf-8")
    blocks = {
        name: re.search(
            rf"\${name}\s*=\s*ConvertTo-TaskArguments\s+@\((.*?)\n\)",
            text,
            re.DOTALL,
        )
        for name in (
            "gatewayArguments",
            "fleetArguments",
            "discordArguments",
            "gptNewDiscordArguments",
        )
    }
    assert all(blocks.values()), {name: bool(block) for name, block in blocks.items()}
    for name, match in blocks.items():
        body = match.group(1)
        assert "$serviceLauncher" in body, f"{name} bypasses the world launcher"
        assert re.search(r"'--world'\s*,\s*'prod'\s*,\s*'--'", body), (
            f"{name} does not pin prod before its target"
        )


def test_p2_pin_scrubs_ambient_endpoint_overrides_before_aurora_import():
    launcher = _load_launcher()
    env = launcher.pinned_environment(
        "prod",
        base={
            "AKASHIC_WORLD": "alpha",
            "REDIS_HOST": "foreign.example",
            "REDIS_PORT": "16381",
            "REDIS_DB": "15",
            "KEEP_ME": "yes",
        },
    )
    assert env["AKASHIC_WORLD"] == "prod"
    assert env["KEEP_ME"] == "yes"
    assert "REDIS_HOST" not in env
    assert "REDIS_PORT" not in env
    assert "REDIS_DB" not in env


def test_p3_launcher_allows_only_named_service_scripts_under_its_repo(tmp_path):
    launcher = _load_launcher()
    allowed = ROOT / "scripts" / "bifrost_runner_discord.py"
    assert launcher.resolve_target(str(allowed), root=ROOT) == allowed.resolve()

    outside = tmp_path / "bifrost_runner_discord.py"
    outside.write_text("raise SystemExit('must never run')\n", encoding="utf-8")
    with pytest.raises(ValueError, match="outside|allowlist"):
        launcher.resolve_target(str(outside), root=ROOT)

    unknown = ROOT / "scripts" / "some_other_service.py"
    with pytest.raises(ValueError, match="allowlist"):
        launcher.resolve_target(str(unknown), root=ROOT)


def test_p4_launcher_contract_names_the_resolved_world_and_endpoint():
    env = dict(os.environ)
    env.update(
        {
            "AKASHIC_WORLD": "alpha",
            "REDIS_HOST": "foreign.example",
            "REDIS_PORT": "16381",
            "REDIS_DB": "15",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--world",
            "prod",
            "--",
            str(ROOT / "scripts" / "codex_bifrost_wake.py"),
            "--help",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "world=prod source=override" in result.stdout
    assert "redis=localhost:16379/0" in result.stdout
