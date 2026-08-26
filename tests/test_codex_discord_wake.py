"""RED contracts for the isolated Discord-to-Codex wake policy."""
from __future__ import annotations

import json

from agent.harness.codex_bifrost_wake import WakePolicy
from core.comm import packet_spec
from core.comm.bus import Bus
from scripts.codex_bifrost_wake import build_parser


class _UnusedClient:
    pass


def _message(*, sender: str = "daniil", kind: str = "chat", source: str = "discord"):
    fields = {
        "frm": sender,
        "to": "sol",
        "kind": kind,
        "content": json.dumps("A message for Sol"),
        "parts": "[]",
        "meta": json.dumps({"source": source, "operator": True}),
        "ts": "2026-08-26T00:00:00+00:00",
    }
    packet_spec.stamp(fields)
    return Bus("sol", client=_UnusedClient(), promote=False)._to_msg("80-0", fields)


def test_discord_operator_policy_requires_sender_kind_and_source_together():
    policy = WakePolicy(
        agent="sol",
        allowed_senders=frozenset({"daniil"}),
        direct_kinds=frozenset({"chat"}),
        required_source="discord",
    )

    assert policy.accepts(_message()) is True
    assert policy.accepts(_message(sender="not-daniil")) is False
    assert policy.accepts(_message(kind="trace")) is False
    assert policy.accepts(_message(source="not-discord")) is False


def test_cli_exposes_an_explicit_additive_kind_and_required_source_gate():
    args = build_parser().parse_args([
        "--allow-from", "daniil",
        "--allow-kind", "chat",
        "--require-source", "discord",
        "--state-path", "sol-discord.state.json",
        "--log-path", "sol-discord.events.jsonl",
    ])

    assert args.allow_from == ["daniil"]
    assert args.allow_kind == ["chat"]
    assert args.require_source == "discord"
    assert args.state_path != "sol.state.json"
