"""T278 S1: `eye find` speaks the query grammar (T280) -- THE EYE as its first tenant.

The grammar's own RED pins (docs/query-grammar-2026-08.md §6), run against this door:

  - THE AS-OF PIN (the -898k class, transcript form): an event recorded after date D is
    INVISIBLE to `as_of=D`; visible without it. known_at <= as_of, the one-sentence law.
  - THE SILENT-EMPTY PIN: a malformed as_of REFUSES with the expected shape (ValueError
    with teaching text at the library; exit 2 at the CLI). Zero rows is never the answer
    to a malformed selector.
  - THE FACET PIN: who= and kind= and q= compose (AND); each alone changes the result set;
    q alone still works (S0 compatibility).
  - THE DEGRADED PIN (the formation-trap pattern, applied to time): events whose ts could
    not be parsed are UNEVALUABLE under as_of -- they are excluded AND the envelope says so
    (degraded: true, reason names the count). Absence of a warning means exactly one thing.

Envelope contract: {results, total, degraded, degraded_reason, tokens_returned, as_of}.

Run: py -m pytest tests/test_t278_s1_eye_grammar.py -q
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


@pytest.fixture()
def db(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for f in ("session_alpha.jsonl", "session_beta.jsonl"):
        shutil.copy(FIX / f, corpus / f)
    # gamma: one event on 08-03 and one with an UNPARSEABLE timestamp
    (corpus / "session_gamma.jsonl").write_text(
        '{"type":"user","isMeta":false,"timestamp":"2026-08-03T09:00:00.000Z",'
        '"message":{"role":"user","content":"gamma fixture sword late saying"}}\n'
        '{"type":"user","isMeta":false,"timestamp":"not-a-real-time",'
        '"message":{"role":"user","content":"timeless fixture sword utterance"}}\n',
        encoding="utf-8")
    dbp = tmp_path / "eye.db"
    EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=dbp)
    return dbp


def test_p1_as_of_hides_later_events(db):
    # without as_of: alpha (08-01) + beta (08-02) + gamma (08-03) operator "fixture sword"
    # family events all visible
    env_all = EYE.find(q="fixture sword", db_path=db)
    ids_all = {r["event_id"] for r in env_all["results"]}
    assert any(i.startswith("session_gamma") for i in ids_all)

    env_d = EYE.find(q="fixture sword", as_of="2026-08-02", db_path=db)
    ids_d = {r["event_id"] for r in env_d["results"]}
    assert not any(i.startswith("session_gamma:1") for i in ids_d), (
        "THE AS-OF PIN: an event recorded 08-03 is invisible to as_of=08-02")
    assert any(i.startswith("session_alpha") for i in ids_d), (
        "earlier events stay visible under as_of")
    assert env_d["as_of"] is not None


def test_p2_malformed_as_of_refuses_with_teaching(db):
    with pytest.raises(ValueError) as e:
        EYE.find(q="fixture", as_of="2026-13-01", db_path=db)
    msg = str(e.value)
    assert "as_of" in msg and ("ISO" in msg or "YYYY-MM-DD" in msg), (
        "THE SILENT-EMPTY PIN: the refusal teaches the expected shape")
    with pytest.raises(ValueError):
        EYE.find(q="fixture", as_of="not-a-date", db_path=db)


def test_p3_facets_compose(db):
    base = EYE.find(q="fixture", db_path=db, limit=100)
    who = EYE.find(q="fixture", who="operator", db_path=db, limit=100)
    kind = EYE.find(q="fixture", who="operator", kind="queue-operation",
                    db_path=db, limit=100)
    assert base["total"] > who["total"] > kind["total"] >= 1, (
        "THE FACET PIN: each facet narrows -- AND composition")
    assert all(r["voice"] == "operator" for r in who["results"])
    assert all(r["type"] == "queue-operation" for r in kind["results"])
    sess = EYE.find(q="fixture", session="session_beta", db_path=db, limit=100)
    assert all(r["session"] == "session_beta" for r in sess["results"])


def test_p4_unevaluable_ts_degrades_the_envelope(db):
    env = EYE.find(q="fixture sword", as_of="2026-08-02", db_path=db)
    assert env["degraded"] is True, (
        "THE DEGRADED PIN: a ts-less matching event cannot be evaluated under as_of; "
        "silence would read as completeness")
    assert "timestamp" in (env["degraded_reason"] or "")
    env2 = EYE.find(q="fixture sword", db_path=db)
    assert env2["degraded"] is False, (
        "no as_of -> ts-less events are ordinary results, nothing degraded")


def test_p5_q_alone_still_works_and_s0_wrapper_intact(db):
    env = EYE.find(q="queued directive", db_path=db)
    assert env["total"] == 1 and env["results"][0]["type"] == "queue-operation"
    assert not hasattr(EYE, "find_text"), (
        "one door, no fork: the S0 wrapper was DELETED when production moved to find() -- "
        "a superseded function left callable is a live fork (the lesson, applied)")


def test_p6_envelope_carries_budget(db):
    env = EYE.find(q="fixture", db_path=db, limit=3)
    assert len(env["results"]) <= 3
    assert env["total"] >= len(env["results"]), "total counts before the limit"
    assert env["tokens_returned"] > 0, (
        "the envelope prices itself -- context-efficiency is a visible number (category B)")
