"""T278 S5: `eye stats` + `eye overview` -- the did-anything-shift senses, numbers first.

Fence r1 C3 split one mixed-modal verb into two: stats = crisp numerics (counts by voice
and kind, sessions, the TIME-FOG fraction -- events whose ts could not be parsed and are
therefore invisible to every as_of query), overview = structure (sessions with counts and
spans). Numbers before prose; fog stated, never hidden (the degraded law made ambient).

Run: py -m pytest tests/test_t278_s5_eye_stats.py -q
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
    (corpus / "session_gamma.jsonl").write_text(
        '{"type":"user","isMeta":false,"timestamp":"not-a-real-time",'
        '"message":{"role":"user","content":"timeless gamma utterance"}}\n',
        encoding="utf-8")
    dbp = tmp_path / "eye.db"
    EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=dbp)
    return dbp


def test_p1_stats_counts_match_fixture_truth(db):
    s = EYE.stats(db_path=db)
    # Recounted AGAINST THE DIAGNOSTIC (second time this build run the pin-math was wrong
    # and the code right -- the fixture-mental-model failure mode; diagnose before patching):
    # alpha 7 = op3 (line1, queue-op line4, line6) + agent1 + system3 (caveat, meta, tasknotif)
    # beta 4 = op2 + agent1 + system1 · gamma 1 = op (timeless)
    assert s["events_total"] == 12
    assert s["sessions"] == 3
    assert s["by_voice"]["operator"] == 6 and s["by_voice"]["agent"] == 2
    assert s["by_voice"]["system"] == 4
    assert s["by_kind"]["queue-operation"] == 2


def test_p2_time_fog_is_a_number(db):
    s = EYE.stats(db_path=db)
    assert s["ts_missing"] == 1, "the timeless gamma event"
    assert 0 < s["time_fog"] < 0.15 and abs(s["time_fog"] - 1 / 12) < 1e-9, (
        "fog is a FRACTION, stated -- every as_of query is blind to exactly this share")


def test_p3_overview_lists_sessions_with_spans(db):
    o = EYE.overview(db_path=db)
    per = {s["session"]: s for s in o["sessions"]}
    assert set(per) == {"session_alpha", "session_beta", "session_gamma"}
    assert per["session_alpha"]["events"] == 7
    assert per["session_alpha"]["first_ts"] is not None
    assert per["session_gamma"]["first_ts"] is None, (
        "a session with only timeless events has no span -- shown as such, not faked")
    assert per["session_alpha"]["operator_events"] == 3
