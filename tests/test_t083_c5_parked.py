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


def test_in_progress_capped_at_two_watches(led):
    # UPDATED 2026-09-04: asserted Phase 1's one-at-a-time serialize until operator ruling
    # art_20260903_width-ruling-2026-09-03_369243 set the cap at TWO watches (ORG Part 3).
    # Full gauge pins: tests/test_width_gauge.py.
    _to_in_progress(led, "wave A")
    _to_in_progress(led, "wave B")                    # second watch is lawful now
    t = led.propose("wave C", by="claude", at="2026-07-16T01:02:00")
    led.transition(t["id"], TL.APPROVED, at="2026-07-16T01:02:01")
    led.transition(t["id"], TL.CLAIMED, owner="x", at="2026-07-16T01:02:02")
    with pytest.raises(TL.LedgerError, match="two-watch"):
        led.transition(t["id"], TL.IN_PROGRESS, at="2026-07-16T01:02:03")


def test_parked_keeps_file_claims(led):
    a = _to_in_progress(led, "wave A", files=["core/x.py"])
    TL.park(led, a, "shelved", at="2026-07-16T01:01:00")
    t = led.propose("wave B", files=["core/x.py"], by="claude", at="2026-07-16T01:02:00")
    led.transition(t["id"], TL.APPROVED, at="2026-07-16T01:02:01")
    with pytest.raises(TL.LedgerError, match="files held"):
        led.transition(t["id"], TL.CLAIMED, owner="x", at="2026-07-16T01:02:02")


def test_unpark_reenters_through_the_gate(led):
    # UPDATED 2026-09-04 for ruling 369243: unpark re-enters through the TWO-watch gate --
    # resuming as a third watch refuses the same way a fresh third start does.
    a = _to_in_progress(led, "wave A")
    TL.park(led, a, "shelved", at="2026-07-16T01:01:00")
    b = _to_in_progress(led, "wave B")
    c = _to_in_progress(led, "wave C")                # two watches open
    with pytest.raises(TL.LedgerError, match="two-watch"):
        TL.unpark(led, a, at="2026-07-16T01:03:00")   # B + C hold both watches
    TL.park(led, b, "swap", at="2026-07-16T01:04:00")
    assert TL.unpark(led, a, at="2026-07-16T01:05:00")["status"] == TL.IN_PROGRESS
    assert c  # C untouched throughout -- the swap only ever moved one watch


def test_parked_to_abandoned_is_legal(led):
    a = _to_in_progress(led)
    TL.park(led, a, "shelved", at="2026-07-16T01:01:00")
    assert led.transition(a, TL.ABANDONED, reason="killed", at="2026-07-16T01:06:00")["status"] \
        == TL.ABANDONED


def test_park_from_claimed_is_legal_but_needs_a_reason(led):
    """UPDATED 2026-08-01: this test asserted the OPPOSITE and had gone stale.

    CLAIMED->PARKED was deliberately legalised at da7962f ("a claim can now be released WITH
    its reason"), and task_ledger.py:80 records the intent: PARKED became reachable from
    CLAIMED and VERIFYING so a seat can hand back work it has claimed while SAYING WHY --
    where releasing to APPROVED drops it silently.

    The rule that survived is the one worth pinning: parking still REQUIRES a reason
    (task_ledger.py:214). Silent shelving is the thing the state exists to prevent, and that
    is what this now guards.

    Left as a stale red for a day because CI died at an earlier guardrail and the suite behind
    it never ran -- the same "gate rots unseen" loop this session was opened to close.
    """
    t = led.propose("w", by="claude", at="2026-07-16T01:00:00")
    led.transition(t["id"], TL.APPROVED, at="2026-07-16T01:00:01")
    led.transition(t["id"], TL.CLAIMED, owner="claude", at="2026-07-16T01:00:02")

    TL.park(led, t["id"], "handing it back: blocked on the T047 fence", at="2026-07-16T01:00:03")
    assert led.get(t["id"])["status"] == TL.PARKED

    t2 = led.propose("w2", by="claude", at="2026-07-16T02:00:00")
    led.transition(t2["id"], TL.APPROVED, at="2026-07-16T02:00:01")
    led.transition(t2["id"], TL.CLAIMED, owner="claude", at="2026-07-16T02:00:02")
    with pytest.raises(TL.LedgerError):
        TL.park(led, t2["id"], "", at="2026-07-16T02:00:03")


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
