"""T278 S2: the pyramid -- LOD as regenerable projection, fidelity by construction.

The fence's hardest ruling (r1 C2/C5): "a stale summary is honest fog; a LYING summary is
invisible poison." S2's answer is structural: summaries are EXTRACTIVE-ONLY -- every word
of L1/L2 text is drawn from events the node's refs anchor, refs are extracted mechanically,
and NO LLM exists in the path. Fidelity is not checked after the fact; it is impossible to
violate by construction. (When an abstractive layer ever lands, the fidelity pin here
becomes its acceptance gate.)

Levels: L1 = exchange (one operator turn + the replies until the next operator turn),
L2 = session digest. Both carry refs (event_ids), built_at, and tokens; reads surface
is_stale when events newer than built_at exist (stale = fog, never silence).

Pins:
  P1 THE FIDELITY PIN: every ref on every node resolves; every task-id mentioned in node
     text appears verbatim in a referenced event (the extractive guarantee, exhaustive
     over fixtures)
  P2 THE LOD PIN: a session's L2 digest costs <5% of its L0 tokens (long synthetic session)
  P3 descent: L2 -> child L1 ids -> event refs, ordering stable
  P4 staleness: appended events flip is_stale on existing nodes; rebuild clears it
  P5b harness double-record (queue-op + user, identical) is ONE exchange, deduped in digest
  P5 exchange grouping: every exchange opens with the operator's voice

Run: py -m pytest tests/test_t278_s2_eye_pyramid.py -q
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.eye import index as EYE  # noqa: E402
from core.eye import pyramid as PYR  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "eye"


@pytest.fixture()
def db(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for f in ("session_alpha.jsonl", "session_beta.jsonl"):
        shutil.copy(FIX / f, corpus / f)
    dbp = tmp_path / "eye.db"
    EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=dbp)
    return dbp


def test_p1_the_fidelity_pin(db):
    PYR.build(db_path=db)
    nodes = PYR.nodes(db_path=db)
    assert nodes, "the build produced nodes"
    for n in nodes:
        assert n["refs"], f"{n['node_id']}: a node with no refs anchors nothing"
        for ref in n["refs"]:
            ev = EYE.get_event(ref, db_path=db)
            assert ev is not None, f"{n['node_id']}: ref {ref} does not resolve"
        anchored = " ".join((EYE.get_event(r, db_path=db) or {}).get("text", "")
                            for r in n["refs"])
        for tid in re.findall(r"\bT\d{3}\b", n["text"]):
            assert tid in anchored, (
                f"{n['node_id']}: mentions {tid} which no referenced event contains -- "
                "the extractive guarantee is broken (the lying-summary poison)")


def test_p2_the_lod_pin(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    lines = []
    for i in range(120):
        who_line = (
            '{"type":"user","isMeta":false,"timestamp":"2026-08-0%dT%02d:%02d:00.000Z",'
            '"message":{"role":"user","content":"operator turn %d: a reasonably long '
            'utterance about the synthetic corpus, padded with enough words that level '
            'zero carries real weight for the ratio test %s"}}'
            % (1 + (i // 60), (i % 24), (i * 7) % 60, i, "filler " * 30))
        agent_line = (
            '{"type":"assistant","timestamp":"2026-08-0%dT%02d:%02d:30.000Z",'
            '"message":{"role":"assistant","content":[{"type":"text","text":"agent reply '
            '%d with its own long body %s"}]}}'
            % (1 + (i // 60), (i % 24), (i * 7) % 60, i, "response " * 40))
        lines += [who_line, agent_line]
    (corpus / "session_long.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    dbp = tmp_path / "eye.db"
    EYE.ingest(paths=[corpus / "session_long.jsonl"], db_path=dbp)
    PYR.build(db_path=dbp)
    dig = PYR.zoom("session_long", db_path=dbp)
    l0_tokens = EYE.stats(db_path=dbp)["events_total"] and sum(
        e["tokens"] for e in
        EYE.find(session="session_long", limit=10_000, db_path=dbp)["results"])
    assert dig["level"] == "L2" and dig["tokens"] > 0
    assert dig["tokens"] < 0.05 * l0_tokens, (
        f"THE LOD PIN: L2 at {dig['tokens']} tok vs L0 {l0_tokens} -- viewing a session "
        "must cost <5% of reading it")


def test_p3_descent_is_citation_following(db):
    PYR.build(db_path=db)
    l2 = PYR.zoom("session_alpha", db_path=db)
    assert l2["level"] == "L2" and l2["children"], "L2 lists its L1 children"
    l1 = PYR.zoom(l2["children"][0], db_path=db)
    assert l1["level"] == "L1" and l1["refs"]
    ev = EYE.get_event(l1["refs"][0], db_path=db)
    assert ev is not None, "descent bottoms out at verbatim L0"
    assert l2["children"] == sorted(l2["children"]), "child ordering is stable"


def test_p4_staleness_is_fog_not_silence(db, tmp_path):
    PYR.build(db_path=db)
    fresh = PYR.zoom("session_alpha", db_path=db)
    assert fresh["is_stale"] is False
    # append an event directly (the indexer would normally do this)
    import sqlite3
    con = sqlite3.connect(str(db))
    con.execute("INSERT INTO events(event_id, session, line, ts, voice, type, text, cwd, "
                "branch, tokens) VALUES('session_alpha:99','session_alpha',99,"
                "9999999999,'operator','user','late arrival','','',3)")
    con.commit(); con.close()
    stale = PYR.zoom("session_alpha", db_path=db)
    assert stale["is_stale"] is True, (
        "events newer than built_at MUST surface as staleness -- fog, never silence")
    PYR.build(db_path=db)
    assert PYR.zoom("session_alpha", db_path=db)["is_stale"] is False


def test_p5b_harness_double_record_is_one_exchange(tmp_path):
    """The live-caught defect: the harness records one operator turn TWICE (queue-op enqueue
    + user record, identical text). Consecutive operator events with no agent between them
    are ONE exchange, and the digest must not repeat the utterance."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    rec = [
        {"type": "queue-operation", "timestamp": "2026-08-01T10:00:00.000Z",
         "prompt": "the very same operator utterance about the sword"},
        {"type": "user", "isMeta": False, "timestamp": "2026-08-01T10:00:01.000Z",
         "message": {"role": "user",
                     "content": "the very same operator utterance about the sword"}},
        {"type": "assistant", "timestamp": "2026-08-01T10:00:05.000Z",
         "message": {"role": "assistant",
                     "content": [{"type": "text", "text": "one reply"}]}},
        {"type": "user", "isMeta": False, "timestamp": "2026-08-01T10:01:00.000Z",
         "message": {"role": "user",
                     "content": "a genuinely second operator turn later"}},
    ]
    (corpus / "session_dup.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rec) + "\n", encoding="utf-8")
    dbp = tmp_path / "eye.db"
    EYE.ingest(paths=[corpus / "session_dup.jsonl"], db_path=dbp)
    PYR.build(db_path=dbp)
    l2 = PYR.zoom("session_dup", db_path=dbp)
    assert len(l2["children"]) == 2, (
        "two exchanges: the doubled first turn is ONE, the later turn is the second")
    assert l2["text"].lower().count("the very same operator utterance") == 1, (
        "the digest must not repeat the doubled utterance")


def test_p5_exchanges_start_at_operator_turns(db):
    PYR.build(db_path=db)
    l2 = PYR.zoom("session_alpha", db_path=db)
    firsts = []
    for child in l2["children"]:
        l1 = PYR.zoom(child, db_path=db)
        first_ev = EYE.get_event(l1["refs"][0], db_path=db)
        firsts.append(first_ev["voice"])
    assert all(v == "operator" for v in firsts), (
        "every exchange opens with an operator turn -- the grouping law")
