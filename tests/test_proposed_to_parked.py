"""Pre-registered pins: PROPOSED -> PARKED, the "still valid, just not now" exit.

Written and committed BEFORE the one-line TRANSITIONS change they gate (M3).

THE GAP. TRANSITIONS had PROPOSED: {APPROVED, ABANDONED}. So a proposal that is still
wanted but not now had exactly two doors, and both lie:

  ABANDONED  -- asserts the intent DIED. It did not; it DRIFTED.
  APPROVED -> CLAIMED -> PARKED  -- three manufactured events (and a file claim) to
             record one decision, through the serialized IN_PROGRESS-adjacent path.

That is the SAME defect task_ledger.py already documents against itself twice, in its
own comments: T139 ("recording four week-old deliveries meant faking four IN_PROGRESS
events") and T083-C5-1 ("16 FALSE in_progress events ... purely to reach a legal
state"). Same shape, one status earlier in the lifecycle.

Receipt for why it is worth a slice: 68 proposals stand, 32 of them rendered stale.
Every one of them faces the same two bad doors today.

The evidence bar does not move. PARKED's mandatory --reason gate is untouched and is
pinned here from the new origin, so a shorter route stays a route and not a hole.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import task_ledger as TL


@pytest.fixture()
def led(tmp_path):
    return TL.TaskLedger(str(tmp_path / "ledger.json"), client=None)


def _proposed(led, title="a wave we still want"):
    return led.propose(title, owner="claude", by="claude", at="2026-08-11T18:00:00")["id"]


def test_proposed_to_parked_is_legal(led):
    """The transition exists at all -- this is the line the slice adds."""
    tid = _proposed(led)
    TL.park(led, tid, "waiting on the sharding window", at="2026-08-11T18:01:00")
    assert led.tasks[tid]["status"] == TL.PARKED


def test_proposed_to_parked_still_requires_a_reason(led):
    """The park gate must fire from the NEW origin, not just from IN_PROGRESS.

    Before the fix this raises 'illegal transition' instead, so the match= is what
    makes this pin RED for the right reason rather than passing by accident.
    """
    tid = _proposed(led)
    with pytest.raises(TL.LedgerError, match="reason"):
        TL.park(led, tid, "", at="2026-08-11T18:01:00")


def test_parking_a_proposal_records_the_reason_in_history(led):
    """A shelved proposal that does not say WHY is the ambiguity PARKED exists to end."""
    tid = _proposed(led)
    TL.park(led, tid, "superseded by the shard fix", at="2026-08-11T18:01:00")
    last = led.tasks[tid]["history"][-1]
    assert last["to"] == TL.PARKED
    assert "superseded by the shard fix" in str(last.get("reason", ""))


def test_abandoned_is_still_reachable_from_proposed(led):
    """The new door must not replace the old one -- a proposal that truly died still dies."""
    tid = _proposed(led)
    led.transition(tid, TL.ABANDONED, by="claude", at="2026-08-11T18:01:00")
    assert led.tasks[tid]["status"] == TL.ABANDONED


def test_parked_proposal_is_not_counted_as_active(led):
    """Parking must clear it from the active set, or the stale-proposal bar does not move."""
    tid = _proposed(led)
    TL.park(led, tid, "not this week", at="2026-08-11T18:01:00")
    assert tid not in [t["id"] for t in led.in_progress()]
