"""T385 RED: a managed daemon may supervise Sunshine's own runner explicitly."""
from __future__ import annotations

from pathlib import Path

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
            "--runner-arg=--ignore-source",
            "--runner-arg=discord",
        ]
    )

    assert args.runner_script == "bifrost_runner_sol.py"
    assert args.runner_arg == ["--ignore-source", "discord"]


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
