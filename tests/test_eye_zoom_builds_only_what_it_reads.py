"""Pins for `eye zoom` on a large index: it builds the session it is asked for, not the corpus.

Measured on the live index 2026-10-24: 116,062 events across 17,562 sessions, and no index on
events.session. The first zoom called pyramid.build(), which read each session with a full
scan of `events` -- about two billion row reads, committed only at the end. A caller's timeout
killed it before the commit, so the pyramid stayed empty and the next zoom started over: zoom
never returned. Once some pyramid did exist, the CLI never built again, so every session
ingested after that build refused with "no pyramid node".

  P1 a per-session read of `events` uses an index, never a scan of the whole table
  P2 zoom on a fresh index builds only the session it reads
  P3 a session ingested after a pyramid exists still zooms
  P4 an unknown session still refuses, and leaves no node behind

Run: uv run pytest tests/test_eye_zoom_builds_only_what_it_reads.py -q
"""

import shutil
import sqlite3
from pathlib import Path

import pytest

import agent_cli
from core.eye import index as EYE
from core.eye import pyramid as PYR

FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "eye"


@pytest.fixture
def eye_db(tmp_path, monkeypatch):
    db = tmp_path / "eye.db"
    monkeypatch.setattr(EYE, "_DEFAULT_DB", db)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return db


def _ingest(db, tmp_path, *names):
    corpus = tmp_path / "corpus"
    corpus.mkdir(exist_ok=True)
    for name in names:
        shutil.copy(FIX / f"{name}.jsonl", corpus / f"{name}.jsonl")
    EYE.ingest(paths=[corpus / f"{n}.jsonl" for n in names], db_path=db)


def _run(capsys, *argv):
    args = agent_cli.build_parser().parse_args(["eye", *argv])
    code = args.fn(args)
    return code, capsys.readouterr()


def _sessions_with_nodes(db):
    con = sqlite3.connect(str(db))
    try:
        return {r[0] for r in con.execute("SELECT DISTINCT session FROM pyramid")}
    finally:
        con.close()


def test_p1_a_per_session_read_uses_an_index(eye_db, tmp_path):
    _ingest(eye_db, tmp_path, "session_alpha")
    con = EYE._connect(eye_db)
    try:
        plan = " ".join(
            str(r[-1])
            for r in con.execute(
                "EXPLAIN QUERY PLAN SELECT event_id, voice, text, tokens FROM events WHERE session=? ORDER BY line",
                ("session_alpha",),
            )
        )
    finally:
        con.close()
    assert "USING INDEX" in plan, f"a per-session read scans every event in the index: {plan}"


def test_p2_zoom_on_a_fresh_index_builds_only_that_session(eye_db, tmp_path, capsys):
    _ingest(eye_db, tmp_path, "session_alpha", "session_beta")
    code, _ = _run(capsys, "zoom", "session_alpha")
    assert code == 0
    assert _sessions_with_nodes(eye_db) == {"session_alpha"}, "zoom built sessions nobody asked for"


def test_p3_a_session_ingested_after_a_build_still_zooms(eye_db, tmp_path, capsys):
    _ingest(eye_db, tmp_path, "session_alpha")
    PYR.build(db_path=eye_db)
    _ingest(eye_db, tmp_path, "session_beta")
    code, out = _run(capsys, "zoom", "session_beta")
    assert code == 0, f"a session newer than the pyramid refused: {out.out}{out.err}"
    assert "session_beta/L2" in out.out


def test_p4_an_unknown_session_refuses_and_leaves_no_node(eye_db, tmp_path, capsys):
    _ingest(eye_db, tmp_path, "session_alpha")
    code, _ = _run(capsys, "zoom", "no_such_session")
    assert code != 0
    assert "no_such_session" not in _sessions_with_nodes(eye_db)
