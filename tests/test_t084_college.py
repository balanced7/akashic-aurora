"""T084 college.record.v1 RED pins: authored voice with receipts, not flattened truth.

The first Unofficial College slice is a protocol engine, not a model pipeline.  It
must keep primary-source admission, an immutable authored lecture, a different
seat's claim audit, learner teach-back, and corrections as distinct append-only
events.  Merely listing a source never upgrades it to verified evidence.
"""
from __future__ import annotations

import argparse
import asyncio
import json

import pytest


COURSE = "cpu-core-architecture-01"
LECTURER = "vandor"
AUDITOR = "sol"


def _start(root):
    from core.library.college import run_college

    return run_college(
        "start", COURSE,
        {
            "title": "CPU Core Architecture, Lecture 01",
            "topic": "How speculative out-of-order cores actually move work",
            "lecturer": LECTURER,
            "auditor": AUDITOR,
        },
        actor="daniel", root=root, now="2026-08-29T00:00:00Z",
    )


def _verify_primary(root, *, status="verified"):
    from core.library.college import run_college

    data = {
        "source_id": "intel-opt-manual",
        "title": "Intel 64 and IA-32 Architectures Optimization Reference Manual",
        "locator": "https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html",
        "source_kind": "primary",
        "status": status,
    }
    if status == "verified":
        data.update({
            "receipt": "Section 2.3 was retrieved and checked against the named mechanism.",
            "retrieved_at": "2026-08-28T23:55:00Z",
        })
    return run_college(
        "source", COURSE, data, actor=AUDITOR, root=root,
        now="2026-08-29T00:01:00Z",
    )


def _seal(root, lecture_path):
    from core.library.college import run_college

    return run_college(
        "lecture", COURSE, {"path": str(lecture_path)}, actor=LECTURER,
        root=root, now="2026-08-29T00:02:00Z",
    )


def test_a_listed_source_is_not_verification_and_cannot_unlock_the_lecture(tmp_path):
    from core.library.college import CollegeError

    _start(tmp_path)
    _verify_primary(tmp_path, status="candidate")
    lecture = tmp_path / "authored.md"
    lecture.write_text("# The lecture\n\nVoice remains mine.\n", encoding="utf-8")

    with pytest.raises(CollegeError, match="verified primary"):
        _seal(tmp_path, lecture)

    assert not (tmp_path / COURSE / "lecture.md").exists()


def test_full_chain_preserves_voice_and_keeps_errata_append_only(tmp_path):
    from core.library.college import run_college

    _start(tmp_path)
    _verify_primary(tmp_path)
    lecture = tmp_path / "authored.md"
    authored = (
        b"# A vivid authored lecture\r\n\r\n"
        b"The reorder buffer is a promise about retirement, not a bag of magic.\r\n"
    )
    lecture.write_bytes(authored)
    _seal(tmp_path, lecture)

    run_college(
        "audit", COURSE,
        {
            "claim_id": "c-retirement-order",
            "claim": "The lecture presents the reorder buffer as a retirement-order mechanism.",
            "anchor": "The reorder buffer is a promise about retirement, not a bag of magic.",
            "species": "mechanism",
            "verdict": "supported",
            "receipt": "Intel optimization manual section 2.3 names retirement order.",
            "source_ids": ["intel-opt-manual"],
            "coverage_complete": True,
            "coverage_receipt": "Auditor read the entire sealed lecture and extracted its one mechanism claim.",
        },
        actor=AUDITOR, root=tmp_path, now="2026-08-29T00:03:00Z",
    )
    run_college(
        "teachback", COURSE,
        {
            "question": "Why does speculation not imply imprecise architectural state?",
            "answer": "Because effects become architectural in retirement order.",
        },
        actor="daniel", root=tmp_path, now="2026-08-29T00:04:00Z",
    )

    events_path = tmp_path / COURSE / "events.jsonl"
    before_erratum = events_path.read_bytes()
    run_college(
        "erratum", COURSE,
        {
            "claim_id": "c-retirement-order",
            "correction": "Qualify this as the architectural model; implementations vary internally.",
            "reason": "The first wording could be read as a physical-layout claim.",
            "source_ids": ["intel-opt-manual"],
        },
        actor=LECTURER, root=tmp_path, now="2026-08-29T00:05:00Z",
    )

    result = run_college("show", COURSE, actor="daniel", root=tmp_path)

    assert result["schema"] == "college.record.v1"
    assert result["course"]["lecturer"] == LECTURER
    assert result["course"]["auditor"] == AUDITOR
    assert result["sources"][0]["status"] == "verified"
    assert result["lecture"]["sealed"] is True
    assert result["audit"][0]["species"] == "mechanism"
    assert result["audit"][0]["verdict"] == "supported"
    assert result["stages"]["audit"]["coverage_declared"] is True
    assert result["teachbacks"][0]["actor"] == "daniel"
    assert result["errata"][0]["claim_id"] == "c-retirement-order"
    assert result["integrity"] == {"event_chain": True, "lecture": True}
    assert result["gaps"] == []
    assert result["effects"] == []
    assert "does not independently verify" in " ".join(result["blind"])

    sealed = tmp_path / COURSE / "lecture.md"
    assert sealed.read_bytes() == authored, "the authored bytes are the protected voice"
    assert events_path.read_bytes().startswith(before_erratum), "errata append; history is not rewritten"


def test_wrong_seat_cannot_author_the_audit_and_self_audit_is_refused(tmp_path):
    from core.library.college import CollegeError, run_college

    with pytest.raises(CollegeError, match="must differ"):
        run_college(
            "start", "self-audit",
            {"title": "Bad split", "topic": "x", "lecturer": "same", "auditor": "same"},
            actor="same", root=tmp_path,
        )

    _start(tmp_path)
    _verify_primary(tmp_path)
    lecture = tmp_path / "lecture.md"
    lecture.write_text("A lecture.", encoding="utf-8")
    _seal(tmp_path, lecture)

    with pytest.raises(CollegeError, match="designated auditor"):
        run_college(
            "audit", COURSE,
            {
                "claim_id": "c1", "claim": "A claim", "anchor": "A lecture.",
                "species": "mechanism",
                "verdict": "supported", "receipt": "receipt",
                "source_ids": ["intel-opt-manual"],
            },
            actor=LECTURER, root=tmp_path,
        )


def test_integrity_read_detects_lecture_and_event_tampering(tmp_path):
    from core.library.college import CollegeError, run_college

    _start(tmp_path)
    _verify_primary(tmp_path)
    lecture = tmp_path / "lecture.md"
    lecture.write_text("Original voice.\n", encoding="utf-8")
    _seal(tmp_path, lecture)

    sealed = tmp_path / COURSE / "lecture.md"
    sealed.write_text("Rewritten voice.\n", encoding="utf-8")
    result = run_college("show", COURSE, root=tmp_path)
    assert result["integrity"]["lecture"] is False
    assert any("lecture hash mismatch" in gap for gap in result["gaps"])
    with pytest.raises(CollegeError, match="integrity"):
        run_college(
            "teachback", COURSE, {"question": "q", "answer": "a"},
            actor="daniel", root=tmp_path,
        )

    events_path = tmp_path / COURSE / "events.jsonl"
    rows = events_path.read_text(encoding="utf-8").splitlines()
    event = json.loads(rows[1])
    event["payload"]["title"] = "silently changed source title"
    rows[1] = json.dumps(event, sort_keys=True)
    events_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    result = run_college("show", COURSE, root=tmp_path)
    assert result["integrity"]["event_chain"] is False
    assert any("event chain" in gap for gap in result["gaps"])


def test_same_hash_lecture_retry_repairs_both_partial_write_windows(tmp_path):
    """The two-file seal cannot be one filesystem transaction, so exact replay is recovery."""
    from core.library.college import run_college

    _start(tmp_path)
    _verify_primary(tmp_path)
    source = tmp_path / "authored.md"
    source.write_bytes(b"Exact authored bytes.\r\n")
    sealed = tmp_path / COURSE / "lecture.md"

    # Window A: bytes landed, process died before lecture.sealed was appended.
    sealed.write_bytes(source.read_bytes())
    recovered = _seal(tmp_path, source)
    assert recovered["lecture"]["sealed"] is True
    assert recovered["integrity"]["lecture"] is True
    event_count = recovered["bounds"]["events"]

    # Window B: event landed, projection disappeared before the caller observed success.
    sealed.unlink()
    restored = _seal(tmp_path, source)
    assert sealed.read_bytes() == source.read_bytes()
    assert restored["bounds"]["events"] == event_count, "repair does not mint a second seal"
    assert restored["effects"] == [{"kind": "create", "path": str(sealed)}]


def test_lecture_path_cannot_escape_its_root_or_copy_a_secret(tmp_path):
    from core.library.college import CollegeError

    _start(tmp_path)
    _verify_primary(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside.write_text("outside", encoding="utf-8")
    with pytest.raises(CollegeError, match="outside the allowed root"):
        _seal(tmp_path, outside)

    secret = tmp_path / ".secrets" / "lecture.md"
    secret.parent.mkdir()
    secret.write_text("secret", encoding="utf-8")
    with pytest.raises(CollegeError, match="secret"):
        _seal(tmp_path, secret)


def test_audit_rosters_refuse_untyped_or_unreceipted_certainty(tmp_path):
    from core.library.college import CollegeError, run_college

    _start(tmp_path)
    _verify_primary(tmp_path)
    lecture = tmp_path / "lecture.md"
    lecture.write_text("A lecture.", encoding="utf-8")
    _seal(tmp_path, lecture)

    base = {
        "claim_id": "c1", "claim": "Claim", "anchor": "A lecture.",
        "verdict": "supported",
        "receipt": "Checked", "source_ids": ["intel-opt-manual"],
    }
    with pytest.raises(CollegeError, match="species"):
        run_college("audit", COURSE, {**base, "species": "fact"}, actor=AUDITOR, root=tmp_path)
    with pytest.raises(CollegeError, match="receipt"):
        run_college(
            "audit", COURSE, {**base, "species": "measurement", "receipt": ""},
            actor=AUDITOR, root=tmp_path,
        )
    with pytest.raises(CollegeError, match="anchor"):
        run_college(
            "audit", COURSE, {**base, "species": "measurement", "anchor": "not in the lecture"},
            actor=AUDITOR, root=tmp_path,
        )

    incomplete = run_college(
        "audit", COURSE, {**base, "species": "measurement"},
        actor=AUDITOR, root=tmp_path,
    )
    assert incomplete["stages"]["audit"]["coverage_declared"] is False
    assert any("coverage" in gap for gap in incomplete["gaps"])


def test_show_is_a_pure_read(tmp_path):
    from core.library.college import run_college

    _start(tmp_path)
    events = tmp_path / COURSE / "events.jsonl"
    before = (events.stat().st_mtime_ns, events.read_bytes())
    before_files = sorted(p.name for p in (tmp_path / COURSE).iterdir())
    result = run_college("show", COURSE, root=tmp_path)
    after = (events.stat().st_mtime_ns, events.read_bytes())
    after_files = sorted(p.name for p in (tmp_path / COURSE).iterdir())

    assert before == after
    assert before_files == after_files, "show does not create even bookkeeping files"
    assert result["effects"] == []


def test_cli_mcp_and_toolbox_share_one_provider(monkeypatch, tmp_path):
    import agent_cli
    from core.comm.toolbox import TOOLS, ToolBox
    from core.library import college as college_module
    from scripts.checkers import check_door_parity

    calls = []

    def fixture(action, course, data=None, *, actor="", root=None, now=None):
        calls.append({"action": action, "course": course, "data": data or {}, "actor": actor})
        return {
            "schema": "college.record.v1", "action": action, "course": {"id": course},
            "effects": [], "blind": [], "gaps": [], "integrity": {},
        }

    monkeypatch.setattr(college_module, "run_college", fixture)

    parser = agent_cli.build_parser()
    parsed = parser.parse_args(["college", "show", COURSE, "--actor", "daniel", "--json"])
    assert parsed.college_action == "show"
    assert parsed.course == COURSE
    assert parsed.fn is agent_cli.cmd_college
    rendered = []
    monkeypatch.setattr(agent_cli, "print", lambda value, *a, **k: rendered.append(str(value)),
                        raising=False)
    assert agent_cli.cmd_college(parsed) == 0
    assert json.loads(rendered[-1])["schema"] == "college.record.v1"

    # Import only after the ordinary CLI assertion. ai_setup_mcp installs a
    # process-wide stdout membrane by design; importing it under capsys would
    # let an MCP helper cache a fixture-owned stream and contaminate later tests.
    import ai_setup_mcp
    raw = asyncio.run(ai_setup_mcp.college(
        agent="daniel", action="show", course=COURSE, data={}
    ))
    assert json.loads(raw)["schema"] == "college.record.v1"
    assert "\n" not in raw, "model-facing MCP JSON stays compact"

    advertised = {row["function"]["name"] for row in TOOLS}
    assert "college" in advertised
    assert check_door_parity.MANIFEST["college"] == "shared"

    tb = ToolBox(
        tmp_path, allow_exec=False, trust=False, allow_secrets=False,
        confirm=lambda *_: False, agent_id="daniel",
    )
    monkeypatch.setattr(tb, "_agent_cli", lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("college must use the native provider, not shell through agent_cli")
    ))
    tb_raw = tb.college("show", COURSE, {})
    assert json.loads(tb_raw)["schema"] == "college.record.v1"
    assert "\n" not in tb_raw, "model-facing ToolBox JSON stays compact"
    assert [call["actor"] for call in calls] == ["daniel", "daniel", "daniel"]
