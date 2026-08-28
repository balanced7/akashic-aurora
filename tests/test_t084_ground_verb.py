"""T084 S1 pre-registered pins — truthful verb grounding.

The feature does not exist in the RED commit.  These pins establish that a
static declaration, an effective grant, a test reference, and a live receipt
remain different evidence rungs.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from types import SimpleNamespace


RUNG_ORDER = [
    "declared",
    "reachable",
    "authorized",
    "wired",
    "exercised",
    "proven",
]


def _rungs(result):
    return {row["name"]: row for row in result["rungs"]}


def test_sweep_grounding_keeps_the_six_evidence_rungs_distinct():
    from core.coord.ground import ground

    result = ground("verb:sweep", subject="t084-unregistered-seat")

    assert result["schema"] == "ground.result.v1"
    assert result["target"] == {"kind": "verb", "name": "sweep"}
    assert result["subject"] == "t084-unregistered-seat"
    assert result["effects"] == []
    assert [row["name"] for row in result["rungs"]] == RUNG_ORDER
    assert result["bounds"]["sources_total"] >= 3
    assert isinstance(result["blind"], list)
    for row in result["rungs"]:
        assert row["state"] in {"observed", "partial", "absent", "refused", "unknown"}
        assert row["claim"]
        assert row["source"]
        assert row["observed_at"].endswith("Z")
        assert row["drill"]

    rungs = _rungs(result)
    assert rungs["declared"]["state"] == "observed"
    assert rungs["declared"]["details"]["classification"] == "shared"
    assert set(rungs["reachable"]["details"]["doors"]) == {"cli", "mcp", "toolbox"}
    assert all(row["present"] for row in rungs["reachable"]["details"]["doors"].values())
    assert rungs["wired"]["state"] == "observed"
    # A test-file reference is evidence of intent, not evidence of a green run.
    assert rungs["exercised"]["state"] == "partial"
    assert rungs["proven"]["state"] == "unknown"


def test_effective_grant_can_refuse_without_erasing_door_presence():
    from core.coord.ground import ground

    result = ground("verb:bifrost-send", subject="t084-unregistered-seat")
    rungs = _rungs(result)

    assert rungs["reachable"]["details"]["doors"]["cli"]["present"] is True
    assert rungs["authorized"]["state"] == "refused"
    assert rungs["authorized"]["details"]["required_caps"] == ["bus.send"]
    assert rungs["authorized"]["details"]["role"] == "quarantined"
    assert rungs["authorized"]["details"]["missing_caps"] == ["bus.send"]


def test_unknown_verb_and_missing_receipt_never_become_false_proof():
    from core.coord.ground import ground

    result = ground("verb:definitely-not-a-real-verb", subject="sol")
    rungs = _rungs(result)

    assert rungs["declared"]["state"] == "absent"
    assert rungs["reachable"]["state"] == "absent"
    assert rungs["wired"]["state"] == "absent"
    assert rungs["proven"]["state"] == "unknown"
    assert "receipt" in rungs["proven"]["claim"].lower()


def test_reach_is_a_ground_rung_not_a_second_public_verb():
    import agent_cli

    parser = agent_cli.build_parser()
    subs = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    assert "ground" in subs.choices
    assert "reach" not in subs.choices


def test_cli_refuses_to_borrow_a_foreign_subject(monkeypatch, capsys):
    import agent_cli

    monkeypatch.delenv("AKASHIC_AGENT_ID", raising=False)
    rc = agent_cli.cmd_ground(SimpleNamespace(target="verb:sweep", agent="", json=True,
                                               continuity=False))
    assert rc == 2
    assert "subject is required" in capsys.readouterr().out


def test_mcp_and_toolbox_use_the_native_grounding_seam(monkeypatch, tmp_path):
    import ai_setup_mcp
    from core.comm.toolbox import ToolBox

    raw = asyncio.run(ai_setup_mcp.ground(target="verb:sweep", agent="sol",
                                          continuity=False))
    assert json.loads(raw)["schema"] == "ground.result.v1"

    tb = ToolBox(tmp_path, allow_exec=False, trust=False, allow_secrets=False,
                 confirm=lambda *_: False, agent_id="sol")
    monkeypatch.setattr(tb, "_agent_cli", lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("ground must not shell through agent_cli")))
    assert json.loads(tb.ground("verb:sweep"))["subject"] == "sol"


def test_toolbox_without_identity_requires_an_explicit_subject(tmp_path):
    from core.comm.toolbox import ToolBox

    tb = ToolBox(tmp_path, allow_exec=False, trust=False, allow_secrets=False,
                 confirm=lambda *_: False)
    try:
        tb.ground("verb:sweep")
    except ValueError as exc:
        assert "subject is required" in str(exc)
    else:
        raise AssertionError("unbound ToolBox borrowed an identity")
