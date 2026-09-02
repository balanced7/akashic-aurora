"""T385 RED: a managed daemon may supervise Sunshine's own runner explicitly."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import bifrost_daemon as daemon


def test_daemon_parser_accepts_explicit_runner_and_repeatable_child_args():
    args = daemon.build_parser().parse_args(
        [
            "--agent",
            "sol",
            "--spawn-runner",
            "--runner-script",
            "bifrost_runner_sol.py",
            "--runner-consume-lane",
            "work",
            "--refusal-exit-code",
            "75",
            "--runner-arg=--ignore-source",
            "--runner-arg=discord",
        ]
    )

    assert args.runner_script == "bifrost_runner_sol.py"
    assert args.runner_consume_lane == "work"
    assert args.refusal_exit_code == 75
    assert args.runner_arg == ["--ignore-source", "discord"]


def test_external_supervisor_keeps_daemon_anchored_instead_of_detached_respawn(monkeypatch):
    calls = []

    def _would_detach(agent, *, in_flight=False):
        calls.append((agent, in_flight))
        return "stale-code successor launched"

    monkeypatch.setattr(daemon._SELF_RESTART, "maybe_self_restart", _would_detach)
    args = daemon.build_parser().parse_args(
        ["--agent", "sol", "--external-supervisor"]
    )

    assert args.external_supervisor is True
    assert daemon.daemon_self_restart_reason(
        "sol", in_flight=False, external_supervisor=args.external_supervisor
    ) is None
    assert calls == []

    assert daemon.daemon_self_restart_reason(
        "sol", in_flight=True, external_supervisor=False
    ) == "stale-code successor launched"
    assert calls == [("sol", True)]


def test_external_supervisor_waits_inside_same_process_for_singleton_lease():
    class _Lock:
        def __init__(self, outcomes):
            self.outcomes = iter(outcomes)
            self.calls = 0

        def acquire(self):
            self.calls += 1
            return next(self.outcomes)

    supervised = _Lock([False, False, True])
    sleeps = []
    assert daemon.acquire_daemon_lock(
        supervised,
        external_supervisor=True,
        retry_s=0.25,
        sleep_fn=sleeps.append,
    ) is True
    assert supervised.calls == 3
    assert sleeps == [0.25, 0.25]

    default = _Lock([False])
    assert daemon.acquire_daemon_lock(
        default,
        external_supervisor=False,
        retry_s=0.25,
        sleep_fn=lambda _: pytest.fail("unsupervised refusal must not wait"),
    ) is False
    assert default.calls == 1


def test_sunshine_scheduled_task_declares_external_supervisor_anchor():
    installer = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "install_sunshine_discord_tasks.ps1"
    ).read_text(encoding="utf-8")

    assert "'--external-supervisor'" in installer


@pytest.mark.skipif(os.name != "nt", reason="PowerShell Task Scheduler installer is Windows-only")
def test_sunshine_installer_resolves_its_default_repo_root_in_script_context():
    installer = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "install_sunshine_discord_tasks.ps1"
    )
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(installer),
            "-ThreadId",
            "00000000-0000-0000-0000-000000000001",
            "-SourceThreadId",
            "00000000-0000-0000-0000-000000000002",
            "-PythonExe",
            sys.executable,
            "-WhatIf",
        ],
        cwd=str(installer.parents[1]),
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_managed_runner_environment_can_pin_the_work_lane_without_dropping_base_values():
    env = daemon.managed_runner_env(
        "sol",
        consume_lane="work",
        base={"KEEP_ME": "yes"},
    )

    assert env["KEEP_ME"] == "yes"
    assert env["BIFROST_CONSUME_LANE"] == "work"

    with pytest.raises(ValueError):
        daemon.managed_runner_env("sol", consume_lane="mystery", base={})


def test_managed_runner_defaults_remain_deepseek_and_full_door(tmp_path):
    argv = daemon.managed_runner_argv(
        "deepseek",
        str(tmp_path / "summary.json"),
    )

    assert Path(argv[1]).name == "bifrost_runner_deepseek.py"
    assert argv[2:7] == [
        "--agent",
        "deepseek",
        "--agentic",
        "--allow-write",
        "--allow-exec",
    ]


def test_managed_runner_can_select_sol_and_exclude_dedicated_discord_ingress(tmp_path):
    summary = str(tmp_path / "summary.json")
    argv = daemon.managed_runner_argv(
        "sol",
        summary,
        runner_script="bifrost_runner_sol.py",
        runner_args=["--ignore-source", "discord"],
        inject_summary=True,
    )

    assert Path(argv[1]).name == "bifrost_runner_sol.py"
    assert argv[2:7] == [
        "--agent",
        "sol",
        "--agentic",
        "--allow-write",
        "--allow-exec",
    ]
    assert argv[7:9] == ["--ignore-source", "discord"]
    assert argv[-4:] == ["--summary-file", summary, "--inject-summary", summary]


@pytest.mark.parametrize(
    "name",
    ["../bifrost_runner_sol.py", "bifrost_daemon.py", "missing_runner.py"],
)
def test_managed_runner_override_refuses_traversal_nonrunner_and_missing_files(name, tmp_path):
    with pytest.raises(ValueError):
        daemon.managed_runner_argv(
            "sol",
            str(tmp_path / "summary.json"),
            runner_script=name,
        )
