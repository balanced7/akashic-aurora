"""T361 acceptance pins — the citation resolver speaks the house dialect
(RED committed alone, M3).

RECEIPT 2026-08-17: Navi cited `51589003:415` — sid8, the same dialect boot,
roster, and every handoff print — and `eye get` answered "no event at
'51589003:415'". The citations were exact; the verdict read as fabrication.
An address the resolver cannot parse must never render as an absence claim
about the EVENT (T176 at a door; T340's silent-wrong-answer class).

The contract under pin:
  P1  a UNIQUE short session prefix resolves to the event.
  P2  an AMBIGUOUS prefix refuses loudly, naming every candidate session —
      a third outcome, distinct from found and from absent.
  P3  a full exact address still resolves (no regression).
  P4  a truly absent address still returns None — honest absence preserved.
  P5  a prefix-resolved record carries the FULL session id, so resolution
      teaches the canonical form instead of hiding it.

Run:  py -m pytest tests/test_t361_eye_get_prefix_pins.py -v
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.eye import index as eye  # noqa: E402

SESS_A = "feed0001-1111-4111-8111-111111111111"   # shares sid8 with B -> ambiguous
SESS_B = "feed0001-2222-4222-8222-222222222222"
SESS_C = "cafe0002-3333-4333-8333-333333333333"   # unique at sid8


@pytest.fixture()
def db(tmp_path):
    p = tmp_path / "eye.db"
    con = eye._connect(p)
    try:
        for sess, text in ((SESS_A, "alpha utterance"), (SESS_B, "bravo utterance"),
                           (SESS_C, "charlie utterance")):
            con.execute(
                "INSERT INTO events(event_id, session, line, ts, voice, type, text) "
                "VALUES (?,?,?,?,?,?,?)",
                (f"{sess}:1", sess, 1, 1.0, "operator", "user", text))
        con.commit()
    finally:
        con.close()
    return p


def test_p1_unique_prefix_resolves(db):
    ev = eye.get_event("cafe0002:1", db_path=db)
    assert ev is not None, (
        "a UNIQUE sid8 prefix must resolve — this exact miss is how a correct "
        "citation in the house's own dialect read as 'no event' (receipt "
        "2026-08-17, Navi's 51589003:415)")
    assert ev["text"] == "charlie utterance"


def test_p2_ambiguous_prefix_refuses_naming_candidates(db):
    with pytest.raises(ValueError) as exc:
        eye.get_event("feed0001:1", db_path=db)
    msg = str(exc.value)
    assert SESS_A in msg and SESS_B in msg, (
        "ambiguity must refuse LOUDLY with every candidate named — a None here "
        "would render 'two matches' as 'no event', the same lie one branch over")


def test_p3_full_address_still_resolves(db):
    ev = eye.get_event(f"{SESS_A}:1", db_path=db)
    assert ev is not None and ev["text"] == "alpha utterance"


def test_p4_true_absence_is_still_none(db):
    assert eye.get_event("deadbeef:1", db_path=db) is None, (
        "a prefix matching NOTHING is a real absence — the fix must not turn "
        "honest no-event into an error")


def test_p5_resolution_teaches_the_canonical_form(db):
    ev = eye.get_event("cafe0002:1", db_path=db)
    assert ev is not None and ev["session"] == SESS_C, (
        "the resolved record must carry the FULL session id so the caller "
        "learns the canonical address")
