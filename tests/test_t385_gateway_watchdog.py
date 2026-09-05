"""RED pins for T385's scheduler-owned Discord gateway recovery path.

Live failure injection on 2026-09-05 proved that this host did not honor the
gateway task's RestartOnFailure XML after its exact owned process was killed.
The existing EarWatchdog task therefore becomes a tiny periodic task nudge:
Task Scheduler starts the gateway task if dead, while IgnoreNew absorbs the
same nudge when it is already healthy. It must never detach its own gateway.
"""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_sunshine_discord_tasks.ps1"


def test_watchdog_nudges_the_owned_gateway_task_once_per_minute():
    text = INSTALLER.read_text(encoding="utf-8")

    block = re.search(
        r"\$gatewayWatchdogArguments\s*=\s*ConvertTo-TaskArguments\s+@\((.*?)\n\)",
        text,
        re.DOTALL,
    )
    assert block is not None, "the scheduler recovery nudge is not declared"
    assert "'/Run', '/TN', $GatewayTaskName" in " ".join(block.group(1).split())
    assert "schtasks.exe" in text
    assert "RepetitionInterval (New-TimeSpan -Minutes 1)" in text
    assert "GatewayWatchdogTaskName" in text
    assert "Register-ScheduledTask" in text
    assert "Enable-ScheduledTask" in text


def test_watchdog_cannot_spawn_an_orphan_gateway_directly():
    text = INSTALLER.read_text(encoding="utf-8")
    block = re.search(
        r"\$gatewayWatchdogArguments\s*=\s*ConvertTo-TaskArguments\s+@\((.*?)\n\)",
        text,
        re.DOTALL,
    )
    assert block is not None
    body = block.group(1)
    assert "bifrost_runner_discord.py" not in body
    assert "revive.py" not in body
    assert "run_aurora_service.py" not in body


def test_gateway_task_absorbs_healthy_watchdog_nudges():
    text = INSTALLER.read_text(encoding="utf-8")
    assert "-MultipleInstances IgnoreNew" in text
