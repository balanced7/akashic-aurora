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
