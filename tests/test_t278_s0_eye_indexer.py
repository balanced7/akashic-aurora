"""T278 S0: THE EYE's indexer -- the corpus layer, with the coverage contract built in.

The organ exists because two directives died in the transcript plane; the indexer is the
first mechanism that makes that plane terrain. S0's laws, from the fenced design (atom
the-eye-design-v2_208b26):

  - operator speech lives in `user` turns AND `queue-operation` records
    (lesson operator_speech_hides_in_queue_operation_records) -- both ingest.
  - VOICE is labeled conservatively: operator | agent | system. A command-caveat block or
    meta line inside a user record is SYSTEM, never operator -- the false-positive class the
    success-vocabulary sweep paid for (task-notification blocks polluting the pack).
  - every event is ADDRESSABLE: event_id = session:line, resolving back to the verbatim
    record (the grammar's address space; T288's resolver substrate).
  - THE COVERAGE PIN (design pin 7): the indexer over a manifest with one unreadable file
    REPORTS the gap -- files_failed named, manifest_complete False. A clipped index cannot
    claim wholeness (the laundering law, built into the organ born from it).
  - incremental: a re-run ingests only appended lines (mtime+line cursor per file).

Fixtures are SYNTHETIC (tests/fixtures/eye/) -- pins never read the live corpus.

Run: py -m pytest tests/test_t278_s0_eye_indexer.py -q
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.eye import index as EYE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "eye"


def _fresh(tmp_path, files=("session_alpha.jsonl", "session_beta.jsonl")):
    """Copy fixtures into tmp (pins never mutate the originals) + a fresh db path."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for f in files:
        shutil.copy(FIX / f, corpus / f)
    return corpus, tmp_path / "eye.db"


def test_p1_manifest_matches_indexed(tmp_path):
    corpus, db = _fresh(tmp_path)
    rep = EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=db)
    assert rep["files_seen"] == 2 and rep["files_indexed"] == 2
    assert rep["files_failed"] == []
    assert rep["manifest_complete"] is True
    # alpha: 6 lines -> user(op) + assistant + user(system caveat) + queue-op + meta(system)
    #        + user(op, block content); beta: user + assistant + system + user
    assert rep["events_total"] == 10, "every parseable record lands as exactly one event"


def test_p2_queue_operation_is_operator_speech(tmp_path):
    corpus, db = _fresh(tmp_path)
    EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=db)
    hits = EYE.find_text("queued directive", db_path=db)
    assert hits, "the queue-operation record must be findable (the operator-speech law)"
    assert hits[0]["voice"] == "operator"
    assert hits[0]["type"] == "queue-operation"


def test_p3_incremental_ingests_only_the_appended_line(tmp_path):
    corpus, db = _fresh(tmp_path)
    r1 = EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=db)
    r2 = EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=db)
    assert r2["events_new"] == 0, "unchanged files re-ingest nothing"
    with open(corpus / "session_beta.jsonl", "a", encoding="utf-8") as f:
        f.write('{"type":"user","isMeta":false,"timestamp":"2026-08-02T10:00:00.000Z",'
                '"message":{"role":"user","content":"appended fixture line about the sword"}}\n')
    r3 = EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=db)
    assert r3["events_new"] == 1, "only the appended line ingests"
    assert r3["events_total"] == r1["events_total"] + 1


def test_p4_coverage_names_the_gap(tmp_path):
    corpus, db = _fresh(tmp_path)
    ghost = corpus / "session_ghost.jsonl"          # named in the manifest, not on disk
    rep = EYE.ingest(paths=sorted(corpus.glob("*.jsonl")) + [ghost], db_path=db)
    assert rep["manifest_complete"] is False, (
        "P4 THE COVERAGE PIN: one unreadable file and the index may not claim wholeness")
    assert any("session_ghost" in f["path"] for f in rep["files_failed"]), (
        "the gap is NAMED, never a bare count")
    assert rep["files_indexed"] == 2


def test_p5_event_id_resolves_to_verbatim(tmp_path):
    corpus, db = _fresh(tmp_path)
    EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=db)
    hits = EYE.find_text("measure fixture progress", db_path=db)
    assert hits and hits[0]["session"] == "session_alpha"
    ev = EYE.get_event(hits[0]["event_id"], db_path=db)
    assert ev is not None, "the address must resolve (grammar address space; T288 resolver)"
    assert "measure fixture progress" in ev["text"]
    assert ev["event_id"] == f"session_alpha:{ev['line']}"


def test_p6_voice_labels_are_conservative(tmp_path):
    corpus, db = _fresh(tmp_path)
    EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=db)
    caveat = EYE.find_text("command-name", db_path=db)
    assert caveat and caveat[0]["voice"] == "system", (
        "a command-caveat block inside a user record is SYSTEM -- the false-positive class "
        "the sweep paid for")
    meta = EYE.find_text("meta housekeeping", db_path=db)
    assert meta and meta[0]["voice"] == "system", "isMeta user records are never operator"
    real = EYE.find_text("sharper every week", db_path=db)
    assert real and real[0]["voice"] == "operator"
    agent = EYE.find_text("Beta acknowledges", db_path=db)
    assert agent and agent[0]["voice"] == "agent"
