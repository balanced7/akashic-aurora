"""RED contracts for separating Sunshine from the existing Discord Codex fork.

The old ``#sol`` room and its bound Codex thread are preserved as the provisional
``gpt-new`` seat.  Sunshine receives a new room and a new completed-history fork.
Address, room, thread, launch posture, and outbound identity must agree.
"""
from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

import scripts.codex_bifrost_wake as WAKE_SCRIPT
import scripts.discord_setup as SETUP
from agent.harness.codex_bifrost_wake import (
    CodexBifrostWake,
    SubjectIdentity,
    WakeProfile,
    build_wake_prompt,
    wake_developer_instructions,
)
from core.comm import discord_feed as FEED
from core.comm import secret_intake as VAULT


ROOT = Path(__file__).resolve().parents[1]


def test_room_contract_gives_each_codex_lineage_one_unambiguous_address():
    assert ("sunshine", "sol") in SETUP.SEAT_CHANNELS
    assert ("gpt-new", "gpt-new") in SETUP.SEAT_CHANNELS
    assert ("sol", "sol") not in SETUP.SEAT_CHANNELS
    assert len({agent for _room, agent in SETUP.SEAT_CHANNELS}) == len(
        SETUP.SEAT_CHANNELS
    )


def test_gpt_new_has_an_address_keyed_vault_lane(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    url = "https://discord.com/api/webhooks/99/fake-gpt-new-token"
    (vault / "discord_channel_gpt-new.url").write_text(url, encoding="utf-8")
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(vault))

    assert "discord_channel_gpt-new.url" in VAULT.TARGETS
    assert FEED.seat_channel_url("gpt-new") == url


class _SplitDiscord:
    """Discord double with the historical #sol room but no split rooms yet."""

    def __init__(self):
        self.patches = []
        self.posts = []
        self.channels = [
            {"id": "cat", "name": "akashic-aurora", "type": 4},
            {"id": "rooms", "name": "aurora-rooms", "type": 0},
            {"id": "old-sol", "name": "sol", "type": 0, "parent_id": "cat"},
        ]
        self.channels.extend(
            {
                "id": f"lane-{name}",
                "name": name,
                "type": 0,
                "parent_id": "cat",
            }
            for name in ("vandor", "heimdall", "navi", "rill")
        )

    def get(self, path):
        if path == "/users/@me/guilds":
            return [{"id": "guild-1", "name": "Fixture Guild", "features": []}]
        if path == "/guilds/guild-1/roles":
            return [{"name": name} for name, _color in SETUP.ROLES]
        if path == "/guilds/guild-1/channels":
            return self.channels
        if path.startswith("/channels/") and path.endswith("/webhooks"):
            channel_id = path.split("/")[2]
            return [{"id": f"hook-{channel_id}", "token": f"token-{channel_id}"}]
        raise AssertionError(f"unexpected GET {path}")

    def patch(self, path, payload):
        self.patches.append((path, dict(payload)))
        channel_id = path.split("/")[-1]
        channel = next(c for c in self.channels if c["id"] == channel_id)
        channel.update(payload)
        return channel

    def post(self, path, payload):
        self.posts.append((path, dict(payload)))
        if path == "/guilds/guild-1/channels":
            channel = {
                "id": f"lane-{payload['name']}",
                "name": payload["name"],
                "type": payload["type"],
                "parent_id": payload.get("parent_id"),
            }
            self.channels.append(channel)
            return channel
        raise AssertionError(f"unexpected POST {path}")


def test_setup_renames_the_historical_room_in_place_and_routes_both_lineages(
    tmp_path, monkeypatch
):
    fake = _SplitDiscord()
    registry_path = tmp_path / "discord_seat_channels.json"
    saved = {}
    monkeypatch.setattr(SETUP, "D", lambda _token: fake)
    monkeypatch.setattr(SETUP, "_token", lambda: "fake-bot-token")
    monkeypatch.setattr(SETUP, "SEATS_FILE", registry_path)
    monkeypatch.setattr(
        SETUP.VAULT,
        "save_secret",
        lambda target, value: saved.setdefault(target, value)
        and {"bytes": len(value.encode("utf-8"))},
    )
    monkeypatch.setattr("sys.argv", ["discord_setup.py"])

    assert SETUP.main() == 0
    assert fake.patches == [("/channels/old-sol", {"name": "gpt-new"})]

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert registry["channels"]["old-sol"] == "gpt-new"
    assert registry["channels"]["lane-sunshine"] == "sol"
    assert saved["discord_channel_gpt-new.url"].endswith(
        "/hook-old-sol/token-old-sol"
    )
    assert saved["discord_channel_sol.url"].endswith(
        "/hook-lane-sunshine/token-lane-sunshine"
    )


def test_wake_defaults_inherit_the_bound_thread_instead_of_re_personalizing_it():
    args = WAKE_SCRIPT.build_parser().parse_args(["--agent", "gpt-new"])
    assert args.model is None
    assert args.effort is None
    assert '"personality": "friendly"' not in inspect.getsource(
        CodexBifrostWake._continuity_thread
    )
    assert '"Sunshine"' not in inspect.getsource(WAKE_SCRIPT.main)
    assert '"historical-unratified"' not in inspect.getsource(WAKE_SCRIPT.main)


def test_expired_rill_incident_fence_is_not_a_permanent_identity_instruction():
    identity = SubjectIdentity(
        agent_id="sol",
        callsign="Sunshine",
        status="ratified",
        authority="resident-registry",
    )
    message = SimpleNamespace(
        content="hello", meta={"source": "discord"}, frm="daniil", id="1-0", kind="chat"
    )
    developer = wake_developer_instructions(
        "sol", identity, WakeProfile(allow_write=True)
    )
    prompt = build_wake_prompt(
        "sol", message, identity=identity, profile=WakeProfile(allow_write=True)
    )

    assert "Rill" not in developer
    assert "dsh_agent" not in developer
    assert "Rill" not in prompt
    assert "dsh_agent" not in prompt


def test_wake_origin_identity_must_match_the_speaking_bus_address_and_is_visible():
    good = {
        "frm": "sol",
        "content": "A reply.",
        "meta": {
            "wake_origin": "codex-bifrost-owned-app-server",
            "subject_seat": "sol",
            "continuity_thread_id": "01a00000-0000-0000-0000-000000000001",
        },
    }
    wrong = {
        **good,
        "frm": "gpt-new",
    }

    assert FEED.wake_identity_refusal(good) is None
    assert FEED.wake_identity_refusal(wrong)
    stamped = FEED.stamp_wake_identity(good)
    assert stamped["content"].endswith("`sol · task 01a00000`")
    assert "wake_identity_refusal(msg)" in inspect.getsource(FEED.pump)


def test_sunshine_installer_arms_write_without_overriding_model_or_effort():
    installer = (ROOT / "scripts" / "install_sunshine_discord_tasks.ps1").read_text(
        encoding="utf-8"
    )

    assert "'--allow-write'" in installer
    assert "sunshine-discord-continuity.state.json" in installer
    assert "gpt-new-discord-continuity.state.json" in installer
    assert "AkashicAurora-GptNewDiscord" in installer
    assert "'--agent', 'gpt-new'" in installer
    assert "'--effort'" not in installer


def test_gpt_new_does_not_inherit_sunshines_exec_or_write_authority():
    installer = (ROOT / "scripts" / "install_sunshine_discord_tasks.ps1").read_text(
        encoding="utf-8"
    )
    block = re.search(
        r"\$gptNewDiscordArguments = ConvertTo-TaskArguments @\((.*?)\n    \)",
        installer,
        re.DOTALL,
    )
    assert block is not None
    assert "'--allow-exec'" not in block.group(1)
    assert "'--allow-write'" not in block.group(1)


def test_gpt_new_exec_and_write_require_separate_explicit_installer_opt_ins():
    installer = (ROOT / "scripts" / "install_sunshine_discord_tasks.ps1").read_text(
        encoding="utf-8"
    )

    assert "[switch]$EnableGptNewExec" in installer
    assert "[switch]$EnableGptNewWrite" in installer
    assert re.search(
        r"if \(\$EnableGptNewExec\) \{.*?'--allow-exec'.*?\}",
        installer,
        re.DOTALL,
    )
    assert re.search(
        r"if \(\$EnableGptNewWrite\) \{.*?'--allow-write'.*?\}",
        installer,
        re.DOTALL,
    )
    assert re.search(
        r"if \(\(\$EnableGptNewExec -or \$EnableGptNewWrite\) -and\s+"
        r"-not \$GptNewThreadId\)",
        installer,
    )


def test_installer_declares_the_three_host_local_runtime_mounts():
    installer = (ROOT / "scripts" / "install_sunshine_discord_tasks.ps1").read_text(
        encoding="utf-8"
    )

    assert "RuntimeConfigRoot" in installer
    assert ".aurora-world" in installer
    assert "ItemType Junction" in installer
    assert "ItemType SymbolicLink" in installer
    assert "security\\acl.json" in installer


def test_installer_owns_one_gateway_and_repurposes_watchdog_as_task_nudge():
    installer = (ROOT / "scripts" / "install_sunshine_discord_tasks.ps1").read_text(
        encoding="utf-8"
    )

    assert "AkashicAurora-DiscordGateway" in installer
    assert "bifrost_runner_discord.py" in installer
    assert "AkashicAurora-EarWatchdog" in installer
    assert "schtasks.exe" in installer
    assert "Disable-ScheduledTask" not in installer


def test_installer_whatif_accepts_an_explicit_runtime_config_root():
    if os.name != "nt":
        return
    installer = ROOT / "scripts" / "install_sunshine_discord_tasks.ps1"
    run = subprocess.run(
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
            "-RepoRoot",
            str(ROOT),
            "-RuntimeConfigRoot",
            str(ROOT),
            "-PythonExe",
            sys.executable,
            "-WhatIf",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 0, run.stdout + run.stderr
