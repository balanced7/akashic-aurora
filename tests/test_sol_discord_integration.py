"""RED contracts for Sol's Discord lane and the setup/status safety boundary.

These pins deliberately use fake Discord credentials and transports.  The live drill
comes only after the local contract is green.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from core.comm import discord_feed as FEED
from core.comm import secret_intake as VAULT
import scripts.discord_setup as SETUP


ROOT = Path(__file__).resolve().parents[1]


def test_discord_status_uses_the_redirected_vault_after_url_file_constant_removal(tmp_path):
    """The T365 credential migration removed DB.URL_FILE; status must use its live resolver."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "discord_webhook.url").write_text(
        "https://discord.com/api/webhooks/1/fake-token", encoding="utf-8")
    env = dict(os.environ)
    env["AKASHIC_SECRETS_DIR"] = str(vault)
    env.pop("AKASHIC_DISCORD_WEBHOOK", None)
    env["PYTHONUTF8"] = "1"
    env["AKASHIC_WORLD"] = "alpha"

    run = subprocess.run(
        [sys.executable, "agent_cli.py", "discord", "status", "--json"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=20)

    assert run.returncode == 0, run.stderr
    payload = json.loads(run.stdout)
    assert payload["configured"] is True
    assert Path(payload["source"]) == vault / "discord_webhook.url"


def test_setup_token_reader_honors_the_redirected_vault(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "discord_bot.token").write_text("fake-bot-token", encoding="utf-8")
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(vault))
    monkeypatch.delenv("AKASHIC_DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.setattr(SETUP, "_ROOT", tmp_path / "wrong-root")

    assert SETUP._token() == "fake-bot-token"


class _ExistingDiscord:
    """Read-only Discord API double: every desired object already exists."""

    def __init__(self):
        self.posts = []
        names = ["akashic-aurora", "aurora-rooms"]
        names.extend(channel for channel, _agent in SETUP.SEAT_CHANNELS)
        self.channels = [
            {"id": f"channel-{index}", "name": name, "type": 0}
            for index, name in enumerate(names)
        ]

    def get(self, path):
        if path == "/users/@me/guilds":
            return [{"id": "guild-1", "name": "Fixture Guild", "features": []}]
        if path == "/guilds/guild-1/roles":
            return [{"name": name} for name, _color in SETUP.ROLES]
        if path == "/guilds/guild-1/channels":
            return self.channels
        if path.startswith("/channels/") and path.endswith("/webhooks"):
            return [{"id": "hook-1", "token": "fake-hook-token"}]
        raise AssertionError(f"unexpected GET {path}")

    def post(self, path, payload):
        self.posts.append((path, payload))
        raise AssertionError(f"dry-run attempted a Discord mutation: {path}")


def test_setup_dry_run_never_writes_the_vault_or_registry(tmp_path, monkeypatch):
    """Dry-run includes local durable writes in its no-mutation promise."""
    fake = _ExistingDiscord()
    registry = tmp_path / "discord_seat_channels.json"
    registry.write_text("sentinel", encoding="utf-8")
    saved = []

    monkeypatch.setattr(SETUP, "D", lambda _token: fake)
    monkeypatch.setattr(SETUP, "_token", lambda: "fake-bot-token")
    monkeypatch.setattr(SETUP, "SEATS_FILE", registry)
    monkeypatch.setattr(
        SETUP.VAULT, "save_secret",
        lambda target, value: saved.append((target, value)) or {"bytes": len(value)})
    monkeypatch.setattr(sys, "argv", ["discord_setup.py", "--dry-run"])

    assert SETUP.main() == 0
    assert fake.posts == []
    assert saved == [], "dry-run must not refresh even an already-existing webhook secret"
    assert registry.read_text(encoding="utf-8") == "sentinel"


def test_sol_lane_uses_the_stable_seat_address_without_callsign_ratification(
        tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    lane_url = "https://discord.com/api/webhooks/2/fake-sol-token"
    (vault / "discord_channel_sol.url").write_text(lane_url, encoding="utf-8")
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(vault))

    url, source, note = FEED.send_target(
        "sol", global_url="https://discord.com/api/webhooks/3/fake-global-token")

    assert FEED.seat_channel_url("sol") == lane_url
    assert url == lane_url
    assert "seat lane" in source
    assert note == ""


def test_setup_declares_sol_as_an_address_not_a_callsign():
    assert ("sunshine", "sol") in SETUP.SEAT_CHANNELS
    assert ("gpt-new", "gpt-new") in SETUP.SEAT_CHANNELS
    assert ("sol", "sol") not in SETUP.SEAT_CHANNELS
    assert all(name.lower() != "sunshine" for name, _color in SETUP.ROLES)
    assert "discord_channel_sol.url" in VAULT.TARGETS
