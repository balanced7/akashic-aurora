"""RED-first pins: a built-not-wired exception must be able to EXPIRE.

check_wiring's EXCEPTIONS block opens with a comment insisting it is "a BACKLOG, not an
amnesty". Measured 2026-08-24: 20 entries, ZERO with an expiry. The sibling allowlist in
check_comprehensibility carries dated expiries and one of them FIRED this morning --
lapsed, blocked a commit, forced a deliberate renewal. That is the difference between a
backlog and an amnesty, and only one of the two lists has it.

The prompt was Clarke & Dawe: "I won't be discussing operational matters, whatever they
are" -- an exemption defined loosely enough to cover whatever is needed later, forever.
An entry whose only safeguard is a sentence asking a future reader to notice is that.

DESIGN, deliberately a ratchet and not a flag day: the existing 20 string entries stay
valid (breaking every commit to make a point is how a good rule gets reverted). A DICT
entry may carry `expires`, and past that date the gate FAILS with re-verify-or-remove.
NEW entries must be dated -- enforced by a pin over the source, so the discipline applies
to the next author rather than to today's tree.

Run: py -m pytest tests/test_wiring_exceptions_expire.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "checkers"))


def _mod():
    import importlib
    import check_wiring
    return importlib.reload(check_wiring)


def test_string_entries_are_grandfathered_and_never_expire():
    """The existing 20 keep working. A rule that breaks every commit on the day it lands
    is a rule that gets reverted."""
    cw = _mod()
    assert cw.exception_expired("core/x.py", "KEEP built-ahead: some prose reason") is False


def test_a_dict_entry_past_its_date_is_EXPIRED():
    cw = _mod()
    entry = {"reason": "wire it when the consumer lands", "expires": "2020-01-01"}
    assert cw.exception_expired("core/x.py", entry) is True


def test_a_dict_entry_inside_its_date_is_live():
    cw = _mod()
    entry = {"reason": "wire it when the consumer lands", "expires": "2099-01-01"}
    assert cw.exception_expired("core/x.py", entry) is False


def test_a_malformed_date_does_not_silently_pass():
    """An unparseable expiry must not read as 'never expires' -- that is the amnesty
    failure mode wearing a typo."""
    cw = _mod()
    entry = {"reason": "r", "expires": "next tuesday"}
    assert cw.exception_expired("core/x.py", entry) is True


def test_expired_entry_produces_a_teaching_refusal():
    """The refusal must name the file, the date, and the two ways out -- the sibling
    allowlist's message is the model."""
    cw = _mod()
    msg = cw.exception_expiry_message("core/x.py", {"reason": "r", "expires": "2020-01-01"})
    assert "core/x.py" in msg
    assert "2020-01-01" in msg
    assert "re-verify" in msg.lower() or "remove" in msg.lower()


def test_every_NEW_entry_must_carry_an_expiry():
    """THE RATCHET. Today's 20 undated entries are frozen as a known set; anything added
    beyond that set must be dated. This pin is what makes 'BACKLOG, not an amnesty' true
    for the next author instead of aspirational for this one."""
    cw = _mod()
    undated = [k for k, v in cw.EXCEPTIONS.items() if isinstance(v, str)]
    assert len(undated) <= cw.GRANDFATHERED_UNDATED, (
        f"a NEW undated exception was added ({len(undated)} > {cw.GRANDFATHERED_UNDATED}). "
        "Give it an expiry: {'reason': ..., 'expires': 'YYYY-MM-DD'}")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
