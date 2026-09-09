"""The gateway status probe must not count its own command line as a gateway."""

import json
import os
from types import SimpleNamespace

import agent_cli
from core.comm import wake_seat


def test_gateway_status_excludes_the_status_process(monkeypatch, capsys):
    self_pid = os.getpid()
    monkeypatch.setattr(
        wake_seat,
        "process_snapshot",
        lambda: {
            self_pid: {
                "name": "python.exe",
                "cmdline": "py agent_cli.py gateway status bifrost_runner_discord"
            },
            3131: {
                "name": "powershell.exe",
                "cmdline": (
                    "powershell -Command Get-CimInstance; "
                    "C:\\repo\\scripts\\bifrost_runner_discord.py"
                ),
            },
            4141: {
                "name": "python.exe",
                "cmdline": "python -c \"print('bifrost_runner_discord.py')\"",
            },
            4242: {
                "name": "python.exe",
                "cmdline": (
                    "python C:\\repo\\scripts\\run_aurora_service.py --world prod -- "
                    "C:\\repo\\scripts\\bifrost_runner_discord.py"
                ),
            },
        },
    )

    rc = agent_cli.cmd_gateway(SimpleNamespace(action="status", json=True))
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload == {"live": [4242], "count": 1}


def test_gateway_restart_delegates_to_the_owned_scheduled_task(monkeypatch):
    """The maintenance door must preserve scheduler ancestry and deployment authority.

    The deployed worktree is intentionally marked alpha, while Task Scheduler pins
    the long-lived gateway to prod through ``run_aurora_service.py``.  The door must
    end and run that task, not reproduce its command under a different parent.
    """
    monkeypatch.setattr(
        wake_seat,
        "process_snapshot",
        lambda: {
            2332: {
                "name": "svchost.exe",
                "cmdline": "svchost.exe -k netsvcs -p -s Schedule",
            },
            55488: {
                "ppid": 2332,
                "name": "python.exe",
                "cmdline": (
                    "python C:\\repo\\scripts\\run_aurora_service.py --world prod -- "
                    "C:\\repo\\scripts\\bifrost_runner_discord.py"
                ),
            },
        },
    )
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("time.sleep", lambda _: None)

    rc = agent_cli.cmd_gateway(SimpleNamespace(action="restart", json=True))

    assert rc == 0
    assert calls == [
        ["schtasks.exe", "/Query", "/TN", "AkashicAurora-DiscordGateway"],
        ["schtasks.exe", "/End", "/TN", "AkashicAurora-DiscordGateway"],
        ["schtasks.exe", "/Run", "/TN", "AkashicAurora-DiscordGateway"],
    ]


def test_gateway_restart_refuses_a_direct_or_foreign_world_process(monkeypatch):
    calls = []
    monkeypatch.setattr(
        wake_seat,
        "process_snapshot",
        lambda: {
            10864: {
                "ppid": 4000,
                "name": "python.exe",
                "cmdline": "python C:\\repo\\scripts\\bifrost_runner_discord.py",
            }
        },
    )

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    rc = agent_cli.cmd_gateway(SimpleNamespace(action="restart", json=True))

    assert rc == 1
    assert calls == [], "foreign gateways require explicit evidence, never a name-wide kill"
