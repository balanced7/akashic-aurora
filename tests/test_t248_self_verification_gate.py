"""T248 -- the done gate could not tell verification from SELF-verification.

MEASURED ON ME, 2026-08-08. I closed four consecutive load-bearing slices (T242-T245, all
touching core/comm/ask.py and agent_cli.py) writing "SELF-VERIFIED by claude -- no second seat"
into `--verified-by`. The ledger stored that faithfully and acted on it not at all. One fence
afterwards found THREE real defects in one pass for $0.09, and two of them were the same defect
those slices shipped to fix, reappearing through doors my own pins never opened.

The same class as T242, one level up: the record was CORRECT, complete, and consulted by
nobody. Today that shape has now cost two runs, four unreviewed slices, and three defects.

WHY A NORM WAS NOT ENOUGH, stated precisely so the fix is not mistaken for a moral. I knew the
rule. I believed the rule. I had written, in this session, that skipping it was a gap -- and
then skipped it three more times. The failure is not knowledge and cannot be repaired by
intending harder, which is exactly the argument for a forcing function rather than a reminder.

TWO FIELDS, BECAUSE THEY ARE TWO CLAIMS.
    verified_by  -- the EVIDENCE. "4 pins + 209 tests + a live check."
    reviewed_by  -- the PERSON, and whether they are someone other than the author.
Collapsing them is what let a sentence describing evidence satisfy a gate about independence.

THE ESCAPE HATCH IS DELIBERATE. A gate with no exit gets routed around by not using the ledger
at all, and an unused ledger is worse than a permissive one. `--self-verified <reason>` closes
the task and RECORDS the override, so overrides become countable instead of invisible. The
count is the real instrument; the refusal is just what makes the count honest.

THE THRESHOLD IS NOT MINE TO SET. LOAD_BEARING is one named constant so it is visible and
tunable in one place. I am the one being gated, so picking my own threshold is the
ratified-my-own-drafts defect (T227) one level up.
"""
import pytest

from core.coord import task_ledger as TL


@pytest.fixture
def ledger(tmp_path):
    """client=None keeps this off the shared Redis ledger, as every other ledger test does."""
    return TL.TaskLedger(str(tmp_path / "ledger.json"), client=None)


def _mk(ledger, files, title="a slice"):
    t = ledger.propose(title, files=files, by="claude", at="2026-08-08T00:00:00")
    tid = t["id"]
    ledger.transition(tid, TL.APPROVED, by="claude", at="2026-08-08T00:00:01")
    ledger.transition(tid, TL.CLAIMED, by="claude", at="2026-08-08T00:00:02")
    ledger.transition(tid, TL.VERIFYING, by="claude", at="2026-08-08T00:00:03")
    return tid


def test_a_load_bearing_slice_cannot_close_self_verified(ledger):
    """The defect, in the shape it actually occurred four times."""
    tid = _mk(ledger, ["core/comm/ask.py"])
    with pytest.raises(TL.LedgerError) as e:
        ledger.transition(tid, TL.DONE, by="claude", at="2026-08-08T00:01:00",
                          commit="abc1234",
                          verified_by="4 pins + 209 tests. SELF-VERIFIED by claude -- no second seat.")
    msg = str(e.value)
    assert "review" in msg.lower(), f"the refusal must name what is missing: {msg}"
    assert "self-verified" in msg.lower() or "--self-verified" in msg, (
        f"the refusal must name the escape hatch, or it just blocks work: {msg}")


def test_the_same_slice_closes_when_someone_else_reviewed_it(ledger):
    """The gate must be passable by doing the right thing, not only by overriding."""
    tid = _mk(ledger, ["core/comm/ask.py"])
    t = ledger.transition(tid, TL.DONE, by="claude", at="2026-08-08T00:01:00",
                          commit="abc1234", verified_by="4 pins + 209 tests",
                          reviewed_by="deepseek")
    assert t["status"] == TL.DONE
    assert t["reviewed_by"] == "deepseek"


def test_reviewing_yourself_does_not_count(ledger):
    """The obvious way around it, closed at the same time as the door it bypasses."""
    tid = _mk(ledger, ["core/comm/ask.py"])
    with pytest.raises(TL.LedgerError):
        ledger.transition(tid, TL.DONE, by="claude", at="2026-08-08T00:01:00",
                          commit="abc1234", verified_by="pins", reviewed_by="claude")


def test_a_non_load_bearing_slice_is_unaffected(ledger):
    """Docs and tests must not need a fence, or the gate becomes noise and gets routed around."""
    tid = _mk(ledger, ["docs/TROUBLESHOOTING.md"])
    t = ledger.transition(tid, TL.DONE, by="claude", at="2026-08-08T00:01:00",
                          commit="abc1234", verified_by="read it")
    assert t["status"] == TL.DONE


def test_the_override_closes_the_task_and_records_its_reason(ledger):
    """A gate with no exit gets routed around by abandoning the ledger entirely."""
    tid = _mk(ledger, ["core/comm/ask.py"])
    t = ledger.transition(tid, TL.DONE, by="claude", at="2026-08-08T00:01:00",
                          commit="abc1234", verified_by="pins",
                          self_verified="no peer awake at 03:00, defect is a one-line typo")
    assert t["status"] == TL.DONE
    assert "no peer awake" in (t.get("self_verified") or ""), (
        "the override must persist its REASON -- an override nobody can count is an "
        "exemption, and this whole task exists because an unread record is not a control")


def test_an_override_with_no_reason_is_refused(ledger):
    """An escape hatch that costs nothing to use is not an escape hatch, it is the default."""
    tid = _mk(ledger, ["core/comm/ask.py"])
    with pytest.raises(TL.LedgerError):
        ledger.transition(tid, TL.DONE, by="claude", at="2026-08-08T00:01:00",
                          commit="abc1234", verified_by="pins", self_verified="   ")


def test_the_threshold_is_one_visible_constant():
    """So Daniil can see and change what counts as load-bearing without reading the gate.

    I am the one being gated. Picking my own threshold, silently, inside a function, is the
    T227 ratified-my-own-drafts defect one level up.
    """
    assert hasattr(TL, "LOAD_BEARING"), "the threshold must be a named, findable constant"
    assert any("core/" in p for p in TL.LOAD_BEARING), (
        f"the default must at least cover core/: {TL.LOAD_BEARING}")


def test_overrides_are_countable(ledger):
    """The count is the instrument. The refusal only makes the count honest."""
    a = _mk(ledger, ["core/comm/ask.py"], "one")
    ledger.transition(a, TL.DONE, by="claude", at="2026-08-08T00:01:00", commit="a1",
                      verified_by="pins", self_verified="reason one")
    b = _mk(ledger, ["core/comm/bus.py"], "two")
    ledger.transition(b, TL.DONE, by="claude", at="2026-08-08T00:02:00", commit="b1",
                      verified_by="pins", reviewed_by="deepseek")

    overridden = [t for t in ledger.tasks.values() if t.get("self_verified")]
    assert len(overridden) == 1, (
        f"exactly one task used the override; found {len(overridden)}. If this cannot be "
        "counted, nobody can tell a rare exception from the new normal.")
