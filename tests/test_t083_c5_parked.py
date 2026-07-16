"""T083-C5-1 pins: PARKED status -- a deliberately shelved wave frees the Phase-1 slot.

Live receipt 2026-07-16: T075 ('PARKED behind T047' in its own text) sat IN_PROGRESS for a day
and blocked T081's done transition through the one-in-progress serialize gate. PARKED keeps
owner + file claims, exits the slot, requires a reason, and resumes through the same gate.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import task_ledger as TL


@pytest.fixture()
def led(tmp_path):
    return TL.TaskLedger(str(tmp_path / "ledger.json"), client=None)


def _to_in_progress(led, title="wave", files=None):
    t = led.propose(title, owner="claude", files=files or [], by="claude", at="2026-07-16T01:00:00")
    led.transition(t["id"], TL.APPROVED, at="2026-07-16T01:00:01")
    led.transition(t["id"], TL.CLAIMED, owner="claude", at="2026-07-16T01:00:02")
    led.transition(t["id"], TL.IN_PROGRESS, at="2026-07-16T01:00:03")
    return t["id"]


def test_park_requires_reason(led):
    tid = _to_in_progress(led)
    with pytest.raises(TL.LedgerError, match="reason"):
        TL.park(led, tid, "", at="2026-07-16T01:01:00")


def test_park_frees_the_serialize_slot(led):
    a = _to_in_progress(led, "wave A")
    TL.park(led, a, "behind T047", at="2026-07-16T01:01:00")
    b = _to_in_progress(led, "wave B")          # would raise serialize if A still held the slot
    assert led.tasks[a]["status"] == TL.PARKED
    assert led.tasks[b]["status"] == TL.IN_PROGRESS


def test_in_progress_still_serialized_against_in_progress(led):
    _to_in_progress(led, "wave A")
    t = led.propose("wave B", by="claude", at="2026-07-16T01:02:00")
    led.transition(t["id"], TL.APPROVED, at="2026-07-16T01:02:01")
    led.transition(t["id"], TL.CLAIMED, owner="x", at="2026-07-16T01:02:02")
    with pytest.raises(TL.LedgerError, match="serialize"):
        led.transition(t["id"], TL.IN_PROGRESS, at="2026-07-16T01:02:03")


def test_parked_keeps_file_claims(led):
    a = _to_in_progress(led, "wave A", files=["core/x.py"])
    TL.park(led, a, "shelved", at="2026-07-16T01:01:00")
    t = led.propose("wave B", files=["core/x.py"], by="claude", at="2026-07-16T01:02:00")
    led.transition(t["id"], TL.APPROVED, at="2026-07-16T01:02:01")
    with pytest.raises(TL.LedgerError, match="files held"):
        led.transition(t["id"], TL.CLAIMED, owner="x", at="2026-07-16T01:02:02")


def test_unpark_reenters_through_the_gate(led):
    a = _to_in_progress(led, "wave A")
    TL.park(led, a, "shelved", at="2026-07-16T01:01:00")
    b = _to_in_progress(led, "wave B")
    with pytest.raises(TL.LedgerError, match="serialize"):
        TL.unpark(led, a, at="2026-07-16T01:03:00")   # B holds the slot
    TL.park(led, b, "swap", at="2026-07-16T01:04:00")
    assert TL.unpark(led, a, at="2026-07-16T01:05:00")["status"] == TL.IN_PROGRESS


def test_parked_to_abandoned_is_legal(led):
    a = _to_in_progress(led)
    TL.park(led, a, "shelved", at="2026-07-16T01:01:00")
    assert led.transition(a, TL.ABANDONED, reason="killed", at="2026-07-16T01:06:00")["status"] \
        == TL.ABANDONED


def test_park_from_claimed_is_illegal(led):
    t = led.propose("w", by="claude", at="2026-07-16T01:00:00")
    led.transition(t["id"], TL.APPROVED, at="2026-07-16T01:00:01")
    led.transition(t["id"], TL.CLAIMED, owner="claude", at="2026-07-16T01:00:02")
    with pytest.raises(TL.LedgerError, match="illegal transition"):
        TL.park(led, t["id"], "nope", at="2026-07-16T01:00:03")


def test_state_view_and_bar_render_parked(led):
    a = _to_in_progress(led, "wave A")
    TL.park(led, a, "behind T047 fence", at="2026-07-16T01:01:00")
    v = TL.state_view(led.path, None)
    assert [p["id"] for p in v["parked"]] == [a]
    assert v["parked"][0]["reason"] == "behind T047 fence"
    assert v["counts"][TL.PARKED] == 1
    assert all(p["id"] != a for p in v["in_progress"])   # parked is NOT in the working set
    txt = TL.format_state(path=led.path, client=None)
    assert "PARKED (shelved with a reason" in txt
    assert "parked 1" in txt
