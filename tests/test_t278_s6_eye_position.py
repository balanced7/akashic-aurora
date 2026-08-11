"""T278 S6: position -- the inhabitant loop closes.

The charter asked how an AI INHABITS this system. An inhabitant has a POSITION: it wakes
where it left off and is told what changed while it slept. That is the last thing the
sensorium is missing -- S0-S5 gave it senses, and senses without a standpoint are a search
engine, not a world.

THE LOAD-BEARING RULE (design atom the-eye-design-v2_208b26, fence r1 C4): position is
keyed PER INCARNATION (agent#sid8), never per base agent. Two live sessions of the same
agent sharing one cursor clobber each other and poison `since=` -- each would report the
other's movement as its own elapsed change. This is the T272 identity law applied to a new
plane, and the fleet has paid for the general version of it more than once (the seat cursor,
the runner lock, the lane cursor).

Succession INHERITS explicitly: a fresh incarnation does not silently adopt a predecessor's
standpoint, because a position adopted without saying so is indistinguishable from one you
walked to yourself, and the whole point of `since=` is knowing which interval is yours.

Fixture: session_gamma / session_delta / session_epsilon (see the S4 pins for their shape).

Run: py -m pytest tests/test_t278_s6_eye_position.py -q
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.eye import connectome as CONN  # noqa: E402
from core.eye import index as EYE  # noqa: E402
from core.eye import position as POS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "eye"

G = "session_gamma"
D = "session_delta"


@pytest.fixture()
def db(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for f in ("session_gamma.jsonl", "session_delta.jsonl"):
        shutil.copy(FIX / f, corpus / f)
    dbp = tmp_path / "eye.db"
    EYE.ingest(paths=sorted(corpus.glob("*.jsonl")), db_path=dbp)
    CONN.build(db_path=dbp)
    return dbp


# ---------------------------------------------------------------- P1: the clobber pin
def test_p1_two_incarnations_hold_independent_positions(db):
    """Fence r1 C4, the reason this is keyed the way it is. Two live seats of ONE agent
    move independently; neither read disturbs the other."""
    POS.go("claude#aaaaaaaa", f"{G}:1", db_path=db)
    POS.go("claude#bbbbbbbb", f"{D}:1", db_path=db)

    assert POS.where("claude#aaaaaaaa", db_path=db)["addr"] == f"{G}:1"
    assert POS.where("claude#bbbbbbbb", db_path=db)["addr"] == f"{D}:1"

    POS.go("claude#aaaaaaaa", f"{G}:6", db_path=db)
    assert POS.where("claude#bbbbbbbb", db_path=db)["addr"] == f"{D}:1", (
        "one seat moving must not drag its twin -- this is the whole pin")


def test_p1b_a_virgin_seat_has_no_position_and_says_so(db):
    """Absent is not the same as 'at the root'. A fabricated default standpoint would make
    `since=` report someone else's interval as yours."""
    assert POS.where("claude#cccccccc", db_path=db) is None


# ---------------------------------------------------------------- P2: it survives
def test_p2_position_persists_across_reads(db):
    POS.go("claude#aaaaaaaa", f"{G}:5", db_path=db)
    for _ in range(3):
        assert POS.where("claude#aaaaaaaa", db_path=db)["addr"] == f"{G}:5"


# ---------------------------------------------------------------- P3: the trail
def test_p3_go_pushes_a_trail_and_back_pops_it(db):
    POS.go("claude#aaaaaaaa", f"{G}:1", db_path=db)
    POS.go("claude#aaaaaaaa", f"{G}:5", db_path=db)
    POS.go("claude#aaaaaaaa", f"{G}:9", db_path=db)
    assert POS.back("claude#aaaaaaaa", db_path=db)["addr"] == f"{G}:5"
    assert POS.back("claude#aaaaaaaa", db_path=db)["addr"] == f"{G}:1"
    # at the origin of the trail, back is a no-op that SAYS it is one
    r = POS.back("claude#aaaaaaaa", db_path=db)
    assert r["addr"] == f"{G}:1" and r["at_trail_origin"] is True


# ---------------------------------------------------------------- P4: look
def test_p4_look_renders_the_standpoint_with_numeric_heat(db):
    """Fence r1 C1: heat is NUMERIC in the envelope -- glow is a UI rendering, never the
    agent's channel. And an unpopulated gauge renders UNKNOWN, never a measured zero."""
    POS.go("claude#aaaaaaaa", f"{G}:5", db_path=db)
    v = POS.look("claude#aaaaaaaa", db_path=db)

    assert v["addr"] == f"{G}:5"
    assert v["node"]["voice"] == "operator"
    assert isinstance(v["heat"]["staleness_s"], (int, float))
    assert v["heat"]["credit"] is None, (
        "the transcript plane has no funnel credit -- UNKNOWN, not 0 "
        "(an unpopulated counter rendering as a measured zero is a named hazard here)")
    # neighbours are SILHOUETTES: one line each, never full bodies
    assert v["exits"], "a node in a connectome has edges out; they are the exits"
    for n in v["neighbors"]:
        assert len(n["snippet"]) <= 160
    assert v["tokens"] <= 400, "look is the DEFAULT verb; it must stay cheap"


def test_p4b_look_without_a_position_teaches_instead_of_guessing(db):
    with pytest.raises(ValueError) as e:
        POS.look("claude#cccccccc", db_path=db)
    assert "no position" in str(e.value).lower()
    assert "eye go" in str(e.value), "the refusal names the verb that fixes it"


# ---------------------------------------------------------------- P5: since
def test_p5_since_reports_only_this_seats_interval(db):
    """The ambient delta: what changed while I was away. Anchored on MY mark, so a twin's
    movement is not reported as my elapsed change."""
    POS.go("claude#aaaaaaaa", f"{G}:1", db_path=db)
    before = POS.since("claude#aaaaaaaa", db_path=db)
    assert before["events_added"] == 0, "nothing has happened since I arrived"

    # a later session lands in the corpus after my mark
    corpus = Path(db).parent / "corpus"
    shutil.copy(FIX / "session_epsilon.jsonl", corpus / "session_epsilon.jsonl")
    EYE.ingest(paths=[corpus / "session_epsilon.jsonl"], db_path=db)
    CONN.build(db_path=db)

    after = POS.since("claude#aaaaaaaa", db_path=db)
    assert after["events_added"] == 2, "epsilon contributes two text-bearing events"
    assert after["since_ts"] == before["since_ts"], "the mark did not move on its own"

    # a twin that never moved reports its OWN interval, not mine
    POS.go("claude#bbbbbbbb", f"{D}:1", db_path=db)
    assert POS.since("claude#bbbbbbbb", db_path=db)["events_added"] == 0


# ---------------------------------------------------------------- P6: succession
def test_p6_succession_is_explicit_and_recorded(db):
    """A fresh incarnation does not silently wear its predecessor's standpoint. Inheriting
    is an ACT, and the inheritor can tell that it inherited."""
    POS.go("claude#aaaaaaaa", f"{G}:6", db_path=db)

    assert POS.where("claude#dddddddd", db_path=db) is None, (
        "a successor is virgin until it says otherwise")

    got = POS.inherit("claude#dddddddd", "claude#aaaaaaaa", db_path=db)
    assert got["addr"] == f"{G}:6"
    assert got["inherited_from"] == "claude#aaaaaaaa"
    assert POS.where("claude#dddddddd", db_path=db)["inherited_from"] == "claude#aaaaaaaa"
    # and the predecessor is untouched by being inherited FROM
    assert POS.where("claude#aaaaaaaa", db_path=db)["addr"] == f"{G}:6"


def test_p6b_inheriting_from_a_seat_with_no_position_refuses(db):
    with pytest.raises(ValueError) as e:
        POS.inherit("claude#dddddddd", "claude#zzzzzzzz", db_path=db)
    assert "no position" in str(e.value).lower()


# ---------------------------------------------------------------- P7: the grammar's 422
def test_p7_go_to_a_bad_address_refuses_with_the_shape(db):
    """The grammar's 422 rule at this door: a bad selector never silent-empties."""
    with pytest.raises(ValueError) as e:
        POS.go("claude#aaaaaaaa", "not-an-address", db_path=db)
    msg = str(e.value)
    assert "session:line" in msg, "the refusal states the expected shape"
    assert POS.where("claude#aaaaaaaa", db_path=db) is None, (
        "a refused move leaves the seat where it was -- never half-moved")
