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
                "cmdline": "py agent_cli.py gateway status bifrost_runner_discord"
            },
            4242: {"cmdline": "py scripts/bifrost_runner_discord.py"},
        },
    )

    rc = agent_cli.cmd_gateway(SimpleNamespace(action="status", json=True))
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload == {"live": [4242], "count": 1}
