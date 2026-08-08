"""T250 -- five bypasses in the T248 gate, found by fencing the gate's own slice.

T248 shipped a gate that refuses to close a load-bearing task without an independent reviewer.
It was the first slice of the day I did NOT self-verify -- and the fence found five real
bypasses in one pass, hours after it landed.

Four are fixed here. The fifth is architectural and is stated in the gate's docstring instead:
the gate reads the task's DECLARED `files`, never the actual diff, so declaring
`files=["README.md"]` while editing `core/` is unblocked. That is the honest limit of a
declaration-based gate and the reason it is a speed bump rather than a wall. Naming it is worth
more than pretending otherwise -- a guard believed to be a wall is more dangerous than one known
to be a bump.

ADJUDICATED AND REJECTED, pinned so they are not re-filed and so a later widening cannot start
catching them by accident:
  - `core.py` at the repo root is NOT the `core/` package.
  - a directory named `mycore/` is not `core/`.
  - direct edits to tasks.json are filesystem access, not a boundary this gate can defend.
"""
import pytest

from core.coord import task_ledger as TL


@pytest.fixture
def ledger(tmp_path):
    return TL.TaskLedger(str(tmp_path / "ledger.json"), client=None)


def _verifying(ledger, files, owner="claude"):
    t = ledger.propose("slice", files=files, owner=owner, by="claude", at="2026-08-08T00:00:00")
    tid = t["id"]
    for st in (TL.APPROVED, TL.CLAIMED, TL.VERIFYING):
        ledger.transition(tid, st, by="claude", at="2026-08-08T00:00:01")
    return tid


# ------------------------------------------------------------------ identity comparison
@pytest.mark.parametrize("alias", [" claude", "claude ", "Claude", "CLAUDE", "  Claude  "])
def test_the_closer_cannot_review_themselves_under_an_alias(ledger, alias):
    """Exact string equality made ' claude' an independent reviewer of claude's own work."""
    tid = _verifying(ledger, ["core/comm/ask.py"])
    with pytest.raises(TL.LedgerError):
        ledger.transition(tid, TL.DONE, by="claude", at="2026-08-08T00:01:00",
                          commit="abc1234", verified_by="pins", reviewed_by=alias)


def test_an_unidentifiable_closer_cannot_pass_the_gate(ledger):
    """`r == (by or owner)` with both empty compares against "" -- so ANY name passed.

    A gate about identity must not run when it cannot establish who is acting. Refusing is the
    only honest branch: the alternative is a check that reports success without having checked.
    """
    tid = _verifying(ledger, ["core/comm/ask.py"], owner="")
    with pytest.raises(TL.LedgerError) as e:
        ledger.transition(tid, TL.DONE, by="", at="2026-08-08T00:01:00",
                          commit="abc1234", verified_by="pins", reviewed_by="somebody")
    assert "who" in str(e.value).lower() or "closer" in str(e.value).lower(), (
        f"the refusal must say the CLOSER is unknown, not imply the reviewer was bad: {e.value}")


def test_a_known_closer_with_a_real_reviewer_still_closes(ledger):
    """The gate must stay passable, or it gets routed around and protects nothing."""
    tid = _verifying(ledger, ["core/comm/ask.py"])
    t = ledger.transition(tid, TL.DONE, by="claude", at="2026-08-08T00:01:00",
                          commit="abc1234", verified_by="pins", reviewed_by="deepseek")
    assert t["status"] == TL.DONE


# ------------------------------------------------------------------ path normalisation
@pytest.mark.parametrize("path", [
    "core/comm/ask.py",
    "./core/comm/ask.py",
    "core\\comm\\ask.py",
    "/srv/repo/core/comm/ask.py",          # absolute
    "E:\\AI-Setup\\core\\comm\\ask.py",    # absolute, windows
    "subdir/../core/comm/ask.py",          # non-leading ..
])
def test_load_bearing_survives_path_spelling(path):
    assert TL.is_load_bearing([path]), f"{path!r} is core/ and was not recognised"


@pytest.mark.parametrize("path", ["core.py", "mycore/x.py", "docs/core-notes.md",
                                  "tests/test_core.py", "score/x.py"])
def test_these_are_correctly_not_load_bearing(path):
    """FREEZES REJECTED FINDINGS. core.py at root is not the core/ package.

    Widening the match until these hit would make the gate fire on documentation, which is how
    a gate becomes noise and then gets routed around.
    """
    assert not TL.is_load_bearing([path]), f"{path!r} must NOT count as load-bearing"


# ------------------------------------------------------------------ the stated limit
def test_the_declared_files_limit_is_written_down():
    """The bypass I am NOT fixing must be findable by the next reader.

    The gate trusts the task's declared `files`. A guard believed to be a wall is more
    dangerous than one known to be a bump, so the limit lives in the docstring rather than in
    a reviewer's head.
    """
    doc = (TL.is_load_bearing.__doc__ or "") + (TL.TaskLedger.transition.__doc__ or "")
    assert "declar" in doc.lower(), (
        "the declared-files limit is not stated anywhere a reader of the gate will find it")
