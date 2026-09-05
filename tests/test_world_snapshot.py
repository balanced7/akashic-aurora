"""Contract pins for the fenced T060 WorldSnapshot first vertical.

Authority: art_20260729_world-snapshot-glance-projection-fleet-d_218aef.
Build gate: Daniil's explicit 2026-09-02 request that Sunshine lead the scaffold.

This is the SUBJECT / ATTENTION read model, not ``scripts/snapshot.py`` and not
the ``core.world`` runtime-routing family.  It has no action, identity, cursor,
settlement, or wake authority.
"""
from __future__ import annotations

import copy
import json

import pytest

from core.context import world_snapshot as world_snapshot_module
from core.context.world_snapshot import (
    assemble_world_snapshot,
    build_program_world_snapshot,
    project_operational_brief,
)


def _source(*, revision: str = "sha256:ledger-v1", checked_at: str = "2026-09-02T20:00:00Z"):
    return {
        "name": "task-ledger-git",
        "plane": "durable-ledger",
        "authority": "governed_source",
        "revision": revision,
        "checked_at": checked_at,
        "drill": "state/coord/tasks.json",
    }


def _view(source_basis: str = "source:task-ledger-git@sha256:ledger-v1"):
    return {
        "authority": {"value": "governed_source", "basis": [source_basis]},
        "claim_kind": {"value": "observed", "basis": ["field:task.status"]},
        "currency": {
            "value": "current",
            "basis": [source_basis],
            "checked_at": "2026-09-02T20:00:00Z",
        },
        "identity_state": {"value": "unknown", "basis": []},
        "risk": {"value": "unknown", "basis": []},
    }


def _item(ref: str = "task:T079", *, attention: str = "ACTING"):
    return {
        "object_ref": ref,
        "organ": "ledger",
        "attention": attention,
        "source_refs": ["task-ledger-git"],
        "data": {"id": ref.split(":", 1)[-1], "status": "in_progress"},
        "epistemic_view": _view(),
    }


def _capabilities():
    return {
        "subject_attention": {
            "state": "SUPPORTED",
            "basis": ["policy:task-status-attention/v1"],
        },
        "deduplication": {
            "state": "UNCHECKABLE",
            "blocked_by": "T116",
            "reason": "logical message identity is not yet authoritative",
        },
    }


def test_snapshot_identity_is_derived_not_a_second_clock_or_ledger():
    first = assemble_world_snapshot(
        subject="aurora-program",
        sources=[_source(checked_at="2026-09-02T20:00:00Z")],
        items=[_item()],
        capabilities=_capabilities(),
        generated_at="2026-09-02T20:00:01Z",
    )
    later_same_world = assemble_world_snapshot(
        subject="aurora-program",
        sources=[_source(checked_at="2026-09-02T21:00:00Z")],
        items=[_item()],
        capabilities=_capabilities(),
        generated_at="2026-09-02T21:00:01Z",
    )
    changed_source = assemble_world_snapshot(
        subject="aurora-program",
        sources=[_source(revision="sha256:ledger-v2")],
        items=[_item()],
        capabilities=_capabilities(),
        generated_at="2026-09-02T21:00:01Z",
    )

    assert first["snapshot_id"].startswith("ws_")
    assert first["snapshot_id"] == later_same_world["snapshot_id"]
    assert first["snapshot_id"] != changed_source["snapshot_id"]
    assert "sequence" not in first


def test_snapshot_projection_and_render_identities_name_different_things():
    rows = [_item("task:T001", attention="ATTENTION"), _item("task:T002")]
    wide = assemble_world_snapshot(
        subject="aurora-program",
        sources=[_source()],
        items=rows,
        capabilities=_capabilities(),
        generated_at="2026-09-02T20:00:01Z",
        max_items=2,
    )
    narrow = assemble_world_snapshot(
        subject="aurora-program",
        sources=[_source(checked_at="2026-09-02T21:00:00Z")],
        items=rows,
        capabilities=_capabilities(),
        generated_at="2026-09-02T21:00:01Z",
        max_items=1,
    )
    later_clock_rows = copy.deepcopy(rows)
    for row in later_clock_rows:
        row["epistemic_view"]["currency"]["checked_at"] = "2026-09-02T22:00:00Z"
        row["epistemic_view"]["currency"]["valid_until"] = "2026-09-02T23:00:00Z"
    same_width_later_clock = assemble_world_snapshot(
        subject="aurora-program",
        sources=[_source(checked_at="2026-09-02T22:00:00Z")],
        items=later_clock_rows,
        capabilities=_capabilities(),
        generated_at="2026-09-02T22:00:01Z",
        max_items=2,
    )

    assert wide["snapshot_id"] == narrow["snapshot_id"]
    assert wide["projection_id"] == narrow["projection_id"]
    assert wide["render_id"] != narrow["render_id"]
    assert wide["render_id"] == same_width_later_clock["render_id"]


def test_render_id_includes_visible_summary_and_bounds_for_off_edge_rows():
    base = [{"id": "T001", "title": "front", "status": "blocked"}]
    expanded = base + [{"id": "T999", "title": "off edge", "status": "done"}]

    def build(tasks):
        return build_program_world_snapshot(
            ledger_path="unused.json",
            ledger_reader=lambda _path, client=None: {"seq": 1, "tasks": tasks},
            checked_at="2026-09-02T20:00:00Z",
            generated_at="2026-09-02T20:00:01Z",
            max_items=1,
        )

    narrow = build(base)
    with_hidden_row = build(expanded)

    assert [row["object_ref"] for row in narrow["items"]] == [
        row["object_ref"] for row in with_hidden_row["items"]
    ]
    assert narrow["items"][0]["data"] == with_hidden_row["items"][0]["data"]
    assert narrow["snapshot_id"] != with_hidden_row["snapshot_id"]
    assert (
        narrow["items"][0]["epistemic_view"]["authority"]["basis"]
        != with_hidden_row["items"][0]["epistemic_view"]["authority"]["basis"]
    )
    assert narrow["bounds"]["total_items"] == 1
    assert with_hidden_row["bounds"]["total_items"] == 2
    assert with_hidden_row["bounds"]["truncated"] is True
    assert narrow["summary"]["operator_sentence"] != with_hidden_row["summary"]["operator_sentence"]
    assert narrow["render_id"] != with_hidden_row["render_id"]


def test_every_item_names_authority_plane_source_and_total_epistemic_view():
    snapshot = assemble_world_snapshot(
        subject="aurora-program",
        sources=[_source()],
        items=[_item()],
        capabilities=_capabilities(),
        generated_at="2026-09-02T20:00:01Z",
    )

    source = snapshot["sources"][0]
    assert source["plane"] == "durable-ledger"
    assert source["authority"] == "governed_source"
    assert source["revision"] == "sha256:ledger-v1"
    item = snapshot["items"][0]
    assert item["source_refs"] == ["task-ledger-git"]
    assert list(item["epistemic_view"]) == [
        "authority",
        "claim_kind",
        "currency",
        "identity_state",
        "risk",
    ]
    assert item["epistemic_view"]["identity_state"]["value"] == "unknown"


def test_unknown_source_reference_fails_loud_instead_of_looking_empty():
    item = _item()
    item["source_refs"] = ["not-a-source"]

    with pytest.raises(ValueError, match="unknown source ref"):
        assemble_world_snapshot(
            subject="aurora-program",
            sources=[_source()],
            items=[item],
            capabilities=_capabilities(),
            generated_at="2026-09-02T20:00:01Z",
        )


def test_bounds_are_loud_and_attention_precedes_quiet_rows():
    snapshot = assemble_world_snapshot(
        subject="aurora-program",
        sources=[_source()],
        items=[
            _item("task:T003", attention="QUIET"),
            _item("task:T002", attention="ACTING"),
            _item("task:T001", attention="ATTENTION"),
        ],
        capabilities=_capabilities(),
        generated_at="2026-09-02T20:00:01Z",
        max_items=2,
    )

    assert [row["object_ref"] for row in snapshot["items"]] == ["task:T001", "task:T002"]
    assert snapshot["bounds"] == {
        "item_limit": 2,
        "total_items": 3,
        "returned_items": 2,
        "truncated": True,
    }
    assert "3 total" in snapshot["summary"]["operator_sentence"]
    assert "2 shown" in snapshot["summary"]["operator_sentence"]


def test_program_adapter_reads_git_ledger_plane_without_redis_or_mutation(tmp_path):
    ledger_path = tmp_path / "tasks.json"
    raw = {
        "seq": 7,
        "tasks": [
            {
                "id": "T079",
                "title": "Engine-room observability",
                "status": "in_progress",
                "owner": "sol",
                "deps": [],
                "files": [],
            }
        ],
    }
    ledger_path.write_text(json.dumps(raw), encoding="utf-8")
    before = ledger_path.read_bytes()
    calls = []

    def reader(path, client="auto"):
        calls.append((path, client))
        return json.loads(ledger_path.read_text(encoding="utf-8"))

    snapshot = build_program_world_snapshot(
        ledger_path=str(ledger_path),
        ledger_reader=reader,
        checked_at="2026-09-02T20:00:00Z",
        generated_at="2026-09-02T20:00:01Z",
    )

    assert calls == [(str(ledger_path), None)]
    assert ledger_path.read_bytes() == before
    assert snapshot["sources"][0]["plane"] == "durable-ledger"
    assert snapshot["items"][0]["data"]["arc"] == "UNCLASSIFIED"
    assert snapshot["capabilities"]["arc_membership"]["state"] == "UNCHECKABLE"
    assert snapshot["capabilities"]["mail_state"]["state"] == "UNCHECKABLE"
    assert snapshot["capabilities"]["runtime_attention"]["state"] == "UNCHECKABLE"
    assert snapshot["capabilities"]["settlement"]["blocked_by"] == "T116"
    assert "ledger projection" in snapshot["summary"]["operator_sentence"]


def test_missing_or_malformed_ledger_refuses_instead_of_looking_empty(tmp_path):
    missing = build_program_world_snapshot(
        ledger_path=str(tmp_path / "missing.json"),
        checked_at="2026-09-02T20:00:00Z",
        generated_at="2026-09-02T20:00:01Z",
    )
    corrupt_path = tmp_path / "corrupt.json"
    corrupt_path.write_text("{not-json", encoding="utf-8")
    corrupt = build_program_world_snapshot(
        ledger_path=str(corrupt_path),
        checked_at="2026-09-02T20:00:00Z",
        generated_at="2026-09-02T20:00:01Z",
    )

    for snapshot in (missing, corrupt):
        assert snapshot["items"] == []
        assert snapshot["sources"] == []
        assert snapshot["capabilities"]["task_state"]["state"] == "UNCHECKABLE"
        assert snapshot["capabilities"]["task_state"]["reason"] != "no reason recorded"
    assert "FileNotFoundError" in missing["capabilities"]["task_state"]["reason"]
    assert "JSONDecodeError" in corrupt["capabilities"]["task_state"]["reason"]


def test_adapter_programmer_error_is_not_laundered_as_an_unreadable_source(tmp_path, monkeypatch):
    ledger_path = tmp_path / "tasks.json"
    ledger_path.write_text(
        json.dumps({"seq": 1, "tasks": [{"id": "T001", "status": "in_progress"}]}),
        encoding="utf-8",
    )

    def broken_projection(_status):
        raise RuntimeError("projection bug")

    monkeypatch.setattr(world_snapshot_module, "_task_attention", broken_projection)
    with pytest.raises(RuntimeError, match="projection bug"):
        build_program_world_snapshot(ledger_path=str(ledger_path))


def test_program_rows_are_text_bounded_and_nearer_gates_sort_before_old_approvals(tmp_path):
    ledger_path = tmp_path / "tasks.json"
    huge = "a very long task title " * 500
    raw = {
        "seq": 8,
        "tasks": [
            {
                "id": "T001",
                "title": huge,
                "status": "approved",
                "owner": "",
                "deps": [],
                "files": ["x" * 500] * 40,
            },
            {
                "id": "T999",
                "title": "Awaiting verification",
                "status": "verifying",
                "owner": "peer",
                "deps": [],
                "files": [],
            },
        ],
    }
    ledger_path.write_text(json.dumps(raw), encoding="utf-8")
    snapshot = build_program_world_snapshot(
        ledger_path=str(ledger_path),
        checked_at="2026-09-02T20:00:00Z",
        generated_at="2026-09-02T20:00:01Z",
    )

    assert [row["object_ref"] for row in snapshot["items"]] == ["task:T999", "task:T001"]
    approved = snapshot["items"][1]["data"]
    assert len(approved["title"]) <= 240
    assert approved["title_truncated"] is True
    # The adapter normalizes boundary whitespace before measuring the retained
    # projection; the raw authority remains available through its drill path.
    assert approved["title_full_chars"] == len(huge.strip())
    assert len(approved["files"]) == 8
    assert approved["files_truncated"] is True


def test_task_attention_is_policy_derived_and_invalid_status_demands_attention():
    tasks = [
        {"id": "T-DONE", "status": "done"},
        {"id": "T-PARKED", "status": "parked"},
        {"id": "T-ABANDONED", "status": "abandoned"},
        {"id": "T-PROPOSED", "status": "proposed"},
        {"id": "T-MALFORMED", "status": "typo-status"},
        {"id": "T-ACTING", "status": "in_progress "},
    ]
    snapshot = build_program_world_snapshot(
        ledger_path="unused.json",
        ledger_reader=lambda _path, client=None: {"seq": 1, "tasks": tasks},
        checked_at="2026-09-02T20:00:00Z",
        generated_at="2026-09-02T20:00:01Z",
    )
    rows = {row["data"]["id"]: row for row in snapshot["items"]}

    for task_id in ("T-DONE", "T-PARKED", "T-ABANDONED", "T-PROPOSED"):
        assert rows[task_id]["attention"] == "QUIET"
    assert rows["T-ACTING"]["attention"] == "ACTING"
    assert rows["T-MALFORMED"]["attention"] == "ATTENTION"
    assert rows["T-MALFORMED"]["epistemic_view"]["risk"]["value"] == "attention_required"

    for row in rows.values():
        claim = row["epistemic_view"]["claim_kind"]
        assert claim["value"] == "inferred"
        assert {basis["ref"] for basis in claim["basis"]} == {
            "field:task.status",
            "policy:task-status-attention/v1",
        }


def test_builder_does_not_mutate_caller_inputs():
    sources = [_source()]
    items = [_item()]
    capabilities = _capabilities()
    before = copy.deepcopy((sources, items, capabilities))

    assemble_world_snapshot(
        subject="aurora-program",
        sources=sources,
        items=items,
        capabilities=capabilities,
        generated_at="2026-09-02T20:00:01Z",
    )

    assert (sources, items, capabilities) == before


def test_operational_brief_cannot_masquerade_as_an_identity_capsule():
    snapshot = assemble_world_snapshot(
        subject="aurora-program",
        sources=[_source()],
        items=[_item()],
        capabilities=_capabilities(),
        generated_at="2026-09-02T20:00:01Z",
    )

    brief = project_operational_brief(snapshot, max_items=1)

    assert brief["schema_version"] == "operational-brief/v1"
    assert brief["purpose"] == "operational_orientation"
    assert brief["identity_authority"] == "none"
    assert brief["snapshot_id"] == snapshot["snapshot_id"]
    assert brief["projection_id"] == snapshot["projection_id"]
    assert brief["source_render_id"] == snapshot["render_id"]
    assert brief["source_refs"] == ["task-ledger-git"]
    assert brief["sources"][0]["plane"] == "durable-ledger"
    assert brief["sources"][0]["authority"] == "governed_source"
    assert brief["focus"][0]["epistemic_view"] == snapshot["items"][0]["epistemic_view"]
    assert brief["capabilities"]["deduplication"]["state"] == "UNCHECKABLE"


