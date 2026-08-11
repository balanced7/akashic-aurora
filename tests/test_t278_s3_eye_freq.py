"""T278 S3: `eye freq` -- the frequency axis. HIS axis.

"A thing said once is an idea; said three times it is a standing directive" -- and the
repetition-counts note existed only because nothing measured this. S3 makes repetition a
query: a PATTERN FAMILY (phrasings OR'd, deduped by event) becomes counts, sessions, span,
per-session refs, and a MECHANICAL verdict. No LLM anywhere.

Semantics pinned here (written down so they can be argued with):
  - phrase matching is CONTIGUOUS: "fixture sword" does NOT match "fixture payrolls sword"
    (v1 of these pins modeled that wrong; the diagnostic run corrected the pins, not the code)
  - `sessions` counts OPERATOR sessions -- the axis is his repetition, echoes don't inflate it
  - verdict: 0 op events -> unheard · 1 -> mentioned-once ·
             >=3 across >=2 sessions -> standing-directive · else -> recurring

Fixture truth table (tests/fixtures/eye/):
  "fixture sword"  -> alpha:2 (agent echo), beta:1 (OPERATOR), beta:2 (agent echo)
  "fixture harvest"-> beta:4 (OPERATOR)
  "fixture progress" -> alpha:4 (queue-op = OPERATOR), alpha:6 (OPERATOR)

Run: py -m pytest tests/test_t278_s3_eye_freq.py -q
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
    dbp = tmp_path / "eye.db"
    EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=dbp)
    return dbp


def test_p1_single_phrase_counts_and_voices(db):
    r = EYE.freq(["fixture sword"], db_path=db)
    assert r["events_total"] == 3, "operator original + two agent echoes"
    assert r["operator_events"] == 1 and r["sessions"] == 1, (
        "the axis counts HIS voice and HIS sessions; agent echoes never inflate it")
    assert r["by_voice"] == {"agent": 2, "operator": 1}
    assert r["first_ts"] is not None and r["last_ts"] >= r["first_ts"]


def test_p2_family_dedupes_same_event_and_sums_distinct(db):
    # both patterns hit the SAME alpha line-1 event -> counted once
    r = EYE.freq(["fixture payrolls", "sharper every week"], db_path=db)
    assert r["events_total"] == 1 and r["operator_events"] == 1
    # distinct events across the family sum: sword(3) + harvest(1)
    r2 = EYE.freq(["fixture sword", "fixture harvest"], db_path=db)
    assert r2["events_total"] == 4 and r2["operator_events"] == 2


def test_p3_per_session_refs(db):
    r = EYE.freq(["fixture sword"], db_path=db)
    per = {s["session"]: s for s in r["per_session"]}
    assert set(per) == {"session_alpha", "session_beta"}
    assert per["session_alpha"]["events"] == 1
    assert per["session_alpha"]["operator_events"] == 0, "alpha's hit is the agent echo"
    assert per["session_beta"]["refs"][0].startswith("session_beta:")


def test_p4_queue_operation_rides_the_operator_axis(db):
    r = EYE.freq(["fixture progress"], db_path=db)
    assert r["events_total"] == 2 and r["operator_events"] == 2, (
        "the queue-operation record counts as operator speech (the law)")
    assert r["by_voice"].get("operator", 0) == 2
    assert r["events_total"] >= r["operator_events"]


def test_p5_verdicts_mechanical(db):
    assert EYE.freq(["no such phrase anywhere"], db_path=db)["verdict"] == "unheard"
    assert EYE.freq(["fixture harvest"], db_path=db)["verdict"] == "mentioned-once"
    assert EYE.freq(["fixture sword", "fixture harvest"],
                    db_path=db)["verdict"] == "recurring", (
        "2 operator events / 2 sessions -> recurring, not yet standing")


def test_p5b_standing_directive_threshold(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for f in ("session_alpha.jsonl", "session_beta.jsonl"):
        shutil.copy(FIX / f, corpus / f)
    (corpus / "session_gamma.jsonl").write_text(
        '{"type":"user","isMeta":false,"timestamp":"2026-08-03T09:00:00.000Z",'
        '"message":{"role":"user","content":"the fixture sword again, third saying"}}\n'
        '{"type":"user","isMeta":false,"timestamp":"2026-08-03T11:00:00.000Z",'
        '"message":{"role":"user","content":"and the fixture sword once more, standing now"}}\n',
        encoding="utf-8")
    dbp = tmp_path / "eye.db"
    EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=dbp)
    r = EYE.freq(["fixture sword"], db_path=dbp)
    assert r["operator_events"] == 3 and r["sessions"] == 2, "beta:1 + gamma x2"
    assert r["verdict"] == "standing-directive"
