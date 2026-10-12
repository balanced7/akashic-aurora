"""Pins for `discord` after the AXI conversion. Nothing here posts: the webhook lookup, the
target resolution and the forwarder are all replaced.

Run: uv run pytest tests/test_axi_discord.py -q
"""

import argparse
import json
from pathlib import Path

import pytest

import agent_cli
from core.comm import discord_bridge as DB
from core.comm import discord_feed as DF
from core.outcome import BoundaryOutcome


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.delenv("AKASHIC_DISCORD_WEBHOOK", raising=False)
    monkeypatch.setattr(DB, "url_file", lambda: Path("/vault/discord_webhook.url"))
    monkeypatch.setattr(DB, "webhook_url", lambda: "")
    monkeypatch.setattr(DB, "forward", lambda *a, **k: pytest.fail("a test must never post"))


def _run(action, **kw):
    ns = argparse.Namespace(action=action, text="hi", kind="chat", json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    return agent_cli.cmd_discord(ns)


def test_unconfigured_status_is_a_state_with_setup_steps(capsys):
    assert _run("status") == 0
    out = capsys.readouterr().out
    assert out.startswith("configured: false")
    assert "webhook_file: /vault/discord_webhook.url" in out
    assert "discord test" in out


def test_status_json_is_unchanged(capsys):
    assert _run("status", json=True) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["configured"] is False
    assert d["source"] is None


def test_send_without_any_target_is_not_configured(monkeypatch, capsys):
    monkeypatch.setattr(DF, "send_target", lambda seat: ("", "", "discord is not configured -- nothing was sent"))
    assert _run("send") == 1
    out = capsys.readouterr().out
    assert "code: NOT_CONFIGURED" in out
    assert "discord status" in out


def test_send_receipt_names_the_room_and_the_fallback(monkeypatch, capsys):
    monkeypatch.setattr(DF, "send_target", lambda seat: ("https://x", "the GLOBAL channel", "falling back"))
    monkeypatch.setattr(DB, "forward", lambda *a, **k: BoundaryOutcome.done())
    assert _run("send") == 0
    out = capsys.readouterr().out
    assert "sent: true" in out
    assert "to: the GLOBAL channel" in out
    assert "note: falling back" in out


def test_a_half_sent_message_is_an_error(monkeypatch, capsys):
    monkeypatch.setattr(DF, "send_target", lambda seat: ("https://x", "claude's own seat lane", ""))
    monkeypatch.setattr(DB, "forward", lambda *a, **k: BoundaryOutcome.partially("2 of 3 parts"))
    assert _run("send") == 1
    assert "code: PARTIAL" in capsys.readouterr().out


def test_human_status_names_the_state(monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    assert _run("status") == 0
    assert "not configured" in capsys.readouterr().out
