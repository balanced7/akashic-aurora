"""T084 intent-shadow v1 RED pins: see the action before reality changes.

The 2026-07-28 VR contract puts the first deterministic shadow at the
deploy/send door.  It must show target, fidelity, scope, proposed effects,
cost, reversibility, authority, risk, and the five-axis epistemic floor while
the preview itself performs no effects.  It must also ask the actual ToolBox
authorization detector rather than maintain a more flattering second policy.

Pre-registered baseline (ADR_0828204749_2f3e1c67): the closest existing
composition, ``ground + ToolBox schema``, measured 70.55 ms hot median and
4,602 compact JSON characters.  The live slice must measure <=35 ms median and
the representative nudge shadow below must stay <=3,000 characters.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pydoc import locate
import subprocess
import sys

import pytest


SUBJECT = "synthetic-sol-t084-shadow"
AXES = {"authority", "claim_kind", "currency", "identity_state", "risk"}


def _allowed(subject: str, action: str, arguments):
    assert subject == SUBJECT
    return {
        "state": "observed",
        "allowed": True,
        "role": "fixture-member",
        "required_caps": ["bus.send", "bus.nudge"],
        "missing_caps": [],
        "kind_allowed": True,
        "source": ["fixture:effective-grant", "fixture:toolbox-gate"],
    }


def _resolved(raw: str) -> str:
    return {"vandor": "claude"}.get(str(raw).lower(), str(raw).lower())


def _nudge(*, observed_at="2026-08-29T00:00:00Z"):
    from core.coord.intent_shadow import build_intent_shadow

    return build_intent_shadow(
        SUBJECT,
        "toolbox:bifrost_nudge",
        {"to": "Vandor", "text": "please look now"},
        authorize=_allowed,
        resolve_recipient=_resolved,
        observed_at=observed_at,
    )


def test_nudge_shadow_is_a_complete_subject_bound_zero_effect_ghost():
    shadow = _nudge()

    assert shadow["schema"] == "intent.shadow.v1"
    assert shadow["subject"] == SUBJECT
    assert shadow["action"] == {
        "door": "toolbox",
        "name": "bifrost_nudge",
        "address": "toolbox:bifrost_nudge",
    }
    assert shadow["target"] == {
        "kind": "seat",
        "addressed_as": "Vandor",
        "resolved": "claude",
    }
    assert shadow["fidelity"] == "interrupt"
    assert shadow["scope"]["planes"] == [
        "bifrost.delivery", "peer.control", "recipient.attention"
    ]
    assert shadow["effects"] == [], "building a shadow must never perform the proposal"

    proposed = {row["id"]: row for row in shadow["proposed_effects"]}
    assert proposed["peer.control.interrupt_flag"]["certainty"] == "expected"
    assert proposed["bifrost.message.enqueue"]["certainty"] == "expected"
    assert proposed["recipient.turn.interrupt"]["certainty"] == "conditional"
    assert all(row["basis"] for row in proposed.values())

    assert shadow["cost"]["verb_calls"] == 1
    assert shadow["cost"]["content_chars"] == len("please look now")
    assert shadow["cost"]["rough_content_tokens"] >= 1
    assert shadow["cost"]["recipient_model_turns"]["state"] == "conditional"
    assert shadow["reversibility"]["state"] == "irreversible_after_observation"
    assert shadow["risk"]["level"] == "high"
    assert shadow["commit"] == {
        "required": True,
        "enforced": False,
        "state": "required_unenforced",
        "reason": "hard interrupt can displace a peer's current work",
    }
    assert shadow["authority"]["allowed"] is True
    assert AXES == set(shadow["epistemic"])
    assert shadow["blind"]
    assert len(shadow["fingerprint"]) == 64


def test_semantic_fingerprint_excludes_observation_time_but_binds_content():
    first = _nudge(observed_at="2026-08-29T00:00:00Z")
    later = _nudge(observed_at="2026-08-29T00:01:00Z")
    assert first["observed_at"] != later["observed_at"]
    assert first["fingerprint"] == later["fingerprint"]

    from core.coord.intent_shadow import build_intent_shadow
    changed = build_intent_shadow(
        SUBJECT, "toolbox:bifrost_nudge",
        {"to": "Vandor", "text": "a different request"},
        authorize=_allowed, resolve_recipient=_resolved,
        observed_at="2026-08-29T00:01:00Z",
    )
    assert changed["fingerprint"] != first["fingerprint"]


def test_send_with_nudge_kind_does_not_claim_the_hard_interrupt_flag():
    """The ordinary send door can label a packet ``nudge`` but does not set the
    control flag.  Only the dedicated nudge action performs both effects."""
    from core.coord.intent_shadow import build_intent_shadow

    sent = build_intent_shadow(
        SUBJECT, "toolbox:bifrost_send",
        {"to": "Vandor", "kind": "nudge", "text": "look"},
        authorize=_allowed, resolve_recipient=_resolved,
        observed_at="2026-08-29T00:00:00Z",
    )
    nudge = _nudge()
    sent_ids = {row["id"] for row in sent["proposed_effects"]}
    nudge_ids = {row["id"] for row in nudge["proposed_effects"]}
    assert "peer.control.interrupt_flag" not in sent_ids
    assert "peer.control.interrupt_flag" in nudge_ids
    assert sent["fidelity"] == "message:nudge"
    assert sent["commit"]["required"] is True


def test_steer_names_soft_queue_and_never_claims_hard_interruption():
    from core.coord.intent_shadow import build_intent_shadow

    shadow = build_intent_shadow(
        SUBJECT, "toolbox:bifrost_steer",
        {"to": "Vandor", "text": "fold this in"},
        authorize=_allowed, resolve_recipient=_resolved,
        observed_at="2026-08-29T00:00:00Z",
    )
    ids = {row["id"] for row in shadow["proposed_effects"]}
    assert shadow["fidelity"] == "steer"
    assert "peer.control.steer_queue" in ids
    assert "recipient.context.splice" in ids
    assert "peer.control.interrupt_flag" not in ids
    assert shadow["risk"]["level"] == "elevated"
    assert shadow["commit"]["required"] is True


def test_every_proposed_effect_basis_resolves_to_a_live_symbol():
    from core.coord.intent_shadow import build_intent_shadow

    rows = []
    for action, arguments in (
        ("toolbox:bifrost_nudge", {"to": "Vandor", "text": "look"}),
        ("toolbox:bifrost_steer", {"to": "Vandor", "text": "fold this in"}),
        ("toolbox:bifrost_send", {
            "to": "Vandor", "kind": "handoff", "text": "continue here",
        }),
    ):
        shadow = build_intent_shadow(
            SUBJECT, action, arguments,
            authorize=_allowed, resolve_recipient=_resolved,
            observed_at="2026-08-29T00:00:00Z",
        )
        rows.extend(shadow["proposed_effects"])

    missing = sorted({row["basis"] for row in rows if locate(row["basis"]) is None})
    assert not missing, f"proposed-effect evidence pointers do not resolve: {missing}"


@pytest.mark.parametrize("target", ["bifrost_nudge", "mcp:bifrost_nudge", "toolbox:nope"])
def test_untyped_foreign_or_unmapped_actions_refuse_instead_of_guessing(target):
    from core.coord.intent_shadow import build_intent_shadow

    with pytest.raises(ValueError, match="toolbox:|unsupported"):
        build_intent_shadow(
            SUBJECT, target, {"to": "claude", "text": "x"},
            authorize=_allowed, resolve_recipient=_resolved,
        )


def test_required_arguments_and_broadcast_boundaries_match_the_real_toolbox_schema():
    from core.coord.intent_shadow import build_intent_shadow

    with pytest.raises(ValueError, match="required argument.*text"):
        build_intent_shadow(
            SUBJECT, "toolbox:bifrost_nudge", {"to": "claude"},
            authorize=_allowed, resolve_recipient=_resolved,
        )
    with pytest.raises(ValueError, match="one seat"):
        build_intent_shadow(
            SUBJECT, "toolbox:bifrost_nudge", {"to": "*", "text": "x"},
            authorize=_allowed, resolve_recipient=_resolved,
        )


def test_recipient_resolution_failure_refuses_instead_of_guessing(monkeypatch):
    from core.coord.intent_shadow import build_intent_shadow
    from core.fleet import residents

    def broken_resolver(_raw):
        raise OSError("resident authority is unreadable")

    monkeypatch.setattr(residents, "resolve_agent", broken_resolver)
    with pytest.raises(RuntimeError, match="could not resolve load-bearing target"):
        build_intent_shadow(
            SUBJECT, "toolbox:bifrost_nudge",
            {"to": "Vandor", "text": "look"}, authorize=_allowed,
        )


def test_compact_shadow_beats_the_preregistered_payload_bar():
    raw = json.dumps(_nudge(), ensure_ascii=False, separators=(",", ":"), default=str)
    assert len(raw) <= 3000


def test_actual_toolbox_gate_and_shadow_ask_the_same_authority_detector(monkeypatch, tmp_path):
    from core.comm.toolbox import ToolBox
    from core.coord.intent_shadow import build_intent_shadow
    from core.trust import action_authority

    calls = []

    def refused(subject, action, arguments):
        calls.append((subject, action, dict(arguments)))
        return {
            "state": "refused", "allowed": False, "role": "fixture",
            "required_caps": ["bus.send", "bus.nudge"],
            "missing_caps": ["bus.nudge"], "kind_allowed": True,
            "source": ["fixture:gate"],
            "execution_error": "REFUSED BY THE SHARED DETECTOR",
        }

    monkeypatch.setattr(action_authority, "evaluate_toolbox_bus_action", refused)
    shadow = build_intent_shadow(
        SUBJECT, "toolbox:bifrost_nudge",
        {"to": "claude", "text": "look"}, resolve_recipient=_resolved,
        observed_at="2026-08-29T00:00:00Z",
    )
    assert shadow["authority"]["state"] == "refused"
    assert shadow["authority"]["missing_caps"] == ["bus.nudge"]
    assert shadow["effects"] == []

    tb = ToolBox(
        tmp_path, allow_exec=False, trust=False, allow_secrets=False,
        confirm=lambda *_: False, agent_id=SUBJECT,
    )
    assert tb._bus_send_ok(
        action="bifrost_nudge", kind="nudge"
    ) == "REFUSED BY THE SHARED DETECTOR"
    assert calls == [
        (SUBJECT, "bifrost_nudge", {"to": "claude", "text": "look"}),
        (SUBJECT, "bifrost_nudge", {"kind": "nudge"}),
    ]


def test_cli_mcp_and_toolbox_share_one_native_shadow_seam(monkeypatch, tmp_path):
    import agent_cli
    import ai_setup_mcp
    from core.comm.toolbox import TOOLS, ToolBox
    from core.coord import intent_shadow as shadow_module
    from scripts.checkers import check_door_parity

    fixture = {
        "schema": "intent.shadow.v1", "subject": SUBJECT,
        "action": {"door": "toolbox", "name": "bifrost_nudge",
                   "address": "toolbox:bifrost_nudge"},
        "effects": [], "fingerprint": "f" * 64,
    }
    calls = []

    def fake(subject, target, arguments=None, **kwargs):
        calls.append((subject, target, dict(arguments or {})))
        return dict(fixture)

    monkeypatch.setattr(shadow_module, "build_intent_shadow", fake)

    parser = agent_cli.build_parser()
    subs = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    parsed = parser.parse_args([
        "shadow", "toolbox:bifrost_nudge", "--agent", SUBJECT,
        "--args-json", '{"to":"claude","text":"look"}', "--json",
    ])
    assert parsed.fn is agent_cli.cmd_shadow
    assert parsed.target == "toolbox:bifrost_nudge"

    raw = asyncio.run(ai_setup_mcp.shadow(
        agent=SUBJECT, target="toolbox:bifrost_nudge",
        arguments={"to": "claude", "text": "look"},
    ))
    assert json.loads(raw)["schema"] == "intent.shadow.v1"
    assert "\n" not in raw

    advertised = {row["function"]["name"] for row in TOOLS}
    assert "shadow" in advertised
    assert check_door_parity.MANIFEST["shadow"] == "shared"

    tb = ToolBox(
        tmp_path, allow_exec=False, trust=False, allow_secrets=False,
        confirm=lambda *_: False, agent_id=SUBJECT,
    )
    tb_raw = tb.shadow("toolbox:bifrost_nudge", {"to": "claude", "text": "look"})
    assert json.loads(tb_raw)["schema"] == "intent.shadow.v1"
    assert "\n" not in tb_raw
    assert calls == [
        (SUBJECT, "toolbox:bifrost_nudge", {"to": "claude", "text": "look"}),
        (SUBJECT, "toolbox:bifrost_nudge", {"to": "claude", "text": "look"}),
    ]


def test_fresh_mcp_stdio_server_advertises_and_serves_the_real_shadow(tmp_path):
    """Prove the negotiated MCP door, not just an imported Python function.

    The MCP server owns its process stdout, so this intentionally follows the
    same stdio transport a newly connected harness negotiates.
    """
    async def flow():
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        params = StdioServerParameters(
            command=sys.executable,
            args=[os.path.join(root, "ai_setup_mcp.py")],
            cwd=root,
            env={
                **os.environ,
                "_AISETUP_TEST_ISOLATED": "1",
                "REDIS_DB": "15",
                "AKASHIC_RECALL_STATE_DIR": str(tmp_path / "recall"),
            },
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = {tool.name for tool in (await session.list_tools()).tools}
                assert "shadow" in tools

                result = await asyncio.wait_for(
                    session.call_tool("shadow", {
                        "agent": SUBJECT,
                        "target": "toolbox:bifrost_nudge",
                        "arguments": {"to": "sol", "text": "transport proof only"},
                    }),
                    timeout=10.0,
                )
                text = "".join(getattr(part, "text", "") for part in result.content)
                shadow = json.loads(text)
                assert shadow["schema"] == "intent.shadow.v1"
                assert shadow["subject"] == SUBJECT
                assert shadow["action"]["address"] == "toolbox:bifrost_nudge"
                assert shadow["effects"] == []
                assert len(shadow["fingerprint"]) == 64

    asyncio.run(flow())


def test_fresh_cli_process_serves_the_real_shadow_without_effects(tmp_path):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [
            sys.executable, os.path.join(root, "agent_cli.py"),
            "shadow", "toolbox:bifrost_nudge", "--agent", SUBJECT,
            "--args-json", '{"to":"sol","text":"CLI transport proof only"}',
            "--json",
        ],
        cwd=root,
        env={
            **os.environ,
            "_AISETUP_TEST_ISOLATED": "1",
            "REDIS_DB": "15",
            "AKASHIC_RECALL_STATE_DIR": str(tmp_path / "recall"),
        },
        capture_output=True,
        text=True,
        timeout=10.0,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    shadow = json.loads(result.stdout)
    assert shadow["schema"] == "intent.shadow.v1"
    assert shadow["subject"] == SUBJECT
    assert shadow["action"]["address"] == "toolbox:bifrost_nudge"
    assert shadow["effects"] == []


def test_bound_toolbox_serves_the_real_shadow_without_effects(tmp_path):
    from core.comm.toolbox import ToolBox

    toolbox = ToolBox(
        tmp_path, allow_exec=False, trust=False, allow_secrets=False,
        confirm=lambda *_: False, agent_id=SUBJECT,
    )
    shadow = json.loads(toolbox.shadow(
        "toolbox:bifrost_nudge", {"to": "sol", "text": "ToolBox proof only"},
    ))
    assert shadow["schema"] == "intent.shadow.v1"
    assert shadow["subject"] == SUBJECT
    assert shadow["action"]["address"] == "toolbox:bifrost_nudge"
    assert shadow["effects"] == []


def test_unbound_toolbox_cannot_borrow_a_shadow_subject(tmp_path):
    from core.comm.toolbox import ToolBox

    tb = ToolBox(
        tmp_path, allow_exec=False, trust=False, allow_secrets=False,
        confirm=lambda *_: False,
    )
    with pytest.raises(ValueError, match="subject is required"):
        tb.shadow("toolbox:bifrost_nudge", {"to": "claude", "text": "look"})


def test_ground_knows_shadow_is_an_open_read_seam_on_every_door():
    from core.coord.ground import ground

    result = ground("verb:shadow", subject="sol")
    authorized = next(row for row in result["rungs"] if row["name"] == "authorized")
    assert authorized["state"] == "observed"
    assert {
        door: row["state"]
        for door, row in authorized["details"]["doors"].items()
    } == {"cli": "observed", "mcp": "observed", "toolbox": "observed"}
