"""PRE-REGISTERED ACCEPTANCE (T138) -- a delivered-but-misfiled entry can reach DONE honestly.

MEASURED 2026-08-03 while executing the ledger consolidation Daniil asked for. Four entries are
COMPLETION RECORDS misfiled as proposals -- someone recorded a finished slice by proposing a new
entry describing it. Their own titles say so, and every sha resolves:

    T110 proposed  "T110 DONE (08f6016+c2244b6): cost meter honesty..."
    T111 proposed  "T108 slice 2 DONE (31e6737): per-incarnation lane cursor..."
    T112 proposed  "T113 DONE (c94e1f4): the tool send door spills oversize payloads..."
    T113 proposed  "T115 DONE (2cc5dc6): check_advertised_verbs..."

There is no honest way to close them. DONE is reachable only through VERIFYING, VERIFYING only
through IN_PROGRESS, and IN_PROGRESS is serialized one-at-a-time -- currently held by T086. So
recording four delivered slices would mean faking four IN_PROGRESS events, one at a time, for work
that finished a week ago. The only reachable terminal is ABANDONED, which asserts the intent DIED
when it was in fact DELIVERED, and would drop four commits' worth of receipts out of the record.

THIS EXACT CLASS WAS FOUND AND FIXED ONCE ALREADY, one door over. task_ledger.py:80 records it:

    "CLAIMED-and-never-started is the state that ACCUMULATES... Its only exits were ABANDONED
     (destructive: asserts the intent DIED when it merely DRIFTED) and APPROVED (no --reason, so
     the rationale is lost). Receipt: 21 ACTIVE / 16 CLAIMED-not-started, unparkable without
     routing each through the one serialized IN_PROGRESS slot -- 16 FALSE in_progress events in an
     audited ledger purely to reach a legal state. A ledger you cannot cut honestly is a ledger
     that grows."

Same sentence, different terminal. That fix added PARKED as reachable from CLAIMED; this one adds
VERIFYING, because VERIFICATION IS LITERALLY THE WORK BEING DONE -- checking a claimed sha against
the commit. Nothing about the evidence bar moves: the done gate still refuses without a commit AND
a verification record ("no proof, no close"), and that gate is what makes this safe rather than a
shortcut. The serialize gate is untouched -- it tests `to == IN_PROGRESS` specifically, so this
path never occupies the slot it never needed.

  L1  CLAIMED -> VERIFYING is legal                       (the receipt path exists at all)
  L2  the done gate is NOT weakened on that path          (no commit or no verified_by -> refused)
  L3  the receipt path never occupies the IN_PROGRESS slot
  L4  the shortcut is not opened wholesale                (PROPOSED -> DONE still illegal)
  L5  the normal build path still works                   (no regression)

Run: py -m pytest tests/test_t138_receipt_path_to_done.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import task_ledger as TL  # noqa: E402


@pytest.fixture()
def led(tmp_path):
    return TL.TaskLedger(str(tmp_path / "ledger.json"), client=None)


def _to_claimed(led, title="receipt", at="2026-08-03T01:00:00"):
    t = led.propose(title, owner="claude", files=[], by="claude", at=at)
    led.transition(t["id"], TL.APPROVED, at=at)
    led.transition(t["id"], TL.CLAIMED, owner="claude", at=at)
    return t["id"]


def _to_in_progress(led, title="wave"):
    tid = _to_claimed(led, title)
    led.transition(tid, TL.IN_PROGRESS, at="2026-08-03T01:00:04")
    return tid


def test_l1_claimed_reaches_verifying(led):
    """The receipt path exists: work already on disk does not have to be re-enacted."""
    tid = _to_claimed(led)
    led.transition(tid, TL.VERIFYING, at="2026-08-03T01:00:05")
    assert led.tasks[tid]["status"] == TL.VERIFYING


def test_l2_the_done_gate_is_not_weakened(led):
    """No proof, no close -- on this path exactly as on every other. This is the gate that makes
    a shorter route safe; without it this pin file would be arguing for a hole."""
    tid = _to_claimed(led)
    led.transition(tid, TL.VERIFYING, at="2026-08-03T01:00:05")
    with pytest.raises(TL.LedgerError, match="no proof, no close"):
        led.transition(tid, TL.DONE, at="2026-08-03T01:00:06")
    with pytest.raises(TL.LedgerError, match="no proof, no close"):
        led.transition(tid, TL.DONE, commit="08f6016", at="2026-08-03T01:00:07")
    led.transition(tid, TL.DONE, commit="08f6016",
                   verified_by="receipt check: sha resolves, message matches the entry",
                   at="2026-08-03T01:00:08")
    assert led.tasks[tid]["status"] == TL.DONE
    assert led.tasks[tid]["commit"] == "08f6016"


def test_l3_the_receipt_path_never_takes_the_serialize_slot(led):
    """A live build must keep running while old receipts are filed. The serialize gate tests
    `to == IN_PROGRESS` specifically, so this must hold by construction -- pinned so a later
    widening of that gate cannot silently deadlock the receipt path."""
    live = _to_in_progress(led, "the live wave")
    tid = _to_claimed(led, "a receipt filed while the live wave runs")
    led.transition(tid, TL.VERIFYING, at="2026-08-03T01:01:00")
    led.transition(tid, TL.DONE, commit="c94e1f4", verified_by="receipt check",
                   at="2026-08-03T01:01:01")
    assert led.tasks[live]["status"] == TL.IN_PROGRESS
    assert led.tasks[tid]["status"] == TL.DONE


def test_l4_the_shortcut_is_not_opened_wholesale(led):
    """Closing a receipt is not the same as skipping the lifecycle. A fresh proposal must still
    walk it."""
    t = led.propose("brand new work", by="claude", at="2026-08-03T02:00:00")
    with pytest.raises(TL.LedgerError, match="illegal transition"):
        led.transition(t["id"], TL.DONE, commit="deadbee", verified_by="x",
                       at="2026-08-03T02:00:01")
    led.transition(t["id"], TL.APPROVED, at="2026-08-03T02:00:02")
    with pytest.raises(TL.LedgerError, match="illegal transition"):
        led.transition(t["id"], TL.VERIFYING, at="2026-08-03T02:00:03")


def test_l5_the_normal_build_path_still_works(led):
    tid = _to_in_progress(led, "ordinary wave")
    led.transition(tid, TL.VERIFYING, at="2026-08-03T03:00:00")
    led.transition(tid, TL.DONE, commit="abc1234", verified_by="pytest",
                   at="2026-08-03T03:00:01")
    assert led.tasks[tid]["status"] == TL.DONE
