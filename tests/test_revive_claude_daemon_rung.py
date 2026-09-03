"""RED pins (M3, acceptance before implementation): the claude daemon rung -- wake
doctrine S1, closing H1 from the 2026-09-02 verification audit.

THE HOLE: the claude autopilot daemon (`bifrost_daemon --agent claude
--manage-listener`) re-arms every wake listener for the Vandor seat -- and NOTHING
supervises it. `revive.DAEMON_AGENTS` was ("deepseek", "kimi") only, so `!revive`
and any watchdog cadence walk right past a dead claude daemon while the seat's
re-arm silently stops (most historical "Vandor went deaf" incidents).

THE TRAP THIS PINS AGAINST (F13 class): claude's daemon takes --manage-listener,
NOT --spawn-runner. Naive rostering would plan the wrong launch flag, and the
runners rung would report a phantom dead claude-runner forever (there is no
bifrost_runner_claude by design -- the Token Frugality Directive).

Design authority: note wake-supervision-reconciliation-2026-08-28 (the L0-L4
ladder; this is the L2 reconciler learning the rung, heal-only-the-ABSENT).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import revive  # noqa: E402


def _table(*lines: str) -> str:
    return "\n".join(lines)


ALL_ALIVE = _table(
    "python.exe E:\\AI-Setup\\scripts\\bifrost_daemon.py --agent deepseek --spawn-runner",
    "python.exe E:\\AI-Setup\\scripts\\bifrost_runner_deepseek.py --agent deepseek",
    "python.exe E:\\AI-Setup\\scripts\\bifrost_daemon.py --agent kimi --spawn-runner",
    "python.exe E:\\AI-Setup\\scripts\\bifrost_runner_deepseek.py --agent kimi",
    "python.exe E:\\AI-Setup\\scripts\\bifrost_daemon.py --agent claude --manage-listener",
    "python.exe E:\\AI-Setup\\scripts\\bifrost_runner_discord.py",
)

CLAUDE_DAEMON_DEAD = _table(
    "python.exe E:\\AI-Setup\\scripts\\bifrost_daemon.py --agent deepseek --spawn-runner",
    "python.exe E:\\AI-Setup\\scripts\\bifrost_runner_deepseek.py --agent deepseek",
    "python.exe E:\\AI-Setup\\scripts\\bifrost_daemon.py --agent kimi --spawn-runner",
    "python.exe E:\\AI-Setup\\scripts\\bifrost_runner_deepseek.py --agent kimi",
    "python.exe E:\\AI-Setup\\scripts\\bifrost_runner_discord.py",
)


def _observe(monkeypatch, table: str):
    monkeypatch.setattr(revive, "_cmdlines", lambda: table)
    return revive.observe(include_app=False)


def test_claude_is_on_the_daemon_roster():
    assert "claude" in revive.DAEMON_AGENTS, (
        "H1: the claude autopilot daemon is unsupervised until the roster knows it"
    )


def test_absent_claude_daemon_is_observed_dead(monkeypatch):
    obs = _observe(monkeypatch, CLAUDE_DAEMON_DEAD)
    assert "claude" in obs["daemon"]["dead"]
    assert obs["daemon"]["healthy"] is False


def test_dead_claude_daemon_plans_manage_listener_never_spawn_runner(monkeypatch):
    obs = _observe(monkeypatch, CLAUDE_DAEMON_DEAD)
    plan = revive.decide(obs, target="daemon")
    claude_steps = [p for p in plan if p.get("agent") == "claude"]
    assert claude_steps, "a dead claude daemon must be planned for revival"
    cmd = claude_steps[0]["cmd"]
    assert "--manage-listener" in cmd, (
        "claude's daemon supervises wake listeners; --manage-listener is its mode"
    )
    assert "--spawn-runner" not in cmd, (
        "F13 class: the wrong launch flag would spawn a runner claude does not have"
    )


def test_live_claude_daemon_is_never_touched(monkeypatch):
    """Heal-only-the-dead (R2's law, extended to the new rung)."""
    obs = _observe(monkeypatch, ALL_ALIVE)
    plan = revive.decide(obs, target="daemon")
    assert not [p for p in plan if p.get("agent") == "claude"], (
        "an alive claude daemon must never be re-planned -- duplicates breed here"
    )
    assert obs["daemon"]["healthy"] is True


def test_runners_rung_does_not_expect_a_claude_runner(monkeypatch):
    """There is no bifrost_runner_claude BY DESIGN; its absence is not a death."""
    obs = _observe(monkeypatch, ALL_ALIVE)
    assert "claude" not in obs["runners"]["dead"]
    assert obs["runners"]["healthy"] is True


def test_deepseek_and_kimi_rungs_are_unchanged(monkeypatch):
    """The new rung must not disturb R2's exact-dead planning for the others."""
    table = _table(
        "python.exe E:\\AI-Setup\\scripts\\bifrost_daemon.py --agent deepseek --spawn-runner",
        "python.exe E:\\AI-Setup\\scripts\\bifrost_runner_deepseek.py --agent deepseek",
        "python.exe E:\\AI-Setup\\scripts\\bifrost_daemon.py --agent claude --manage-listener",
        "python.exe E:\\AI-Setup\\scripts\\bifrost_runner_discord.py",
    )
    obs = _observe(monkeypatch, table)
    assert obs["daemon"]["dead"] == ["kimi"]
    plan = revive.decide(obs, target="daemon")
    planned = sorted(p["agent"] for p in plan if p["organ"] == "daemon")
    assert planned == ["kimi"], f"only the dead agent is planned, got {planned}"
    kimi_cmd = [p for p in plan if p.get("agent") == "kimi"][0]["cmd"]
    assert "--spawn-runner" in kimi_cmd and "--manage-listener" not in kimi_cmd
