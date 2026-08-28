"""T084 S3 pre-registered pins -- continuity is evidence, never identity synthesis.

The profile is deliberately subject-bound and read-only.  Only the ratified
resident registry may supply a designation; every other region keeps its weaker
authority label and exact attribution.
"""
from __future__ import annotations

import argparse
import asyncio
import json

import pytest


REGION_ORDER = [
    "designation",
    "lessons",
    "notes",
    "handoffs",
    "artifacts",
    "movement",
]


def _batch(items, source="fixture", *, total=None, scanned=None, truncated=False, blind=None):
    rows = list(items)
    return {
        "items": rows,
        "total": len(rows) if total is None else total,
        "scanned": len(rows) if scanned is None else scanned,
        "truncated": truncated,
        "source": source,
        "ordering": "fixture order",
        "blind": list(blind or []),
    }


def _empty_sources(**overrides):
    sources = {
        name: (lambda _subject, _name=name: _batch([], source=f"fixture:{_name}"))
        for name in REGION_ORDER
    }
    sources.update(overrides)
    return sources


def _regions(result):
    return {row["name"]: row for row in result["regions"]}


def test_profile_has_bounded_regions_and_explicitly_refuses_an_identity_verdict():
    from core.coord.continuity import build_profile

    result = build_profile(
        "sol",
        sources=_empty_sources(),
        observed_at="2026-08-28T07:00:00Z",
    )

    assert result["schema"] == "ground.result.v1"
    assert result["mode"] == "continuity"
    assert result["target"] == {"kind": "seat", "name": "sol"}
    assert result["subject"] == "sol"
    assert result["effects"] == []
    assert result["identity_verdict"]["state"] == "not_computed"
    assert "resident registry" in result["identity_verdict"]["claim"].lower()
    assert [row["name"] for row in result["regions"]] == REGION_ORDER
    assert result["bounds"]["ordering"] == REGION_ORDER

    for row in result["regions"]:
        assert row["state"] in {"observed", "partial", "absent", "unknown"}
        assert row["claim"]
        assert row["source"]
        assert row["currency"]["observed_at"].endswith("Z")
        assert row["currency"]["basis"]
        assert row["bounds"]["shown"] == len(row["items"])
        assert isinstance(row["blind"], list)
        assert row["drill"]


def test_only_a_ratified_subject_record_can_supply_a_designation():
    from core.coord.continuity import build_profile

    unratified = {
        "state": "nominated",
        "agent_id": "sol",
        "callsign": "A Name Still Awaiting Ceremony",
        "receipts": ["own-receipt"],
        "by": "peer",
        "at": 10,
    }
    result = build_profile(
        "sol",
        sources=_empty_sources(
            designation=lambda _subject: _batch([unratified], "resident fixture")
        ),
    )
    designation = _regions(result)["designation"]
    assert designation["state"] == "absent"
    assert designation["items"] == []
    assert "unratified" in " ".join(designation["blind"]).lower()
    assert "callsign" not in result["identity_verdict"]

    ratified = dict(unratified, state="ratified", callsign="Sunshine",
                    ratified_by="daniil", at=20)
    result = build_profile(
        "sol",
        sources=_empty_sources(
            designation=lambda _subject: _batch([ratified], "resident fixture")
        ),
    )
    designation = _regions(result)["designation"]
    assert designation["state"] == "observed"
    assert designation["authority"] == "ratified_resident_registry"
    assert designation["items"][0]["callsign"] == "Sunshine"
    assert designation["items"][0]["receipts"] == ["learn:experiment:own-receipt"]
    assert designation["items"][0]["ratified_by"] == "daniil"


def test_each_region_filters_exact_subject_and_preserves_weaker_authority():
    from core.coord.continuity import build_profile

    sources = _empty_sources(
        lessons=lambda _s: _batch([
            {"id": "own", "agent_id": "sol", "experiment": "own", "result": "worked",
             "timestamp": "2026-08-28T01:00:00Z"},
            {"id": "foreign", "agent_id": "other", "experiment": "mentions-sol",
             "result": "Sol appears in prose", "timestamp": "2026-08-28T02:00:00Z"},
        ], "learning fixture"),
        notes=lambda _s: _batch([
            {"id": "n-own", "title": "scratch:sol:voice", "decision": "keep warmth",
             "created_at": "2026-08-28T03:00:00Z"},
            {"id": "n-foreign", "title": "scratch:other:about-sol",
             "decision": "Sol appears in prose", "created_at": "2026-08-28T04:00:00Z"},
        ], "note fixture"),
        handoffs=lambda _s: _batch([
            {"signal_id": "h-out", "signal_type": "handoff", "agent_id": "sol",
             "target_agent": "other", "task": "outbound", "timestamp": "2026-08-28T05:00:00Z"},
            {"signal_id": "h-in", "signal_type": "handoff", "agent_id": "other",
             "target_agent": "sol", "task": "inbound", "timestamp": "2026-08-28T06:00:00Z"},
            {"signal_id": "h-foreign", "signal_type": "handoff", "agent_id": "a",
             "target_agent": "b", "task": "Sol appears in prose"},
        ], "handoff fixture"),
        artifacts=lambda _s: _batch([
            {"id": "a-own", "header": {"seats": ["sol"], "title": "ours",
             "date": "2026-08-28", "type": "report", "gist": "attributed"}},
            {"id": "a-foreign", "header": {"seats": ["other"], "title": "about Sol",
             "date": "2026-08-28", "type": "report", "gist": "Sol in prose"},
             "body": "Sol"},
        ], "artifact fixture"),
        movement=lambda _s: _batch([
            {"id": "m-own", "agent_id": "sol", "kind": "command", "summary": "worked",
             "at": "2026-08-28T07:00:00Z", "_ref": "event:events:raw:1"},
            {"id": "m-foreign", "agent_id": "other", "kind": "note",
             "summary": "Sol in prose", "at": "2026-08-28T08:00:00Z"},
        ], "movement fixture"),
    )
    result = build_profile("sol", sources=sources)
    regions = _regions(result)

    assert [r["id"] for r in regions["lessons"]["items"]] == ["own"]
    assert regions["lessons"]["authority"] == "exact_lesson_authorship"
    assert [r["id"] for r in regions["notes"]["items"]] == ["n-own"]
    assert regions["notes"]["authority"] == "subject_scoped_not_author_verified"
    assert "not prove authorship" in regions["notes"]["claim"].lower()
    assert {r["direction"] for r in regions["handoffs"]["items"]} == {"inbound", "outbound"}
    assert regions["handoffs"]["authority"] == "directional_attribution"
    assert [r["id"] for r in regions["artifacts"]["items"]] == ["a-own"]
    assert regions["artifacts"]["authority"] == "header_attribution_not_authorship"
    assert [r["id"] for r in regions["movement"]["items"]] == ["m-own"]
    assert regions["movement"]["authority"] == "telemetry_attribution_not_identity"


def test_prose_mentions_never_mint_a_name_and_bounds_remain_loud():
    from core.coord.continuity import build_profile

    notes = [
        {"id": f"n-{i}", "title": f"scratch:sol:{i}",
         "decision": "Friends sometimes call this seat Mirage", "created_at": f"2026-08-2{i}T00:00:00Z"}
        for i in range(1, 5)
    ]
    result = build_profile(
        "sol",
        sources=_empty_sources(
            notes=lambda _s: _batch(notes, "bounded notes", total=40, scanned=4,
                                     truncated=True, blind=["older notes outside window"])
        ),
        limits={"notes": 2},
    )
    region = _regions(result)["notes"]
    assert region["bounds"]["matched"] == 4
    assert region["bounds"]["shown"] == 2
    assert region["bounds"]["truncated"] is True
    assert "older notes outside window" in region["blind"]
    assert "callsign" not in result["identity_verdict"]
    assert not any("callsign" in row for row in region["items"])


def test_source_failure_is_unknown_not_evidence_of_absence():
    from core.coord.continuity import build_profile

    def unavailable(_subject):
        raise RuntimeError("fixture archive offline")

    result = build_profile(
        "sol",
        sources=_empty_sources(lessons=unavailable),
    )
    lessons = _regions(result)["lessons"]
    assert lessons["state"] == "unknown"
    assert lessons["items"] == []
    assert "unavailable" in " ".join(lessons["blind"]).lower()
    assert result["bounds"]["sources_failed"] == 1


def test_region_drills_never_invent_cli_grammar():
    import agent_cli
    from core.coord.continuity import build_profile

    result = build_profile("sol", sources=_empty_sources())
    regions = _regions(result)
    parser = agent_cli.build_parser()

    # These are executable escape hatches, so the live parser must accept them.
    parser.parse_args(["resident", "show", "sol"])
    parser.parse_args(["recall", "--agent", "sol", "--json"])
    parser.parse_args(["handoff", "sol", "--list", "--to", "sol", "--json"])
    parser.parse_args(["events", "--agent", "sol", "--limit", "25", "--json"])

    assert regions["designation"]["drill"] == "py agent_cli.py resident show sol"
    assert regions["lessons"]["drill"] == "py agent_cli.py recall --agent sol --json"
    assert "no dedicated exact atom read door" in regions["artifacts"]["drill"]
    assert "docs" not in regions["artifacts"]["drill"]


def test_ground_requires_continuity_mode_and_exact_subject_binding(monkeypatch):
    from core.coord import continuity
    from core.coord.ground import ground

    sentinel = {
        "schema": "ground.result.v1", "mode": "continuity",
        "target": {"kind": "seat", "name": "sol"}, "subject": "sol",
        "regions": [], "bounds": {}, "blind": [], "effects": [],
        "identity_verdict": {"state": "not_computed", "claim": "fixture"},
    }
    monkeypatch.setattr(continuity, "build_profile", lambda subject: dict(sentinel))
    assert ground("seat:sol", subject="sol", continuity=True)["mode"] == "continuity"

    with pytest.raises(ValueError, match="--continuity"):
        ground("seat:sol", subject="sol", continuity=False)
    with pytest.raises(ValueError, match="match"):
        ground("seat:other", subject="sol", continuity=True)
    with pytest.raises(ValueError, match="match"):
        ground("seat:Sol", subject="sol", continuity=True)
    with pytest.raises(ValueError, match="only for seat"):
        ground("verb:sweep", subject="sol", continuity=True)


def test_cli_mcp_and_toolbox_are_native_and_toolbox_cannot_borrow_a_seat(monkeypatch, tmp_path):
    import agent_cli
    import ai_setup_mcp
    from core.comm.toolbox import TOOLS, ToolBox
    from core.coord import ground as ground_module

    parser = agent_cli.build_parser()
    subs = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    args = parser.parse_args(["ground", "seat:sol", "--continuity", "--agent", "sol"])
    assert args.target == "seat:sol" and args.continuity is True
    assert "ground" in {row["function"]["name"] for row in TOOLS}

    calls = []

    def fake_ground(target, *, subject, continuity=False):
        calls.append((target, subject, continuity))
        return {"schema": "ground.result.v1", "target": {"kind": "seat", "name": subject},
                "subject": subject, "mode": "continuity", "regions": [], "bounds": {},
                "blind": [], "effects": [],
                "identity_verdict": {"state": "not_computed", "claim": "fixture"}}

    monkeypatch.setattr(ground_module, "ground", fake_ground)
    raw = asyncio.run(ai_setup_mcp.ground(target="seat:sol", agent="sol", continuity=True))
    assert json.loads(raw)["subject"] == "sol"

    tb = ToolBox(tmp_path, allow_exec=False, trust=False, allow_secrets=False,
                 confirm=lambda *_: False, agent_id="sol")
    monkeypatch.setattr(tb, "_agent_cli", lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("ground must not shell through agent_cli")))
    assert json.loads(tb.ground("seat:sol", continuity=True))["subject"] == "sol"
    with pytest.raises(ValueError, match="bound identity"):
        tb.ground("seat:other", subject="other", continuity=True)
    assert calls == [
        ("seat:sol", "sol", True),
        ("seat:sol", "sol", True),
    ]
